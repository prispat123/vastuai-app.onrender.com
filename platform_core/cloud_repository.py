from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from platform_core import auth


def enabled() -> bool:
    return bool(auth.configured() and auth.current_user() is not None and auth.user_id())


def _table(name: str):
    if not enabled():
        raise RuntimeError("Authenticated Supabase session required.")
    return auth.client().table(name)



_TRANSIENT_HTTP_ERRORS = {
    "RemoteProtocolError",
    "ReadError",
    "ConnectError",
    "ReadTimeout",
    "ConnectTimeout",
    "WriteError",
    "PoolTimeout",
}


def _is_transient_transport_error(exc: Exception) -> bool:
    cls = exc.__class__
    return cls.__name__ in _TRANSIENT_HTTP_ERRORS and cls.__module__.startswith("httpx")


def _execute(builder_factory, attempts: int = 3):
    """Execute a Supabase/PostgREST request with short transient-network retries.

    builder_factory must rebuild the query each attempt because PostgREST
    request builders are single-use. Authentication and RLS remain unchanged.
    """
    last_exc = None
    for attempt in range(attempts):
        try:
            return builder_factory().execute()
        except Exception as exc:
            last_exc = exc
            if not _is_transient_transport_error(exc) or attempt >= attempts - 1:
                raise
            time.sleep(0.35 * (attempt + 1))
    raise last_exc


def _uid() -> str:
    uid = auth.user_id()
    if not uid:
        raise RuntimeError("Authentication required.")
    return uid


def next_legacy_analysis_id() -> int:
    response = _execute(lambda: (
        _table("professional_analyses")
        .select("legacy_analysis_id")
        .eq("user_id", _uid())
        .not_.is_("legacy_analysis_id", "null")
        .order("legacy_analysis_id", desc=True)
        .limit(1)
    ))
    rows = list(response.data or [])
    return int(rows[0]["legacy_analysis_id"]) + 1 if rows else 1


def _to_legacy_row(row: dict[str, Any]) -> dict[str, Any]:
    prop = dict(row.get("property_data") or {})
    result = dict(row.get("assessment_data") or {})
    return {
        "id": int(row.get("legacy_analysis_id") or 0),
        "cloud_id": str(row.get("id") or ""),
        "project_id": int(row.get("legacy_project_id") or 0),
        "property_label": str(row.get("property_name") or "Unnamed property"),
        "owner_name": str(prop.get("owner_name") or ""),
        "flat_number": str(prop.get("flat_number") or ""),
        "overall_score": row.get("overall_score"),
        "vastu_score": row.get("vastu_score"),
        "numerology_score": row.get("numerology_score"),
        "confidence": row.get("confidence") or "N/A",
        "workflow_status": row.get("workflow_status") or "Draft",
        "tags": row.get("tags") or "",
        "consultant_notes": row.get("consultant_notes") or "",
        "payload_json": json.dumps(prop, ensure_ascii=False, default=str),
        "result_json": json.dumps(result, ensure_ascii=False, default=str),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "status": row.get("status") or "active",
    }


def save_professional_analysis(*, legacy_project_id: int, payload: dict[str, Any], result: dict[str, Any]) -> int:
    final = result.get("final_result", {}) or {}
    vastu = result.get("vastu_result", {}) or {}
    numerology = result.get("numerology_result", {}) or {}
    recommendation = result.get("recommendation_result", {}) or {}
    legacy_id = next_legacy_analysis_id()
    label = str(payload.get("property_name") or payload.get("flat_number") or "Unnamed property")
    response = _execute(lambda: _table("professional_analyses").insert({
        "user_id": _uid(),
        "legacy_analysis_id": legacy_id,
        "legacy_project_id": int(legacy_project_id),
        "property_name": label,
        "property_data": payload,
        "assessment_data": result,
        "overall_score": float(final.get("score", 0) or 0),
        "vastu_score": float(vastu.get("score", 0) or 0) if vastu else None,
        "numerology_score": float(numerology.get("score", 0) or 0) if numerology else None,
        "confidence": recommendation.get("confidence") or vastu.get("confidence") or "N/A",
        "status": "active",
    }))
    if not response.data:
        raise RuntimeError("Supabase did not return the saved Professional assessment.")
    return legacy_id


def update_professional_analysis(legacy_analysis_id: int, *, legacy_project_id: int, payload: dict[str, Any], result: dict[str, Any]) -> None:
    final = result.get("final_result", {}) or {}
    vastu = result.get("vastu_result", {}) or {}
    numerology = result.get("numerology_result", {}) or {}
    recommendation = result.get("recommendation_result", {}) or {}
    label = str(payload.get("property_name") or payload.get("flat_number") or "Unnamed property")
    _execute(lambda: (
        _table("professional_analyses")
        .update({
            "legacy_project_id": int(legacy_project_id),
            "property_name": label,
            "property_data": payload,
            "assessment_data": result,
            "overall_score": float(final.get("score", 0) or 0),
            "vastu_score": float(vastu.get("score", 0) or 0) if vastu else None,
            "numerology_score": float(numerology.get("score", 0) or 0) if numerology else None,
            "confidence": recommendation.get("confidence") or vastu.get("confidence") or "N/A",
        })
        .eq("user_id", _uid())
        .eq("legacy_analysis_id", int(legacy_analysis_id))
    ))


def list_professional_analyses(limit: int = 100, legacy_project_id: int | None = None) -> list[dict[str, Any]]:
    query = (
        _table("professional_analyses")
        .select("*")
        .eq("user_id", _uid())
        .order("legacy_analysis_id", desc=True)
        .limit(int(limit))
    )
    # The Professional product is property-centric. Project IDs from the
    # ephemeral compatibility layer must never hide a user's permanent data.
    response = _execute(lambda: (
        _table("professional_analyses")
        .select("*")
        .eq("user_id", _uid())
        .order("legacy_analysis_id", desc=True)
        .limit(int(limit))
    ))
    return [_to_legacy_row(dict(row)) for row in (response.data or [])]


def get_professional_analysis(legacy_analysis_id: int) -> dict[str, Any] | None:
    response = _execute(lambda: (
        _table("professional_analyses")
        .select("*")
        .eq("user_id", _uid())
        .eq("legacy_analysis_id", int(legacy_analysis_id))
        .limit(1)
    ))
    rows = list(response.data or [])
    return _to_legacy_row(dict(rows[0])) if rows else None


def delete_professional_analysis(legacy_analysis_id: int) -> None:
    _execute(lambda: (
        _table("professional_analyses")
        .delete()
        .eq("user_id", _uid())
        .eq("legacy_analysis_id", int(legacy_analysis_id))
    ))


def update_professional_metadata(legacy_analysis_id: int, workflow_status: str, tags: str, consultant_notes: str) -> None:
    _execute(lambda: (
        _table("professional_analyses")
        .update({
            "workflow_status": workflow_status.strip() or "Draft",
            "tags": tags.strip(),
            "consultant_notes": consultant_notes.strip(),
        })
        .eq("user_id", _uid())
        .eq("legacy_analysis_id", int(legacy_analysis_id))
    ))


def _analysis_cloud_uuid(legacy_analysis_id: int) -> str | None:
    response = _execute(lambda: (
        _table("professional_analyses")
        .select("id")
        .eq("user_id", _uid())
        .eq("legacy_analysis_id", int(legacy_analysis_id))
        .limit(1)
    ))
    rows = list(response.data or [])
    return str(rows[0]["id"]) if rows else None


def create_pdp(legacy_analysis_id: int, profile: dict[str, Any]) -> dict[str, Any]:
    analysis_uuid = _analysis_cloud_uuid(legacy_analysis_id)
    if not analysis_uuid:
        raise RuntimeError("Cloud source assessment not found.")
    existing = _execute(lambda: (
        _table("property_decision_profiles")
        .select("id,profile_data,created_at")
        .eq("user_id", _uid())
        .eq("analysis_id", analysis_uuid)
        .order("created_at", desc=False)
    ))
    version = len(existing.data or []) + 1
    decision_id = f"PDP-{datetime.now().year}-{int(legacy_analysis_id):06d}-{version:02d}"
    cloud_profile = dict(profile)
    cloud_profile["decision_id"] = decision_id
    response = _execute(lambda: _table("property_decision_profiles").insert({
        "user_id": _uid(),
        "analysis_id": analysis_uuid,
        "profile_data": cloud_profile,
    }))
    row = dict((response.data or [{}])[0])
    return {
        "id": str(row.get("id") or ""),
        "decision_id": decision_id,
        "buyer_id": None,
        "profile": cloud_profile,
    }


def latest_pdp_for_analysis(legacy_analysis_id: int) -> dict[str, Any] | None:
    analysis_uuid = _analysis_cloud_uuid(legacy_analysis_id)
    if not analysis_uuid:
        return None
    response = _execute(lambda: (
        _table("property_decision_profiles")
        .select("*")
        .eq("user_id", _uid())
        .eq("analysis_id", analysis_uuid)
        .order("created_at", desc=True)
        .limit(1)
    ))
    rows = list(response.data or [])
    if not rows:
        return None
    row = dict(rows[0])
    profile = dict(row.get("profile_data") or {})
    return {
        "id": str(row.get("id") or ""),
        "decision_id": str(profile.get("decision_id") or ""),
        "analysis_id": int(legacy_analysis_id),
        "profile": profile,
        "created_at": row.get("created_at"),
    }


def list_pdps() -> list[dict[str, Any]]:
    # Fetch user-owned PDPs and resolve their source legacy IDs.
    response = _execute(lambda: (
        _table("property_decision_profiles")
        .select("*")
        .eq("user_id", _uid())
        .order("created_at", desc=True)
    ))
    output = []
    for row in (response.data or []):
        profile = dict(row.get("profile_data") or {})
        legacy_id = int(((profile.get("audit") or {}).get("source_analysis_id")) or profile.get("analysis_id") or 0)
        output.append({
            "id": str(row.get("id") or ""),
            "decision_id": str(profile.get("decision_id") or ""),
            "analysis_id": legacy_id,
            "owner_name": str((profile.get("buyer") or {}).get("owner_name") or ""),
            "property_name": str((profile.get("property") or {}).get("property_name") or ""),
            "property_number": str((profile.get("property") or {}).get("property_number") or ""),
            "overall_score": (profile.get("overall_professional") or {}).get("score"),
            "overall_rating": str((profile.get("overall_professional") or {}).get("rating") or ""),
            "created_at": row.get("created_at"),
        })
    return output


def get_pdp(decision_id: str) -> dict[str, Any] | None:
    # PostgREST JSON-path filters differ across client versions; fetch only
    # the authenticated user's PDPs and match the small list in-process.
    response = _execute(lambda: (
        _table("property_decision_profiles")
        .select("*")
        .eq("user_id", _uid())
        .order("created_at", desc=True)
    ))
    for row in (response.data or []):
        profile = dict(row.get("profile_data") or {})
        if str(profile.get("decision_id") or "") == str(decision_id):
            return {
                "id": str(row.get("id") or ""),
                "decision_id": str(decision_id),
                "analysis_id": int(((profile.get("audit") or {}).get("source_analysis_id")) or 0),
                "profile": profile,
                "created_at": row.get("created_at"),
            }
    return None
