from __future__ import annotations

from datetime import date
from typing import Any

from knowledge_engine import KnowledgeEngine, KnowledgeRepository
from numerology_engine import NumerologyEngine


UNKNOWN = {"", "Unknown", "None", "N/A", None}


def _vastu_observations(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key.endswith("_direction") and value not in UNKNOWN
    }


def _knowledge_ids(assessment: dict) -> list[str]:
    return [
        str(item.get("rule_id"))
        for item in assessment.get("findings", [])
        if item.get("rule_id")
    ]


def _numerology_ids(result: dict) -> list[str]:
    rows = result.get("number_objects", []) + result.get(
        "alignment_objects", []
    )
    return [
        str(item.get("object_id"))
        for item in rows
        if item.get("object_id")
    ]


def build_snapshot(
    *,
    payload: dict[str, Any],
    professional_result: dict[str, Any],
    vastu_profile: str = "practical",
) -> dict[str, Any]:
    """Build one individual-property snapshot from saved Property Details.

    Vastu and Numerology remain independent. This function creates no tower,
    building or project-level Numerology assessment and never averages the two
    scores.
    """
    observations = _vastu_observations(payload)
    vastu_knowledge = KnowledgeEngine(KnowledgeRepository()).evaluate(
        observations,
        profile=vastu_profile,
        detection_confidences={key: 1.0 for key in observations},
    ) if observations else {}

    numerology_knowledge = {}
    dob_text = str(payload.get("dob") or "").strip()
    property_identifier = str(payload.get("flat_number") or "").strip()
    if dob_text and property_identifier:
        numerology_knowledge = NumerologyEngine().evaluate(
            intended_user_name=str(payload.get("owner_name") or ""),
            date_of_birth=date.fromisoformat(dob_text),
            property_identifier=property_identifier,
            property_name=str(payload.get("property_name") or ""),
            method_profile="foundational",
        )

    vastu_result = professional_result.get("vastu_result", {}) or {}
    legacy_numerology = professional_result.get("numerology_result", {}) or {}

    return {
        "property": {
            "property_name": payload.get("property_name", ""),
            "owner_name": payload.get("owner_name", ""),
            "date_of_birth": dob_text,
            "property_identifier": property_identifier,
            "assessment_year": payload.get("assessment_year"),
        },
        "vastu": {
            "result": vastu_result,
            "knowledge": vastu_knowledge,
            "knowledge_ids": _knowledge_ids(vastu_knowledge),
        },
        "numerology": {
            "legacy_result": legacy_numerology,
            "knowledge_result": numerology_knowledge,
            "knowledge_ids": _numerology_ids(numerology_knowledge),
            "available": bool(numerology_knowledge),
        },
        "separation_policy": {
            "independent_scores": True,
            "direct_comparison_allowed": False,
            "averaging_allowed": False,
            "scope": "individual_property_and_intended_user",
        },
    }
