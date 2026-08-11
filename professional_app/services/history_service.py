from __future__ import annotations

import json
from typing import Any

from platform_core.database import connect, transaction
from assessment_core.record_compatibility import normalize_professional_result
from professional_app.services import pdp_service

_ACTIVE_PROJECT_ID: int | None = None

def set_active_project(project_id: int) -> None:
    global _ACTIVE_PROJECT_ID
    _ACTIVE_PROJECT_ID = int(project_id)

def _project_id() -> int:
    if _ACTIVE_PROJECT_ID is None:
        raise RuntimeError("No Professional project is active.")
    return _ACTIVE_PROJECT_ID

def save_analysis(payload: dict[str, Any], result: dict[str, Any]) -> int:
    final = result.get("final_result", {})
    vastu = result.get("vastu_result", {})
    numerology = result.get("numerology_result", {})
    recommendation = result.get("recommendation_result", {})
    label = str(payload.get("property_name") or payload.get("flat_number") or "Unnamed property")
    project_id = _project_id()
    with transaction() as conn:
        cursor = conn.execute(
            """
            INSERT INTO professional_analyses(
                project_id,property_label,owner_name,flat_number,
                overall_score,vastu_score,numerology_score,confidence,
                payload_json,result_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                project_id, label, payload.get("owner_name", ""),
                payload.get("flat_number", ""),
                float(final.get("score", 0) or 0),
                float(vastu.get("score", 0) or 0) if vastu else None,
                float(numerology.get("score", 0) or 0) if numerology else None,
                recommendation.get("confidence") or vastu.get("confidence") or "N/A",
                json.dumps(payload, ensure_ascii=False, default=str),
                json.dumps(result, ensure_ascii=False, default=str),
            ),
        )
        analysis_id = int(cursor.lastrowid)

    # Build the canonical PDP after the assessment write transaction commits.
    # The Knowledge engines may initialize/read SQLite metadata and must not
    # run while another write transaction is held. Missing PDPs are safely
    # recoverable through Decision Profiles backfill.
    pdp_service.create_profile(
        project_id,
        analysis_id,
        payload,
        result,
    )
    return analysis_id

def update_analysis(analysis_id: int, payload: dict[str, Any], result: dict[str, Any]) -> None:
    final = result.get("final_result", {})
    vastu = result.get("vastu_result", {})
    numerology = result.get("numerology_result", {})
    recommendation = result.get("recommendation_result", {})
    label = str(payload.get("property_name") or payload.get("flat_number") or "Unnamed property")
    project_id = _project_id()
    with transaction() as conn:
        conn.execute(
            """
            UPDATE professional_analyses SET
                property_label=?,owner_name=?,flat_number=?,overall_score=?,
                vastu_score=?,numerology_score=?,confidence=?,
                payload_json=?,result_json=?
            WHERE id=? AND project_id=?
            """,
            (
                label,payload.get("owner_name",""),payload.get("flat_number",""),
                float(final.get("score",0) or 0),
                float(vastu.get("score",0) or 0) if vastu else None,
                float(numerology.get("score",0) or 0) if numerology else None,
                recommendation.get("confidence") or vastu.get("confidence") or "N/A",
                json.dumps(payload,ensure_ascii=False,default=str),
                json.dumps(result,ensure_ascii=False,default=str),
                int(analysis_id),project_id,
            ),
        )
    # A reassessment creates a new immutable PDP version after the source
    # assessment transaction commits, avoiding nested Knowledge-engine DB
    # initialization while a write lock is held.
    pdp_service.create_profile(
        project_id,
        int(analysis_id),
        payload,
        result,
    )

def list_analyses(limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        rows=conn.execute(
            """SELECT * FROM professional_analyses
            WHERE project_id=? ORDER BY id DESC LIMIT ?""",
            (_project_id(),int(limit)),
        ).fetchall()
    return [dict(row) for row in rows]

def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row=conn.execute(
            "SELECT * FROM professional_analyses WHERE id=? AND project_id=?",
            (int(analysis_id),_project_id()),
        ).fetchone()
    if row is None:return None
    item=dict(row)
    item["payload"]=json.loads(item.pop("payload_json"))
    item["result"]=normalize_professional_result(
        json.loads(item.pop("result_json"))
    )
    return item

def delete_analysis(analysis_id: int) -> None:
    with transaction() as conn:
        conn.execute(
            "DELETE FROM professional_analyses WHERE id=? AND project_id=?",
            (int(analysis_id),_project_id()),
        )

def update_metadata(analysis_id: int, workflow_status: str, tags: str, consultant_notes: str) -> None:
    with transaction() as conn:
        conn.execute(
            """UPDATE professional_analyses
            SET workflow_status=?,tags=?,consultant_notes=?
            WHERE id=? AND project_id=?""",
            (
                workflow_status.strip() or "Draft",tags.strip(),
                consultant_notes.strip(),int(analysis_id),_project_id()
            ),
        )
