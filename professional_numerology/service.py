from __future__ import annotations

import json

from assessment_core import build_snapshot
from numerology_engine import NumerologyRepository
from platform_core.database import connect, initialize_database, transaction


def _ensure_schema() -> None:
    initialize_database()
    with connect() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(professional_numerology_assessments)"
            ).fetchall()
        }
    if "analysis_id" not in columns:
        with transaction() as connection:
            connection.execute(
                "ALTER TABLE professional_numerology_assessments "
                "ADD COLUMN analysis_id INTEGER"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_professional_numerology_analysis "
                "ON professional_numerology_assessments(analysis_id,id DESC)"
            )


def repository() -> NumerologyRepository:
    return NumerologyRepository()


def list_properties(project_id: int) -> list[dict]:
    _ensure_schema()
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id,property_label,owner_name,flat_number,
                   vastu_score,numerology_score,created_at
            FROM professional_analyses
            WHERE project_id=?
            ORDER BY id DESC
            """,
            (int(project_id),),
        ).fetchall()
    return [dict(row) for row in rows]


def get_property(project_id: int, analysis_id: int) -> dict | None:
    _ensure_schema()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT * FROM professional_analyses
            WHERE id=? AND project_id=?
            """,
            (int(analysis_id), int(project_id)),
        ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["payload"] = json.loads(item.pop("payload_json") or "{}")
    item["result"] = json.loads(item.pop("result_json") or "{}")
    return item


def run_assessment(project_id: int, analysis_id: int) -> dict:
    saved = get_property(project_id, analysis_id)
    if not saved:
        raise ValueError("Saved Professional property was not found.")

    payload = saved["payload"]
    if not str(payload.get("dob") or "").strip():
        raise ValueError(
            "Date of birth is missing. Update it in Property Details."
        )
    if not str(payload.get("flat_number") or "").strip():
        raise ValueError(
            "Property number is missing. Update it in Property Details."
        )

    snapshot = build_snapshot(
        payload=payload,
        professional_result=saved["result"],
    )
    result = snapshot["numerology"]["knowledge_result"]

    with transaction() as connection:
        connection.execute(
            """
            INSERT INTO professional_numerology_assessments(
                project_id,analysis_id,knowledge_version,method_profile,
                input_hash,birth_number,life_path_number,property_number,
                numerology_score,grade,confidence,result_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(project_id), int(analysis_id),
                result["knowledge_version"], result["method_profile"],
                result["input_hash"],
                result["calculated_numbers"]["birth_number"],
                result["calculated_numbers"]["life_path_number"],
                result["calculated_numbers"]["property_number"],
                result["numerology_score"], result["grade"],
                result["confidence"],
                json.dumps(result, ensure_ascii=False),
            ),
        )
    return {"saved_property": saved, "snapshot": snapshot, "result": result}


def latest_assessment(project_id: int, analysis_id: int) -> dict | None:
    _ensure_schema()
    with connect() as connection:
        row = connection.execute(
            """
            SELECT * FROM professional_numerology_assessments
            WHERE project_id=? AND analysis_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (int(project_id), int(analysis_id)),
        ).fetchone()
    if not row:
        return None
    result = json.loads(row["result_json"] or "{}")
    result["assessment_id"] = int(row["id"])
    result["created_at"] = row["created_at"]
    return result
