from __future__ import annotations

from typing import Any


VASTU_WEIGHT = 0.50
NUMEROLOGY_WEIGHT = 0.50


def score_band_10(score: float) -> tuple[str, str]:
    value = float(score)
    if value >= 8.5:
        return "Excellent", "excellent"
    if value >= 7.0:
        return "Good", "good"
    if value >= 5.5:
        return "Moderate", "moderate"
    return "Needs careful review", "critical"


def numerology_band_100(score: float) -> str:
    value = float(score)
    if value >= 90:
        return "Excellent"
    if value >= 80:
        return "Very Good"
    if value >= 70:
        return "Good"
    if value >= 60:
        return "Balanced"
    return "Needs review"


def overall_professional_score(
    vastu_score_10: float | None,
    numerology_score_100: float | None,
) -> dict[str, Any]:
    """Create the transparent platform composite.

    When both disciplines are available, Vastu and Numerology receive equal
    importance. The two underlying assessments remain independent.
    """
    if vastu_score_10 is not None and numerology_score_100 is not None:
        vastu_100 = float(vastu_score_10) * 10
        overall_100 = round(
            vastu_100 * VASTU_WEIGHT
            + float(numerology_score_100) * NUMEROLOGY_WEIGHT,
            1,
        )
        overall_10 = round(overall_100 / 10, 1)
        basis = "Equal-weight Vastu and Numerology"
        weights = {"vastu": VASTU_WEIGHT, "numerology": NUMEROLOGY_WEIGHT}
    elif vastu_score_10 is not None:
        overall_10 = round(float(vastu_score_10), 1)
        overall_100 = round(overall_10 * 10, 1)
        basis = "Vastu only"
        weights = {"vastu": 1.0, "numerology": 0.0}
    elif numerology_score_100 is not None:
        overall_100 = round(float(numerology_score_100), 1)
        overall_10 = round(overall_100 / 10, 1)
        basis = "Numerology only"
        weights = {"vastu": 0.0, "numerology": 1.0}
    else:
        overall_10 = 0.0
        overall_100 = 0.0
        basis = "Insufficient information"
        weights = {"vastu": 0.0, "numerology": 0.0}

    rating, colour_band = score_band_10(overall_10)
    return {
        "score": overall_10,
        "score_100": overall_100,
        "rating": rating,
        "colour_band": colour_band,
        "basis": basis,
        "weights": weights,
        "footnote": (
            "Overall Professional Score is a mathematical platform composite. "
            "When both assessments are available, Vastu and Numerology receive "
            "equal weight (50% each). The underlying assessments remain "
            "independent and should also be reviewed separately."
        ),
    }


def deterministic_summary(
    *,
    payload: dict[str, Any],
    vastu: dict[str, Any],
    numerology: dict[str, Any],
    final: dict[str, Any],
    recommendation: dict[str, Any],
) -> str:
    owner = str(payload.get("owner_name") or "the intended buyer")
    property_id = str(
        payload.get("flat_number")
        or payload.get("property_name")
        or "the property"
    )
    vastu_score = vastu.get("score")
    numerology_100 = numerology.get("score_100")
    if numerology_100 is None and numerology.get("score") is not None:
        numerology_100 = round(float(numerology["score"]) * 10, 1)

    lines = [
        (
            f"For {owner} and {property_id}, the Overall Professional Score is "
            f'{float(final.get("score", 0) or 0):.1f}/10 '
            f'({final.get("rating", "Not rated")}).'
        )
    ]

    if vastu_score is not None:
        lines.append(
            f'Professional Vastu is {float(vastu_score):.1f}/10 '
            f'({vastu.get("grade", "Not graded")}), based on '
            f'{vastu.get("evaluated_count", 0)} evaluated factors and '
            f'{vastu.get("coverage", 0)}% coverage.'
        )

    if numerology_100 is not None:
        lines.append(
            f'Professional Numerology is {float(numerology_100):.1f}/100 '
            f'({numerology.get("grade") or numerology_band_100(numerology_100)}).'
        )

    strengths = list(vastu.get("strengths", []))[:3]
    cautions = list(vastu.get("cautions", []))[:3]
    if strengths:
        lines.append("Key Vastu strengths: " + " ".join(strengths))
    if cautions:
        lines.append("Priority Vastu review items: " + " ".join(cautions))

    actions = recommendation.get("actions", [])
    if actions:
        lines.append(
            "First practical priority: "
            + str(actions[0].get("practical_action") or "Review the highest-priority finding.")
        )

    lines.append(str(final.get("footnote") or ""))
    lines.append(
        "This is belief-based guidance and is not structural, legal, "
        "financial, scientific, safety, valuation or investment advice."
    )
    return "\n\n".join(line for line in lines if line)
