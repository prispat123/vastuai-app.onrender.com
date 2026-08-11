from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from platform_core.database import connect, transaction
from platform_core.projects import get_project, touch_project
from platform_core.storage import STORAGE

DOCUMENT_CATEGORIES = [
    "Brochure",
    "Master Layout",
    "Floor Plans",
    "Images",
    "Other",
]

ANALYSIS_STATUSES = [
    "Not Started",
    "Queued",
    "Extracting",
    "Ready",
    "Knowledge Analysis",
    "Completed",
    "Needs Review",
]

PROJECT_TYPES = [
    "Apartment",
    "Villa",
    "Township",
    "Commercial",
]

def ensure_project_details(project_id: int) -> None:
    with transaction() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO project_intelligence_details(project_id)
            VALUES(?)
            """,
            (int(project_id),),
        )

def get_project_details(project_id: int):
    ensure_project_details(project_id)
    with connect() as connection:
        return connection.execute(
            """
            SELECT p.*, d.project_type, d.state, d.country,
                   d.north_reference, d.number_of_towers, d.remarks
            FROM projects p
            JOIN project_intelligence_details d ON d.project_id=p.id
            WHERE p.id=?
            """,
            (int(project_id),),
        ).fetchone()

def update_project_details(
    project_id: int,
    *,
    project_type: str,
    state: str,
    country: str,
    north_reference: str,
    number_of_towers: int,
    remarks: str,
) -> None:
    ensure_project_details(project_id)
    with transaction() as connection:
        connection.execute(
            """
            UPDATE project_intelligence_details SET
                project_type=?,state=?,country=?,north_reference=?,
                number_of_towers=?,remarks=?,updated_at=CURRENT_TIMESTAMP
            WHERE project_id=?
            """,
            (
                project_type,
                state.strip(),
                country.strip(),
                north_reference,
                int(number_of_towers),
                remarks.strip(),
                int(project_id),
            ),
        )
    add_timeline_event(
        project_id,
        "PROJECT_DETAILS_UPDATED",
        "Project details updated",
        f"Project type: {project_type}; towers: {number_of_towers}",
    )
    touch_project(project_id, "PROJECT_INTELLIGENCE_DETAILS_UPDATED")

def _category_folder(project_folder: str, category: str) -> Path:
    safe = category.lower().replace(" ", "_")
    folder = Path(project_folder) / "documents" / safe
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def save_document(project_id: int, category: str, uploaded_file) -> int:
    if category not in DOCUMENT_CATEGORIES:
        raise ValueError("Invalid document category.")
    project = get_project(project_id)
    if not project:
        raise ValueError("Project not found.")

    data = uploaded_file.getvalue()
    original_name = Path(uploaded_file.name).name
    document_uuid = str(uuid.uuid4())
    destination = (
        _category_folder(project["project_folder"], category)
        / f"{document_uuid[:8]}_{original_name}"
    )
    STORAGE.save_bytes(destination, data, overwrite=False)
    file_hash = hashlib.sha256(data).hexdigest()

    with transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO project_documents(
                project_id,document_uuid,category,display_name,
                original_name,stored_path,file_hash,file_size
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                int(project_id),
                document_uuid,
                category,
                original_name,
                original_name,
                str(destination),
                file_hash,
                len(data),
            ),
        )
        document_id = int(cursor.lastrowid)

    add_timeline_event(
        project_id,
        "DOCUMENT_UPLOADED",
        f"{category} uploaded",
        original_name,
    )
    touch_project(project_id, "DOCUMENT_UPLOADED", original_name)
    return document_id

def list_documents(project_id: int, category: str | None = None):
    query = "SELECT * FROM project_documents WHERE project_id=?"
    params: tuple[Any, ...] = (int(project_id),)
    if category:
        query += " AND category=?"
        params += (category,)
    query += " ORDER BY uploaded_at DESC,id DESC"
    with connect() as connection:
        return connection.execute(query, params).fetchall()

def rename_document(document_id: int, display_name: str) -> None:
    if not display_name.strip():
        raise ValueError("Document name cannot be blank.")
    with transaction() as connection:
        row = connection.execute(
            "SELECT project_id FROM project_documents WHERE id=?",
            (int(document_id),),
        ).fetchone()
        if not row:
            raise ValueError("Document not found.")
        connection.execute(
            "UPDATE project_documents SET display_name=? WHERE id=?",
            (display_name.strip(), int(document_id)),
        )
    add_timeline_event(
        int(row["project_id"]),
        "DOCUMENT_RENAMED",
        "Document renamed",
        display_name.strip(),
    )

def delete_document(document_id: int) -> None:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM project_documents WHERE id=?",
            (int(document_id),),
        ).fetchone()
        if not row:
            return
        connection.execute(
            "DELETE FROM project_documents WHERE id=?",
            (int(document_id),),
        )
    path = Path(row["stored_path"])
    if path.exists():
        path.unlink()
    add_timeline_event(
        int(row["project_id"]),
        "DOCUMENT_DELETED",
        "Document deleted",
        row["display_name"],
    )

def add_layout(
    project_id: int,
    *,
    tower: str,
    flat_number: str,
    layout_type: str,
    floor: str,
    drawing_path: str = "",
    notes: str = "",
) -> int:
    layout_uuid = str(uuid.uuid4())
    with transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO project_layouts(
                project_id,layout_uuid,tower,flat_number,layout_type,
                floor,drawing_path,notes
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                int(project_id),
                layout_uuid,
                tower.strip(),
                flat_number.strip(),
                layout_type.strip(),
                floor.strip(),
                drawing_path.strip(),
                notes.strip(),
            ),
        )
        layout_id = int(cursor.lastrowid)

    add_timeline_event(
        project_id,
        "LAYOUT_ADDED",
        "Layout added",
        " · ".join(x for x in [tower, flat_number, layout_type] if x),
    )
    touch_project(project_id, "LAYOUT_ADDED")
    return layout_id

def update_layout(
    layout_id: int,
    *,
    tower: str,
    flat_number: str,
    layout_type: str,
    floor: str,
    analysis_status: str,
    notes: str,
) -> None:
    if analysis_status not in ANALYSIS_STATUSES:
        raise ValueError("Invalid analysis status.")
    with transaction() as connection:
        row = connection.execute(
            "SELECT project_id FROM project_layouts WHERE id=?",
            (int(layout_id),),
        ).fetchone()
        if not row:
            raise ValueError("Layout not found.")
        connection.execute(
            """
            UPDATE project_layouts SET
                tower=?,flat_number=?,layout_type=?,floor=?,
                analysis_status=?,notes=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                tower.strip(),
                flat_number.strip(),
                layout_type.strip(),
                floor.strip(),
                analysis_status,
                notes.strip(),
                int(layout_id),
            ),
        )
    add_timeline_event(
        int(row["project_id"]),
        "LAYOUT_UPDATED",
        "Layout updated",
        f"Layout ID {layout_id}; status {analysis_status}",
    )

def delete_layout(layout_id: int) -> None:
    with transaction() as connection:
        row = connection.execute(
            "SELECT * FROM project_layouts WHERE id=?",
            (int(layout_id),),
        ).fetchone()
        if not row:
            return
        connection.execute(
            "DELETE FROM project_layouts WHERE id=?",
            (int(layout_id),),
        )
    drawing = Path(row["drawing_path"]) if row["drawing_path"] else None
    if drawing and drawing.exists():
        drawing.unlink()
    add_timeline_event(
        int(row["project_id"]),
        "LAYOUT_DELETED",
        "Layout deleted",
        row["flat_number"] or f"Layout ID {layout_id}",
    )

def list_layouts(project_id: int):
    with connect() as connection:
        return connection.execute(
            """
            SELECT * FROM project_layouts
            WHERE project_id=?
            ORDER BY tower,floor,flat_number,id
            """,
            (int(project_id),),
        ).fetchall()

def save_layout_drawing(project_id: int, uploaded_file) -> str:
    project = get_project(project_id)
    if not project:
        raise ValueError("Project not found.")
    data = uploaded_file.getvalue()
    drawing_uuid = str(uuid.uuid4())
    name = Path(uploaded_file.name).name
    folder = Path(project["project_folder"]) / "layouts"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{drawing_uuid[:8]}_{name}"
    STORAGE.save_bytes(destination, data, overwrite=False)
    return str(destination)

def dashboard_metrics(project_id: int) -> dict:
    with connect() as connection:
        document_count = connection.execute(
            "SELECT COUNT(*) v FROM project_documents WHERE project_id=?",
            (int(project_id),),
        ).fetchone()["v"]
        layout_count = connection.execute(
            "SELECT COUNT(*) v FROM project_layouts WHERE project_id=?",
            (int(project_id),),
        ).fetchone()["v"]
        analysed = connection.execute(
            """
            SELECT COUNT(*) v FROM project_layouts
            WHERE project_id=? AND analysis_status='Completed'
            """,
            (int(project_id),),
        ).fetchone()["v"]
        needs_review = connection.execute(
            """
            SELECT COUNT(*) v FROM project_layouts
            WHERE project_id=? AND analysis_status='Needs Review'
            """,
            (int(project_id),),
        ).fetchone()["v"]
        pending = layout_count - analysed
        average_score = connection.execute(
            """
            SELECT AVG(overall_score) v FROM project_layouts
            WHERE project_id=? AND overall_score IS NOT NULL
            """,
            (int(project_id),),
        ).fetchone()["v"]
    return {
        "documents": int(document_count),
        "layouts": int(layout_count),
        "analysed": int(analysed),
        "pending": int(pending),
        "needs_review": int(needs_review),
        "average_score": float(average_score) if average_score is not None else None,
    }

def add_timeline_event(
    project_id: int,
    event_type: str,
    title: str,
    details: str = "",
) -> None:
    with transaction() as connection:
        connection.execute(
            """
            INSERT INTO project_timeline(project_id,event_type,title,details)
            VALUES(?,?,?,?)
            """,
            (int(project_id), event_type, title, details),
        )

def list_timeline(project_id: int, limit: int = 100):
    with connect() as connection:
        return connection.execute(
            """
            SELECT * FROM project_timeline
            WHERE project_id=?
            ORDER BY id DESC LIMIT ?
            """,
            (int(project_id), int(limit)),
        ).fetchall()
