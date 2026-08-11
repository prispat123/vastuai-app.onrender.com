from __future__ import annotations

from assessment_core.composite_score import overall_professional_score
from professional_app.state import PropertyState


def scoring_agent(state: PropertyState) -> dict:
    errors = state.get("validation_errors", [])
    if errors:
        return {
            "final_result": {
                "score": 0.0,
                "score_100": 0.0,
                "rating": "Input error",
                "errors": errors,
            }
        }

    vastu = state.get("vastu_result", {})
    numerology = state.get("numerology_result", {})
    vastu_score = vastu.get("score")
    numerology_score_100 = numerology.get("score_100")
    if numerology_score_100 is None and numerology.get("score") is not None:
        numerology_score_100 = float(numerology["score"]) * 10

    return {
        "final_result": overall_professional_score(
            float(vastu_score) if vastu_score is not None else None,
            (
                float(numerology_score_100)
                if numerology_score_100 is not None
                else None
            ),
        )
    }
