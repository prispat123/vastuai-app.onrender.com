from __future__ import annotations

import json

from knowledge_engine import KnowledgeEngine, KnowledgeRepository
from knowledge_engine.importer import (
    ensure_seeded,
    export_runtime_json_bytes,
    import_json_master,
    runtime_status,
)
from platform_core.database import connect, transaction


def repository() -> KnowledgeRepository:
    ensure_seeded()
    return KnowledgeRepository()


def engine() -> KnowledgeEngine:
    return KnowledgeEngine(repository())


# Repository and engine creation is intentionally lazy. Streamlit imports UI
# modules before app.py calls initialize_database(), so module-level database
# access would fail when an existing database has not yet received the additive
# Knowledge tables.


def ensure_settings(project_id: int) -> None:
    with transaction() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO project_knowledge_settings(
                project_id,profile_name
            ) VALUES(?, 'practical')
            """,
            (int(project_id),),
        )


def get_profile(project_id: int) -> str:
    ensure_settings(project_id)
    with connect() as connection:
        row = connection.execute(
            """
            SELECT profile_name
            FROM project_knowledge_settings
            WHERE project_id=?
            """,
            (int(project_id),),
        ).fetchone()
    profile = row["profile_name"] if row else "practical"
    if profile not in repository().profiles():
        return "practical"
    return profile


def set_profile(project_id: int, profile_name: str) -> None:
    if profile_name not in repository().profiles():
        raise ValueError("Invalid Knowledge profile.")
    ensure_settings(project_id)
    with transaction() as connection:
        connection.execute(
            """
            UPDATE project_knowledge_settings
            SET profile_name=?,updated_at=CURRENT_TIMESTAMP
            WHERE project_id=?
            """,
            (profile_name, int(project_id)),
        )


def evaluate_layout(
    project_id: int,
    layout_id: int,
    observations: dict,
    *,
    detection_confidences: dict | None = None,
) -> dict:
    profile = get_profile(project_id)
    result = engine().evaluate(
        observations,
        profile=profile,
        detection_confidences=detection_confidences,
    )

    with transaction() as connection:
        connection.execute(
            """
            INSERT INTO layout_knowledge_assessments(
                project_id,layout_id,profile_name,result_json
            ) VALUES(?,?,?,?)
            ON CONFLICT(layout_id,profile_name) DO UPDATE SET
                result_json=excluded.result_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                int(project_id),
                int(layout_id),
                profile,
                json.dumps(result),
            ),
        )
    return result


def latest_assessment(layout_id: int):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM layout_knowledge_assessments
            WHERE layout_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (int(layout_id),),
        ).fetchone()
    if not row:
        return None
    return {
        "profile_name": row["profile_name"],
        "result": json.loads(row["result_json"] or "{}"),
    }


def refresh_from_json() -> dict:
    return import_json_master()


def knowledge_status() -> dict:
    return runtime_status()


def export_backup_bytes() -> bytes:
    return export_runtime_json_bytes()
