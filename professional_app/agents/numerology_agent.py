from __future__ import annotations

from datetime import date

from numerology_engine import NumerologyEngine
from professional_app.state import PropertyState
from professional_app.utils.numerology import calculate_numerology


def numerology_agent(state: PropertyState) -> dict:
    if state.get("validation_errors"):
        return {"numerology_result": {}}
    readiness = state.get("analysis_readiness", {})
    if not readiness.get("numerology_ready"):
        return {"numerology_result": {}}

    dob = date.fromisoformat(state["dob"])
    legacy = calculate_numerology(
        owner_name=state.get("owner_name", ""),
        dob=dob,
        flat_number=state["flat_number"],
        assessment_year=state.get("assessment_year"),
    )
    knowledge = NumerologyEngine().evaluate(
        intended_user_name=state.get("owner_name", ""),
        date_of_birth=dob,
        property_identifier=state["flat_number"],
        property_name=state.get("property_name", ""),
        method_profile="foundational",
    )

    legacy["legacy_score"] = legacy.get("score")
    legacy["score_100"] = float(knowledge["numerology_score"])
    legacy["score"] = round(float(knowledge["numerology_score"]) / 10, 1)
    legacy["grade"] = knowledge["grade"]
    legacy["knowledge_version"] = knowledge["knowledge_version"]
    legacy["knowledge_assessment"] = knowledge
    legacy["knowledge_ids"] = [
        item["object_id"]
        for item in (
            knowledge.get("number_objects", [])
            + knowledge.get("alignment_objects", [])
        )
        if item.get("object_id")
    ]
    return {"numerology_result": legacy}
