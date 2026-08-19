from __future__ import annotations

from typing import Any

from platform_core import auth


def _table(name: str):
    if auth.current_user() is None:
        raise RuntimeError("Authentication required.")
    return auth.client().table(name)


def list_professional_properties(limit: int = 200) -> list[dict[str, Any]]:
    """Read only the signed-in user's Professional cloud records.

    RLS is the primary enforcement layer; the explicit user_id filter is
    retained as defense-in-depth and for clearer query intent.
    """
    uid = auth.user_id()
    response = (
        _table("professional_analyses")
        .select("*")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(response.data or [])


def save_professional_property(
    *,
    property_name: str,
    property_data: dict[str, Any],
    assessment_data: dict[str, Any],
    overall_score: float | None,
    vastu_score: float | None,
    numerology_score: float | None,
    project_id: str | None = None,
) -> dict[str, Any]:
    uid = auth.user_id()
    if not uid:
        raise RuntimeError("Authentication required.")
    payload = {
        "user_id": uid,
        "project_id": project_id,
        "property_name": property_name,
        "property_data": property_data,
        "assessment_data": assessment_data,
        "overall_score": overall_score,
        "vastu_score": vastu_score,
        "numerology_score": numerology_score,
    }
    response = _table("professional_analyses").insert(payload).execute()
    if not response.data:
        raise RuntimeError("Supabase did not return the saved property.")
    return dict(response.data[0])


def create_cloud_project(name: str, workspace_type: str = "Professional", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    uid = auth.user_id()
    if not uid:
        raise RuntimeError("Authentication required.")
    response = _table("projects").insert({
        "user_id": uid,
        "name": name,
        "workspace_type": workspace_type,
        "metadata": metadata or {},
    }).execute()
    if not response.data:
        raise RuntimeError("Supabase did not return the saved project.")
    return dict(response.data[0])
