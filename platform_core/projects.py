from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

from platform_core.config import CONFIG
from platform_core.database import connect, transaction
from platform_core.storage import STORAGE
from platform_core.logging_service import LOGGER

VALID_WORKSPACES = {"Professional", "Builder"}

def _slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    return value.strip("-") or "project"

def _project_folder(workspace: str, project_uuid: str, name: str) -> Path:
    return CONFIG.projects_dir / workspace / f"{_slug(name)}_{project_uuid[:8]}"

def create_project(
    *,
    name: str,
    workspace_type: str,
    client_or_builder: str = "",
    city: str = "",
    description: str = "",
) -> int:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name is required.")
    if workspace_type not in VALID_WORKSPACES:
        raise ValueError("Invalid workspace type.")

    project_uuid = str(uuid.uuid4())
    folder = _project_folder(workspace_type, project_uuid, clean_name)
    folder.mkdir(parents=True, exist_ok=False)

    metadata = {
        "schema_version": 1,
        "project_uuid": project_uuid,
        "name": clean_name,
        "workspace_type": workspace_type,
        "client_or_builder": client_or_builder.strip(),
        "city": city.strip(),
        "description": description.strip(),
    }
    (folder / "project.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    STORAGE.ensure_project_structure(folder)

    try:
        with transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO projects(
                    project_uuid,name,workspace_type,client_or_builder,
                    city,description,project_folder
                )
                VALUES(?,?,?,?,?,?,?)
                """,
                (
                    project_uuid,
                    clean_name,
                    workspace_type,
                    client_or_builder.strip(),
                    city.strip(),
                    description.strip(),
                    str(folder),
                ),
            )
            project_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO project_events(project_id,event_type,details)
                VALUES(?,?,?)
                """,
                (project_id, "PROJECT_CREATED", json.dumps(metadata)),
            )
            LOGGER.info(
                "Created %s project %s (%s)",
                workspace_type,
                clean_name,
                project_uuid,
            )
            return project_id
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise

def list_projects(workspace_type: str | None = None):
    query = "SELECT * FROM projects"
    params = ()
    if workspace_type:
        query += " WHERE workspace_type=?"
        params = (workspace_type,)
    query += " ORDER BY updated_at DESC,id DESC"
    with connect() as connection:
        return connection.execute(query, params).fetchall()

def get_project(project_id: int):
    with connect() as connection:
        return connection.execute(
            "SELECT * FROM projects WHERE id=?",
            (project_id,),
        ).fetchone()

def update_project(
    project_id: int,
    *,
    name: str,
    client_or_builder: str,
    city: str,
    description: str,
    status: str,
) -> None:
    if not name.strip():
        raise ValueError("Project name is required.")
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM projects WHERE id=?",
            (project_id,),
        ).fetchone()
        if not row:
            raise ValueError("Project not found.")
        connection.execute(
            """
            UPDATE projects SET
                name=?,client_or_builder=?,city=?,description=?,status=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                name.strip(),
                client_or_builder.strip(),
                city.strip(),
                description.strip(),
                status,
                project_id,
            ),
        )
        connection.execute(
            """
            INSERT INTO project_events(project_id,event_type,details)
            VALUES(?,?,?)
            """,
            (
                project_id,
                "PROJECT_UPDATED",
                json.dumps(
                    {
                        "name": name.strip(),
                        "client_or_builder": client_or_builder.strip(),
                        "city": city.strip(),
                        "status": status,
                    }
                ),
            ),
        )

def touch_project(project_id: int, event_type: str, details: str = "") -> None:
    with transaction() as connection:
        connection.execute(
            "UPDATE projects SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (project_id,),
        )
        connection.execute(
            """
            INSERT INTO project_events(project_id,event_type,details)
            VALUES(?,?,?)
            """,
            (project_id, event_type, details),
        )

def delete_project(project_id: int, *, delete_files: bool = True) -> None:
    row = get_project(project_id)
    if not row:
        return
    folder = Path(row["project_folder"])
    with transaction() as connection:
        connection.execute("DELETE FROM projects WHERE id=?", (project_id,))
    if delete_files:
        shutil.rmtree(folder, ignore_errors=True)

def project_health(project) -> dict:
    folder = Path(project["project_folder"])
    return {
        "folder_exists": folder.exists(),
        "metadata_exists": (folder / "project.json").exists(),
        "uploads_folder": (folder / "uploads").exists(),
        "analysis_folder": (folder / "analysis").exists(),
    }
