from __future__ import annotations

from copy import deepcopy
from typing import Any

from assessment_core.composite_score import (
    numerology_band_100,
    overall_professional_score,
)


def normalize_numerology_result(value: Any) -> dict[str, Any]:
    """Normalize historical and current Numerology result shapes."""
    result = deepcopy(value) if isinstance(value, dict) else {}

    score_100 = result.get("score_100")
    score_10 = result.get("score")

    if score_100 is None and score_10 is not None:
        try:
            numeric = float(score_10)
            score_100 = numeric * 10 if numeric <= 10 else numeric
        except (TypeError, ValueError):
            score_100 = None

    if score_10 is None and score_100 is not None:
        try:
            score_10 = float(score_100) / 10
        except (TypeError, ValueError):
            score_10 = None

    if score_100 is not None:
        result["score_100"] = round(float(score_100), 1)
    if score_10 is not None:
        result["score"] = round(float(score_10), 1)

    if score_100 is not None and not result.get("grade"):
        result["grade"] = numerology_band_100(float(score_100))

    return result


def normalize_professional_result(value: Any) -> dict[str, Any]:
    """Normalize a stored Professional result without mutating its source."""
    result = deepcopy(value) if isinstance(value, dict) else {}

    numerology = normalize_numerology_result(
        result.get("numerology_result", {})
    )
    result["numerology_result"] = numerology

    vastu = (
        deepcopy(result.get("vastu_result"))
        if isinstance(result.get("vastu_result"), dict)
        else {}
    )
    result["vastu_result"] = vastu

    final = (
        deepcopy(result.get("final_result"))
        if isinstance(result.get("final_result"), dict)
        else {}
    )

    vastu_score = vastu.get("score")
    numerology_score_100 = numerology.get("score_100")

    if (
        not final
        or "weights" not in final
        or (
            vastu_score is not None
            and numerology_score_100 is not None
            and final.get("basis") != "Equal-weight Vastu and Numerology"
        )
    ):
        final = overall_professional_score(
            float(vastu_score) if vastu_score is not None else None,
            (
                float(numerology_score_100)
                if numerology_score_100 is not None
                else None
            ),
        )

    result["final_result"] = final
    return result
