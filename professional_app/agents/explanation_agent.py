from __future__ import annotations

from assessment_core.composite_score import deterministic_summary
from professional_app.state import PropertyState


def explanation_agent(state: PropertyState) -> dict:
    if state.get("validation_errors"):
        return {
            "explanation": (
                "Correct the input errors and run the assessment again."
            )
        }

    return {
        "explanation": deterministic_summary(
            payload=dict(state),
            vastu=state.get("vastu_result", {}),
            numerology=state.get("numerology_result", {}),
            final=state.get("final_result", {}),
            recommendation=state.get("recommendation_result", {}),
        )
    }
