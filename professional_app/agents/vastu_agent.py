from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from professional_app.state import PropertyState

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = PROJECT_ROOT / "config" / "vastu_rules.json"


def load_rules() -> dict[str, dict[str, Any]]:
    with RULES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def _severity(score: float) -> str:
    if score <= 3:
        return "Critical"
    if score <= 5:
        return "High"
    if score < 7:
        return "Medium"
    return "Low"


def _status(score: float) -> str:
    if score >= 8.5:
        return "Excellent"
    if score >= 7:
        return "Favourable"
    if score >= 5:
        return "Mixed"
    return "Needs attention"


def _grade(score: float) -> str:
    if score >= 9:
        return "A+"
    if score >= 8:
        return "A"
    if score >= 7:
        return "B+"
    if score >= 6:
        return "B"
    if score >= 5:
        return "C"
    return "D"


def _confidence(coverage: float, evaluated_count: int) -> str:
    if evaluated_count >= 8 and coverage >= 65:
        return "High"
    if evaluated_count >= 5:
        return "Moderate"
    if evaluated_count >= 3:
        return "Limited"
    return "Insufficient"


def vastu_agent(state: PropertyState) -> dict:
    if state.get("validation_errors"):
        return {"vastu_result": {}}

    rules = load_rules()
    details: list[dict[str, Any]] = []
    strengths: list[str] = []
    cautions: list[str] = []
    critical_issues: list[dict[str, Any]] = []
    weighted_total = 0.0
    total_weight = 0.0

    for field, rule in rules.items():
        direction = str(state.get(field, "") or "").strip()
        score_map = rule.get("scores", {})
        if direction not in score_map:
            continue

        score = float(score_map[direction])
        weight = float(rule.get("weight", 1.0))
        severity = _severity(score)
        status = _status(score)
        item = {
            "field": field,
            "area": rule.get("label", field.replace("_direction", "").replace("_", " ").title()),
            "direction": direction,
            "score": score,
            "weight": weight,
            "weighted_score": round(score * weight, 2),
            "status": status,
            "severity": severity,
            "preferred": rule.get("preferred", []),
            "avoid": rule.get("avoid", []),
            "rationale": rule.get("rationale", ""),
            "structural_remedy": rule.get("remedies", {}).get("structural", ""),
            "non_structural_remedy": rule.get("remedies", {}).get("non_structural", ""),
        }
        details.append(item)
        weighted_total += score * weight
        total_weight += weight

        if score >= 8:
            strengths.append(f"{item['area']} in {direction} is {status.lower()} under the configured rules.")
        elif score < 7:
            cautions.append(f"{item['area']} in {direction} is rated {score:g}/10 ({severity.lower()} concern).")
        if score <= 5:
            critical_issues.append(item)

    if not details:
        return {"vastu_result": {}}

    score = round(weighted_total / total_weight, 1)
    total_rules = len(rules)
    coverage = round(len(details) / total_rules * 100, 1)
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    critical_issues.sort(key=lambda item: (severity_order[item["severity"]], item["score"]))

    return {
        "vastu_result": {
            "score": score,
            "percentage": round(score * 10, 1),
            "grade": _grade(score),
            "status": _status(score),
            "details": details,
            "strengths": strengths,
            "cautions": cautions,
            "critical_issues": critical_issues,
            "evaluated_count": len(details),
            "total_supported_factors": total_rules,
            "coverage": coverage,
            "confidence": _confidence(coverage, len(details)),
            "weighted_total": round(weighted_total, 2),
            "total_weight": round(total_weight, 2),
        }
    }
