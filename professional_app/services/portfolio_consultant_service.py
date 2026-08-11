from __future__ import annotations

from typing import Any

from professional_app.services import buyer_workspace_service


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _property_label(row: dict[str, Any]) -> str:
    name = str(row.get("property_name") or "Property").strip()
    number = str(row.get("property_number") or "").strip()
    return f"{name} {number}".strip()


def _ranking_key(row: dict[str, Any]) -> tuple[float, float, float, float, int]:
    """Rank without recalculating any assessment.

    The immutable PDP Overall Professional Score remains the primary basis.
    Critical/high findings, Vastu and Numerology are deterministic tie-breakers.
    The original shortlist order is retained as the final stable tie-breaker.
    """
    return (
        _number(row.get("overall_score")),
        -_number(row.get("critical_high_count")),
        _number(row.get("vastu_score")),
        _number(row.get("numerology_score_100")),
        -int(row.get("shortlist_order") or 0),
    )


def _dedupe_text(values: list[Any], limit: int = 3) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = " ".join(str(value or "").split())
        key = text.lower()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
        if len(result) >= limit:
            break
    return result


def _strengths(row: dict[str, Any]) -> list[str]:
    profile = row.get("profile", {}) or {}
    vastu = profile.get("vastu", {}) or {}
    strengths = _dedupe_text(list(vastu.get("strengths", []) or []), 3)
    if strengths:
        return strengths

    generated: list[str] = []
    if _number(row.get("vastu_score")) >= 8.0:
        generated.append(f'High Vastu score: {_number(row.get("vastu_score")):.1f}/10.')
    if _number(row.get("numerology_score_100")) >= 80.0:
        generated.append(
            f'Strong Numerology score: {_number(row.get("numerology_score_100")):.1f}/100.'
        )
    if _number(row.get("critical_high_count")) == 0:
        generated.append("No critical/high Vastu findings recorded in the PDP.")
    return generated[:3] or ["Review the saved PDP for its detailed strengths."]


def _concerns(row: dict[str, Any]) -> list[str]:
    profile = row.get("profile", {}) or {}
    vastu = profile.get("vastu", {}) or {}
    cautions = _dedupe_text(list(vastu.get("cautions", []) or []), 3)
    if cautions:
        return cautions

    generated: list[str] = []
    critical = int(_number(row.get("critical_high_count")))
    if critical:
        generated.append(f"{critical} critical/high Vastu finding(s) require review.")
    if _number(row.get("vastu_score")) < 7.0:
        generated.append(f'Vastu score is {_number(row.get("vastu_score")):.1f}/10.')
    if _number(row.get("numerology_score_100")) < 70.0:
        generated.append(
            f'Numerology score is {_number(row.get("numerology_score_100")):.1f}/100.'
        )
    return generated[:3] or ["No additional portfolio-level concern identified from saved PDP fields."]


def _tradeoff(row: dict[str, Any], best_vastu: dict[str, Any], best_num: dict[str, Any]) -> str:
    parts: list[str] = []
    if int(row["id"]) != int(best_vastu["id"]):
        gap = _number(best_vastu.get("vastu_score")) - _number(row.get("vastu_score"))
        if gap > 0.05:
            parts.append(f"Vastu trails the shortlist leader by {gap:.1f} point(s).")
    else:
        parts.append("This is the shortlist's strongest Vastu fit.")

    if int(row["id"]) != int(best_num["id"]):
        gap = _number(best_num.get("numerology_score_100")) - _number(row.get("numerology_score_100"))
        if gap > 0.5:
            parts.append(f"Numerology trails the shortlist leader by {gap:.1f} point(s).")
    else:
        parts.append("This is the shortlist's strongest Numerology fit.")

    return " ".join(parts) or "Scores are closely balanced against the shortlist leaders."


def analyse_shortlist(buyer_id: int) -> dict[str, Any]:
    """Create a deterministic portfolio view from the buyer's saved shortlist."""
    buyer = buyer_workspace_service.get_buyer(int(buyer_id))
    if not buyer:
        raise ValueError("Buyer not found.")

    shortlist = buyer_workspace_service.list_shortlist(int(buyer_id))
    if not shortlist:
        return {
            "buyer": buyer,
            "shortlist_count": 0,
            "ranked": [],
            "best_overall": None,
            "best_vastu": None,
            "best_numerology": None,
            "recommendation": "Add at least one saved PDP to the buyer shortlist.",
            "ranking_basis": "No ranking available.",
        }

    ranked_raw = sorted(shortlist, key=_ranking_key, reverse=True)
    best_vastu = max(
        shortlist,
        key=lambda row: (
            _number(row.get("vastu_score")),
            -_number(row.get("critical_high_count")),
            _number(row.get("overall_score")),
        ),
    )
    best_num = max(
        shortlist,
        key=lambda row: (
            _number(row.get("numerology_score_100")),
            _number(row.get("overall_score")),
            -_number(row.get("critical_high_count")),
        ),
    )

    ranked: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked_raw, 1):
        item = dict(row)
        item["portfolio_rank"] = rank
        item["property_label"] = _property_label(row)
        item["strengths"] = _strengths(row)
        item["concerns"] = _concerns(row)
        item["tradeoff"] = _tradeoff(row, best_vastu, best_num)
        ranked.append(item)

    best = ranked[0]
    if len(ranked) == 1:
        recommendation = (
            f'{best["decision_id"]} — {best["project_name"]} — '
            f'{best["property_label"]} is currently the only shortlisted property. '
            "Add another PDP for comparative portfolio advice."
        )
    else:
        runner_up = ranked[1]
        gap = _number(best.get("overall_score")) - _number(runner_up.get("overall_score"))
        recommendation = (
            f'Start with {best["decision_id"]} — {best["project_name"]} — '
            f'{best["property_label"]}. It ranks first on the saved Overall Professional Score '
            f'({_number(best.get("overall_score")):.1f}/10)'
            + (f", {gap:.1f} point(s) ahead of rank 2" if gap > 0.05 else ", with a close margin over rank 2")
            + ". Review its recorded concerns before making a buying decision."
        )

    return {
        "buyer": buyer,
        "shortlist_count": len(shortlist),
        "ranked": ranked,
        "best_overall": ranked[0],
        "best_vastu": next(row for row in ranked if int(row["id"]) == int(best_vastu["id"])),
        "best_numerology": next(row for row in ranked if int(row["id"]) == int(best_num["id"])),
        "recommendation": recommendation,
        "ranking_basis": (
            "Ranking preserves each immutable PDP Overall Professional Score as the primary basis. "
            "Fewer critical/high findings, Vastu score and Numerology score are used only as tie-breakers. "
            "No assessment score is recalculated by Portfolio Consultant."
        ),
    }
