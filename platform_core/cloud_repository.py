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



def _next_legacy_id(table: str, column: str) -> int:
    response = _execute(lambda: (
        _table(table)
        .select(column)
        .eq("user_id", _uid())
        .not_.is_(column, "null")
        .order(column, desc=True)
        .limit(1)
    ))
    rows = list(response.data or [])
    return int(rows[0][column]) + 1 if rows else 1


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalized_buyer_key(name: str, date_of_birth: str) -> str:
    import re as _re
    clean_name = _re.sub(r"[^a-z0-9]+", " ", _clean(name).lower()).strip()
    return f"{clean_name}|{_clean(date_of_birth)}"


def sync_cloud_buyers_from_pdps() -> dict[str, Any]:
    pdps = _execute(lambda: (
        _table("property_decision_profiles")
        .select("id,legacy_pdp_id,buyer_id,profile_data")
        .eq("user_id", _uid())
        .order("created_at", desc=False)
    ))
    linked, failures = 0, []
    for row in (pdps.data or []):
        if row.get("buyer_id"):
            continue
        profile = dict(row.get("profile_data") or {})
        buyer = dict(profile.get("buyer") or {})
        name = _clean(buyer.get("owner_name"))
        dob = _clean(buyer.get("date_of_birth"))
        if not name:
            failures.append({"pdp_id": row.get("legacy_pdp_id"), "error": "Buyer name is missing."})
            continue
        key = _normalized_buyer_key(name, dob)
        found = _execute(lambda key=key: (
            _table("buyers")
            .select("*")
            .eq("user_id", _uid())
            .eq("normalized_key", key)
            .limit(1)
        ))
        buyers = list(found.data or [])
        if buyers:
            buyer_row = dict(buyers[0])
        else:
            legacy_id = _next_legacy_id("buyers", "legacy_buyer_id")
            created = _execute(lambda: _table("buyers").insert({
                "user_id": _uid(),
                "legacy_buyer_id": legacy_id,
                "name": name,
                "date_of_birth": dob,
                "normalized_key": key,
                "buyer_data": {"buyer_name": name, "date_of_birth": dob},
                "status": "Active",
            }))
            buyer_row = dict((created.data or [{}])[0])
        _execute(lambda pdp_uuid=row["id"], buyer_uuid=buyer_row["id"]: (
            _table("property_decision_profiles")
            .update({"buyer_id": buyer_uuid})
            .eq("user_id", _uid())
            .eq("id", pdp_uuid)
        ))
        linked += 1
    return {"linked_count": linked, "failure_count": len(failures), "failures": failures}


def list_cloud_buyers() -> list[dict[str, Any]]:
    sync_cloud_buyers_from_pdps()
    buyers = _execute(lambda: (
        _table("buyers")
        .select("*")
        .eq("user_id", _uid())
        .eq("status", "Active")
        .order("name")
    ))
    output = []
    for row in (buyers.data or []):
        buyer_uuid = row["id"]
        pdps = _execute(lambda buyer_uuid=buyer_uuid: (
            _table("property_decision_profiles")
            .select("id")
            .eq("user_id", _uid())
            .eq("buyer_id", buyer_uuid)
        ))
        shortlist = _execute(lambda buyer_uuid=buyer_uuid: (
            _table("buyer_shortlists")
            .select("id")
            .eq("user_id", _uid())
            .eq("buyer_id", buyer_uuid)
            .eq("status", "Shortlisted")
        ))
        output.append({
            "id": int(row.get("legacy_buyer_id") or 0),
            "cloud_id": str(buyer_uuid),
            "buyer_uuid": str(buyer_uuid),
            "buyer_name": row.get("name") or "",
            "date_of_birth": row.get("date_of_birth") or "",
            "email": row.get("email") or "",
            "phone": row.get("phone") or "",
            "status": row.get("status") or "Active",
            "pdp_count": len(pdps.data or []),
            "shortlist_count": len(shortlist.data or []),
        })
    return output


def _cloud_buyer_by_legacy(legacy_buyer_id: int) -> dict[str, Any] | None:
    response = _execute(lambda: (
        _table("buyers")
        .select("*")
        .eq("user_id", _uid())
        .eq("legacy_buyer_id", int(legacy_buyer_id))
        .limit(1)
    ))
    rows = list(response.data or [])
    return dict(rows[0]) if rows else None


def _cloud_pdp_by_legacy(legacy_pdp_id: int) -> dict[str, Any] | None:
    response = _execute(lambda: (
        _table("property_decision_profiles")
        .select("*")
        .eq("user_id", _uid())
        .eq("legacy_pdp_id", int(legacy_pdp_id))
        .limit(1)
    ))
    rows = list(response.data or [])
    return dict(rows[0]) if rows else None


def get_cloud_buyer(legacy_buyer_id: int) -> dict[str, Any] | None:
    row = _cloud_buyer_by_legacy(legacy_buyer_id)
    if not row:
        return None
    return {
        "id": int(row.get("legacy_buyer_id") or 0),
        "cloud_id": str(row.get("id") or ""),
        "buyer_uuid": str(row.get("id") or ""),
        "buyer_name": row.get("name") or "",
        "date_of_birth": row.get("date_of_birth") or "",
        "email": row.get("email") or "",
        "phone": row.get("phone") or "",
        "status": row.get("status") or "Active",
    }


def cloud_buyer_for_pdp(legacy_pdp_id: int) -> dict[str, Any] | None:
    pdp = _cloud_pdp_by_legacy(legacy_pdp_id)
    if not pdp:
        return None
    if not pdp.get("buyer_id"):
        sync_cloud_buyers_from_pdps()
        pdp = _cloud_pdp_by_legacy(legacy_pdp_id)
    if not pdp or not pdp.get("buyer_id"):
        return None
    response = _execute(lambda: (
        _table("buyers")
        .select("*")
        .eq("user_id", _uid())
        .eq("id", pdp["buyer_id"])
        .limit(1)
    ))
    rows = list(response.data or [])
    if not rows:
        return None
    row = dict(rows[0])
    return {
        "id": int(row.get("legacy_buyer_id") or 0),
        "cloud_id": str(row.get("id") or ""),
        "buyer_uuid": str(row.get("id") or ""),
        "buyer_name": row.get("name") or "",
        "date_of_birth": row.get("date_of_birth") or "",
        "email": row.get("email") or "",
        "phone": row.get("phone") or "",
        "status": row.get("status") or "Active",
    }


def _enriched_cloud_pdp(row: dict[str, Any], *, shortlisted: bool = False, shortlist_row: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = dict(row.get("profile_data") or {})
    overall = dict(profile.get("overall_professional") or {})
    vastu = dict(profile.get("vastu") or {})
    numerology = dict(profile.get("numerology") or {})
    rec = dict(profile.get("recommendation") or {})
    prop = dict(profile.get("property") or {})
    item = {
        "id": int(row.get("legacy_pdp_id") or 0),
        "cloud_id": str(row.get("id") or ""),
        "decision_id": str(profile.get("decision_id") or ""),
        "analysis_id": int(((profile.get("audit") or {}).get("source_analysis_id")) or 0),
        "buyer_id": None,
        "project_name": str(prop.get("property_name") or ""),
        "project_city": "",
        "property_label": str(prop.get("property_name") or ""),
        "property_name": str(prop.get("property_name") or ""),
        "property_number": str(prop.get("property_number") or ""),
        "owner_name": str((profile.get("buyer") or {}).get("owner_name") or ""),
        "profile": profile,
        "overall_score": overall.get("score"),
        "overall_rating": overall.get("rating"),
        "vastu_score": vastu.get("score"),
        "vastu_grade": vastu.get("grade"),
        "numerology_score_100": numerology.get("score_100"),
        "numerology_grade": numerology.get("grade"),
        "critical_high_count": vastu.get("critical_high_count", 0),
        "recommendation": rec.get("decision"),
        "decision_confidence": rec.get("confidence"),
        "shortlisted": 1 if shortlisted else 0,
        "created_at": row.get("created_at"),
    }
    if shortlist_row:
        item["shortlist_item_id"] = int(shortlist_row.get("legacy_shortlist_id") or 0)
        item["shortlist_order"] = int(shortlist_row.get("shortlist_order") or 1)
        item["shortlist_notes"] = shortlist_row.get("notes") or ""
    return item


def list_cloud_buyer_pdps(legacy_buyer_id: int) -> list[dict[str, Any]]:
    buyer = _cloud_buyer_by_legacy(legacy_buyer_id)
    if not buyer:
        return []
    pdps = _execute(lambda: (
        _table("property_decision_profiles")
        .select("*")
        .eq("user_id", _uid())
        .eq("buyer_id", buyer["id"])
        .order("created_at", desc=True)
    ))
    shortlist = _execute(lambda: (
        _table("buyer_shortlists")
        .select("*")
        .eq("user_id", _uid())
        .eq("buyer_id", buyer["id"])
        .eq("status", "Shortlisted")
    ))
    short_by_pdp = {row["pdp_id"]: dict(row) for row in (shortlist.data or [])}
    return [
        _enriched_cloud_pdp(dict(row), shortlisted=row["id"] in short_by_pdp, shortlist_row=short_by_pdp.get(row["id"]))
        for row in (pdps.data or [])
    ]


def list_cloud_shortlist(legacy_buyer_id: int) -> list[dict[str, Any]]:
    buyer = _cloud_buyer_by_legacy(legacy_buyer_id)
    if not buyer:
        return []
    shortlist = _execute(lambda: (
        _table("buyer_shortlists")
        .select("*")
        .eq("user_id", _uid())
        .eq("buyer_id", buyer["id"])
        .eq("status", "Shortlisted")
        .order("shortlist_order")
    ))
    output = []
    for short in (shortlist.data or []):
        pdp_resp = _execute(lambda pdp_uuid=short["pdp_id"]: (
            _table("property_decision_profiles")
            .select("*")
            .eq("user_id", _uid())
            .eq("id", pdp_uuid)
            .limit(1)
        ))
        rows = list(pdp_resp.data or [])
        if rows:
            output.append(_enriched_cloud_pdp(dict(rows[0]), shortlisted=True, shortlist_row=dict(short)))
    return output


def cloud_is_shortlisted(legacy_buyer_id: int, legacy_pdp_id: int) -> bool:
    buyer = _cloud_buyer_by_legacy(legacy_buyer_id)
    pdp = _cloud_pdp_by_legacy(legacy_pdp_id)
    if not buyer or not pdp:
        return False
    response = _execute(lambda: (
        _table("buyer_shortlists")
        .select("id")
        .eq("user_id", _uid())
        .eq("buyer_id", buyer["id"])
        .eq("pdp_id", pdp["id"])
        .eq("status", "Shortlisted")
        .limit(1)
    ))
    return bool(response.data)


def _normalize_cloud_shortlist_order(buyer_uuid: str) -> None:
    response = _execute(lambda: (
        _table("buyer_shortlists")
        .select("*")
        .eq("user_id", _uid())
        .eq("buyer_id", buyer_uuid)
        .eq("status", "Shortlisted")
        .order("shortlist_order")
    ))
    for order, row in enumerate(response.data or [], 1):
        if int(row.get("shortlist_order") or 0) != order:
            _execute(lambda row_id=row["id"], order=order: (
                _table("buyer_shortlists")
                .update({"shortlist_order": order})
                .eq("user_id", _uid())
                .eq("id", row_id)
            ))


def cloud_add_to_shortlist(legacy_buyer_id: int, legacy_pdp_id: int) -> None:
    buyer = _cloud_buyer_by_legacy(legacy_buyer_id)
    pdp = _cloud_pdp_by_legacy(legacy_pdp_id)
    if not buyer or not pdp:
        raise ValueError("Buyer or PDP not found.")
    if str(pdp.get("buyer_id") or "") != str(buyer["id"]):
        raise ValueError("This PDP belongs to a different buyer.")
    current = list_cloud_shortlist(legacy_buyer_id)
    next_order = len(current) + 1
    existing = _execute(lambda: (
        _table("buyer_shortlists")
        .select("*")
        .eq("user_id", _uid())
        .eq("buyer_id", buyer["id"])
        .eq("pdp_id", pdp["id"])
        .limit(1)
    ))
    rows = list(existing.data or [])
    if rows:
        _execute(lambda row_id=rows[0]["id"]: (
            _table("buyer_shortlists")
            .update({"status": "Shortlisted", "shortlist_order": next_order})
            .eq("user_id", _uid())
            .eq("id", row_id)
        ))
    else:
        legacy_shortlist_id = _next_legacy_id("buyer_shortlists", "legacy_shortlist_id")
        _execute(lambda: _table("buyer_shortlists").insert({
            "user_id": _uid(),
            "buyer_id": buyer["id"],
            "pdp_id": pdp["id"],
            "legacy_shortlist_id": legacy_shortlist_id,
            "shortlist_order": next_order,
            "status": "Shortlisted",
            "notes": "",
        }))
    _normalize_cloud_shortlist_order(str(buyer["id"]))


def cloud_remove_from_shortlist(legacy_buyer_id: int, legacy_pdp_id: int) -> None:
    buyer = _cloud_buyer_by_legacy(legacy_buyer_id)
    pdp = _cloud_pdp_by_legacy(legacy_pdp_id)
    if not buyer or not pdp:
        return
    _execute(lambda: (
        _table("buyer_shortlists")
        .update({"status": "Removed"})
        .eq("user_id", _uid())
        .eq("buyer_id", buyer["id"])
        .eq("pdp_id", pdp["id"])
    ))
    _normalize_cloud_shortlist_order(str(buyer["id"]))


def cloud_move_shortlist_item(legacy_buyer_id: int, legacy_pdp_id: int, direction: str) -> None:
    buyer = _cloud_buyer_by_legacy(legacy_buyer_id)
    if not buyer:
        return
    items = list_cloud_shortlist(legacy_buyer_id)
    ids = [int(item["id"]) for item in items]
    target = int(legacy_pdp_id)
    if target not in ids:
        return
    idx = ids.index(target)
    new_idx = idx - 1 if direction == "up" else idx + 1
    if new_idx < 0 or new_idx >= len(ids):
        return
    ids[idx], ids[new_idx] = ids[new_idx], ids[idx]
    for order, pdp_legacy in enumerate(ids, 1):
        pdp = _cloud_pdp_by_legacy(pdp_legacy)
        if pdp:
            _execute(lambda pdp_uuid=pdp["id"], order=order: (
                _table("buyer_shortlists")
                .update({"shortlist_order": order})
                .eq("user_id", _uid())
                .eq("buyer_id", buyer["id"])
                .eq("pdp_id", pdp_uuid)
                .eq("status", "Shortlisted")
            ))


def cloud_update_buyer_contact(legacy_buyer_id: int, email: str = "", phone: str = "") -> None:
    buyer = _cloud_buyer_by_legacy(legacy_buyer_id)
    if not buyer:
        return
    _execute(lambda: (
        _table("buyers")
        .update({"email": _clean(email), "phone": _clean(phone)})
        .eq("user_id", _uid())
        .eq("id", buyer["id"])
    ))


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
    legacy_pdp_id = _next_legacy_id("property_decision_profiles", "legacy_pdp_id")
    cloud_profile = dict(profile)
    cloud_profile["decision_id"] = decision_id
    response = _execute(lambda: _table("property_decision_profiles").insert({
        "user_id": _uid(),
        "analysis_id": analysis_uuid,
        "profile_data": cloud_profile,
        "legacy_pdp_id": legacy_pdp_id,
    }))
    row = dict((response.data or [{}])[0])
    return {
        "id": int(row.get("legacy_pdp_id") or legacy_pdp_id),
        "cloud_id": str(row.get("id") or ""),
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
        "id": int(row.get("legacy_pdp_id") or 0),
        "cloud_id": str(row.get("id") or ""),
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
            "id": int(row.get("legacy_pdp_id") or 0),
            "cloud_id": str(row.get("id") or ""),
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
                "id": int(row.get("legacy_pdp_id") or 0),
                "cloud_id": str(row.get("id") or ""),
                "decision_id": str(decision_id),
                "analysis_id": int(((profile.get("audit") or {}).get("source_analysis_id")) or 0),
                "profile": profile,
                "created_at": row.get("created_at"),
            }
    return None
