from __future__ import annotations

import json
from typing import Any

from platform_core.database import connect, transaction
from platform_core import cloud_repository
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

def _cloud() -> bool:
    return cloud_repository.enabled()

def save_analysis(payload: dict[str, Any], result: dict[str, Any]) -> int:
    if _cloud():
        analysis_id = cloud_repository.save_professional_analysis(
            legacy_project_id=_project_id(), payload=payload, result=result
        )
        pdp_service.create_profile(_project_id(), analysis_id, payload, result)
        return int(analysis_id)

    final = result.get("final_result", {})
    vastu = result.get("vastu_result", {})
    numerology = result.get("numerology_result", {})
    recommendation = result.get("recommendation_result", {})
    label = str(payload.get("property_name") or payload.get("flat_number") or "Unnamed property")
    project_id = _project_id()
    with transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO professional_analyses(
                project_id,property_label,owner_name,flat_number,
                overall_score,vastu_score,numerology_score,confidence,
                payload_json,result_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (project_id,label,payload.get("owner_name",""),payload.get("flat_number",""),
             float(final.get("score",0) or 0),
             float(vastu.get("score",0) or 0) if vastu else None,
             float(numerology.get("score",0) or 0) if numerology else None,
             recommendation.get("confidence") or vastu.get("confidence") or "N/A",
             json.dumps(payload,ensure_ascii=False,default=str),
             json.dumps(result,ensure_ascii=False,default=str))
        )
        analysis_id=int(cursor.lastrowid)
    pdp_service.create_profile(project_id,analysis_id,payload,result)
    return analysis_id

def update_analysis(analysis_id: int, payload: dict[str, Any], result: dict[str, Any]) -> None:
    if _cloud():
        cloud_repository.update_professional_analysis(
            int(analysis_id), legacy_project_id=_project_id(), payload=payload, result=result
        )
        pdp_service.create_profile(_project_id(), int(analysis_id), payload, result)
        return

    final=result.get("final_result",{}); vastu=result.get("vastu_result",{})
    numerology=result.get("numerology_result",{}); recommendation=result.get("recommendation_result",{})
    label=str(payload.get("property_name") or payload.get("flat_number") or "Unnamed property")
    project_id=_project_id()
    with transaction() as conn:
        conn.execute("""UPDATE professional_analyses SET
            property_label=?,owner_name=?,flat_number=?,overall_score=?,
            vastu_score=?,numerology_score=?,confidence=?,payload_json=?,result_json=?
            WHERE id=? AND project_id=?""",
            (label,payload.get("owner_name",""),payload.get("flat_number",""),
             float(final.get("score",0) or 0),
             float(vastu.get("score",0) or 0) if vastu else None,
             float(numerology.get("score",0) or 0) if numerology else None,
             recommendation.get("confidence") or vastu.get("confidence") or "N/A",
             json.dumps(payload,ensure_ascii=False,default=str),
             json.dumps(result,ensure_ascii=False,default=str),
             int(analysis_id),project_id))
    pdp_service.create_profile(project_id,int(analysis_id),payload,result)

def list_analyses(limit: int = 100) -> list[dict[str, Any]]:
    if _cloud():
        return cloud_repository.list_professional_analyses(limit=int(limit), legacy_project_id=_project_id())
    with connect() as conn:
        rows=conn.execute("""SELECT * FROM professional_analyses
            WHERE project_id=? ORDER BY id DESC LIMIT ?""",(_project_id(),int(limit))).fetchall()
    return [dict(row) for row in rows]

def get_analysis(analysis_id: int) -> dict[str, Any] | None:
    if _cloud():
        item=cloud_repository.get_professional_analysis(int(analysis_id))
        if item is None: return None
    else:
        with connect() as conn:
            row=conn.execute("SELECT * FROM professional_analyses WHERE id=? AND project_id=?",
                             (int(analysis_id),_project_id())).fetchone()
        if row is None:return None
        item=dict(row)
    item["payload"]=json.loads(item.pop("payload_json"))
    item["result"]=normalize_professional_result(json.loads(item.pop("result_json")))
    return item

def delete_analysis(analysis_id: int) -> None:
    if _cloud():
        cloud_repository.delete_professional_analysis(int(analysis_id)); return
    with transaction() as conn:
        conn.execute("DELETE FROM professional_analyses WHERE id=? AND project_id=?",
                     (int(analysis_id),_project_id()))

def update_metadata(analysis_id: int, workflow_status: str, tags: str, consultant_notes: str) -> None:
    if _cloud():
        cloud_repository.update_professional_metadata(
            int(analysis_id),workflow_status,tags,consultant_notes
        ); return
    with transaction() as conn:
        conn.execute("""UPDATE professional_analyses SET workflow_status=?,tags=?,consultant_notes=?
            WHERE id=? AND project_id=?""",
            (workflow_status.strip() or "Draft",tags.strip(),consultant_notes.strip(),
             int(analysis_id),_project_id()))
