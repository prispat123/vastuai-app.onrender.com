from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from assessment_core import build_snapshot
from assessment_core.record_compatibility import normalize_professional_result
from knowledge_engine.importer import runtime_status
from platform_core.database import connect, initialize_database, transaction
from professional_app.version import __version__
from professional_app.services.buyer_workspace_service import link_pdp_to_buyer

CURRENT_SCHEMA_VERSION = 3


def _unique(values) -> list[str]:
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in output:
            output.append(text)
    return output


def build_profile(project_id: int, analysis_id: int, payload: dict[str, Any], stored_result: dict[str, Any]) -> dict[str, Any]:
    """Build the canonical PDP from the same snapshot used by reports."""
    result = normalize_professional_result(stored_result)
    snapshot = build_snapshot(payload=payload, professional_result=result)

    final = result.get("final_result", {}) or {}
    vastu = result.get("vastu_result", {}) or {}
    numerology = result.get("numerology_result", {}) or {}
    recommendation = result.get("recommendation_result", {}) or {}

    vastu_knowledge = snapshot["vastu"].get("knowledge", {}) or {}
    numerology_knowledge = snapshot["numerology"].get("knowledge_result", {}) or {}
    vastu_ids = _unique(snapshot["vastu"].get("knowledge_ids", []))
    numerology_ids = _unique(snapshot["numerology"].get("knowledge_ids", []))

    status = runtime_status()
    vastu_version = str((status.get("meta") or {}).get("knowledge_version") or "")
    numerology_version = str(numerology_knowledge.get("knowledge_version") or numerology.get("knowledge_version") or "")
    details = list(vastu.get("details", []) or [])
    critical_high = [row for row in details if str(row.get("severity", "")).strip().lower() in {"critical", "high"}]

    profile = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "entity_type": "property_decision_profile",
        "project_id": int(project_id),
        "analysis_id": int(analysis_id),
        "buyer": {
            "owner_name": str(payload.get("owner_name") or ""),
            "date_of_birth": str(payload.get("dob") or ""),
        },
        "property": {
            "property_name": str(payload.get("property_name") or ""),
            "property_number": str(payload.get("flat_number") or ""),
            "assessment_year": payload.get("assessment_year"),
        },
        "overall_professional": {
            "score": final.get("score"),
            "score_100": final.get("score_100"),
            "rating": final.get("rating"),
            "colour_band": final.get("colour_band"),
            "basis": final.get("basis"),
            "weights": final.get("weights"),
            "footnote": final.get("footnote"),
        },
        "vastu": {
            "score": vastu.get("score"),
            "grade": vastu.get("grade"),
            "status": vastu.get("status"),
            "coverage": vastu.get("coverage"),
            "confidence": vastu.get("confidence"),
            "evaluated_count": vastu.get("evaluated_count", len(details)),
            "critical_high_count": len(critical_high),
            "strengths": list(vastu.get("strengths", []) or []),
            "cautions": list(vastu.get("cautions", []) or []),
            "knowledge_ids": vastu_ids,
            "knowledge_count": len(vastu_ids),
            "knowledge_profile": vastu_knowledge.get("profile_name") or vastu_knowledge.get("profile") or "",
            "knowledge_confidence": vastu_knowledge.get("average_confidence"),
            "knowledge_summary": vastu_knowledge.get("reasoning_summary", ""),
            "knowledge_findings": [
                {k: row.get(k) for k in ("rule_id", "title", "category", "field", "direction", "polarity", "severity")}
                for row in vastu_knowledge.get("findings", [])
            ],
        },
        "numerology": {
            "score": numerology.get("score"),
            "score_100": numerology.get("score_100"),
            "grade": numerology.get("grade") or numerology_knowledge.get("grade"),
            "confidence": numerology.get("confidence") or numerology_knowledge.get("confidence"),
            "knowledge_ids": numerology_ids,
            "knowledge_count": len(numerology_ids),
            "knowledge_version": numerology_version,
            "calculated_numbers": numerology_knowledge.get("calculated_numbers", {}),
            "knowledge_findings": [
                {k: row.get(k) for k in ("object_id", "domain", "title", "polarity", "severity")}
                for row in (list(numerology_knowledge.get("number_objects", []) or []) + list(numerology_knowledge.get("alignment_objects", []) or []))
            ],
        },
        "recommendation": {
            "decision": recommendation.get("decision"),
            "confidence": recommendation.get("confidence") or vastu.get("confidence"),
            "critical_issue_count": recommendation.get("critical_issue_count", len(critical_high)),
            "actions": list(recommendation.get("actions", []) or []),
        },
        "versions": {
            "platform": __version__,
            "vastu_knowledge": vastu_version,
            "numerology_knowledge": numerology_version,
        },
        "executive_summary": str(result.get("explanation") or ""),
        "audit": {
            "immutable_assessment": True,
            "source_analysis_id": int(analysis_id),
            "profile_schema_version": CURRENT_SCHEMA_VERSION,
            "creation_path": "automatic_persistence",
        },
    }
    raw = json.dumps(profile, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")
    profile["source_hash"] = hashlib.sha256(raw).hexdigest()
    return profile


def insert_profile(connection, project_id: int, analysis_id: int, payload: dict, stored_result: dict) -> dict:
    profile = build_profile(project_id, analysis_id, payload, stored_result)
    cursor = connection.execute(
        """INSERT INTO property_decision_profiles(
            decision_id,project_id,analysis_id,owner_name,property_name,
            property_number,source_hash,overall_score,overall_rating,profile_json
        ) VALUES('',?,?,?,?,?,?,?,?,?)""",
        (int(project_id), int(analysis_id), profile["buyer"]["owner_name"], profile["property"]["property_name"], profile["property"]["property_number"], profile["source_hash"], float(profile["overall_professional"].get("score") or 0), str(profile["overall_professional"].get("rating") or ""), json.dumps(profile, ensure_ascii=False, default=str)),
    )
    row_id = int(cursor.lastrowid)
    decision_id = f"PDP-{datetime.now().year}-{row_id:06d}"
    profile["decision_id"] = decision_id
    connection.execute(
        "UPDATE property_decision_profiles "
        "SET decision_id=?,profile_json=? WHERE id=?",
        (
            decision_id,
            json.dumps(profile, ensure_ascii=False, default=str),
            row_id,
        ),
    )
    buyer_id = link_pdp_to_buyer(
        connection,
        pdp_id=row_id,
        profile=profile,
    )
    return {
        "id": row_id,
        "decision_id": decision_id,
        "buyer_id": buyer_id,
        "profile": profile,
    }


def create_profile(project_id: int, analysis_id: int, payload: dict, stored_result: dict) -> dict:
    initialize_database()
    with transaction() as connection:
        return insert_profile(connection, project_id, analysis_id, payload, stored_result)


def latest_for_analysis(analysis_id: int) -> dict | None:
    initialize_database()
    with connect() as connection:
        row = connection.execute("SELECT * FROM property_decision_profiles WHERE analysis_id=? ORDER BY id DESC LIMIT 1", (int(analysis_id),)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["profile"] = json.loads(item.pop("profile_json") or "{}")
    return item


def backfill_missing_profiles(project_id: int) -> dict[str, Any]:
    initialize_database()
    with connect() as connection:
        rows = connection.execute(
            """SELECT pa.id,pa.payload_json,pa.result_json
               FROM professional_analyses pa
               WHERE pa.project_id=?
                 AND NOT EXISTS(SELECT 1 FROM property_decision_profiles pdp WHERE pdp.analysis_id=pa.id AND pdp.project_id=pa.project_id)
               ORDER BY pa.id""", (int(project_id),)).fetchall()
    created, failures = [], []
    for row in rows:
        try:
            pdp = create_profile(int(project_id), int(row["id"]), json.loads(row["payload_json"] or "{}"), json.loads(row["result_json"] or "{}"))
            created.append(pdp["decision_id"])
        except Exception as exc:
            failures.append({"analysis_id": str(row["id"]), "error": str(exc)})
    return {"eligible": len(rows), "created_count": len(created), "created": created, "failure_count": len(failures), "failures": failures}


def _needs_enrichment(profile: dict) -> bool:
    if int(profile.get("schema_version") or 0) < CURRENT_SCHEMA_VERSION:
        return True
    vastu = profile.get("vastu", {}) or {}
    numerology = profile.get("numerology", {}) or {}
    if vastu.get("score") is not None and not vastu.get("knowledge_ids"):
        return True
    if numerology.get("score_100") is not None and not numerology.get("knowledge_ids"):
        return True
    return False


def enrich_existing_profiles(project_id: int) -> dict[str, Any]:
    """Enrich PDP metadata from the original saved assessment without changing its Decision ID."""
    initialize_database()
    updated, failures = [], []
    with transaction() as connection:
        rows = connection.execute("SELECT id,decision_id,analysis_id,profile_json FROM property_decision_profiles WHERE project_id=? ORDER BY id", (int(project_id),)).fetchall()
        for row in rows:
            try:
                current = json.loads(row["profile_json"] or "{}")
                if not _needs_enrichment(current):
                    continue
                source = connection.execute("SELECT payload_json,result_json FROM professional_analyses WHERE id=? AND project_id=?", (int(row["analysis_id"]), int(project_id))).fetchone()
                if not source:
                    failures.append({"decision_id": row["decision_id"], "error": "Source assessment not found."})
                    continue
                rebuilt = build_profile(int(project_id), int(row["analysis_id"]), json.loads(source["payload_json"] or "{}"), json.loads(source["result_json"] or "{}"))
                rebuilt["decision_id"] = row["decision_id"]
                rebuilt["audit"]["creation_path"] = "schema_enrichment_from_source_assessment"
                connection.execute("""UPDATE property_decision_profiles SET owner_name=?,property_name=?,property_number=?,source_hash=?,overall_score=?,overall_rating=?,profile_json=? WHERE id=?""", (rebuilt["buyer"]["owner_name"], rebuilt["property"]["property_name"], rebuilt["property"]["property_number"], rebuilt["source_hash"], float(rebuilt["overall_professional"].get("score") or 0), str(rebuilt["overall_professional"].get("rating") or ""), json.dumps(rebuilt, ensure_ascii=False, default=str), int(row["id"])))
                updated.append(row["decision_id"])
            except Exception as exc:
                failures.append({"decision_id": str(row["decision_id"]), "error": str(exc)})
    return {"updated_count": len(updated), "updated": updated, "failure_count": len(failures), "failures": failures}


def list_profiles(project_id: int) -> list[dict]:
    initialize_database()
    with connect() as connection:
        return [dict(row) for row in connection.execute("""SELECT id,decision_id,analysis_id,owner_name,property_name,property_number,overall_score,overall_rating,created_at FROM property_decision_profiles WHERE project_id=? ORDER BY id DESC""", (int(project_id),)).fetchall()]


def get_profile(decision_id: str) -> dict | None:
    initialize_database()
    with connect() as connection:
        row = connection.execute("SELECT * FROM property_decision_profiles WHERE decision_id=?", (decision_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["profile"] = json.loads(item.pop("profile_json") or "{}")
    return item
