from __future__ import annotations

from typing import Any

from professional_app.state import PropertyState


def _priority_rank(severity: str) -> int:
    return {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}.get(str(severity), 4)


def _decision(score: float, critical_count: int, confidence: str) -> tuple[str, str]:
    if critical_count >= 2 or score < 4.5:
        return "Proceed only after major review", "High caution"
    if critical_count == 1 or score < 6.0:
        return "Proceed with caution", "Caution"
    if score < 7.5 or confidence in {"Limited", "Insufficient information"}:
        return "Potentially suitable with improvements", "Moderate"
    if score < 8.7:
        return "Generally suitable", "Positive"
    return "Strong traditional compatibility", "Very positive"


def recommendation_agent(state: PropertyState) -> dict[str, Any]:
    if state.get("validation_errors"):
        return {"recommendation_result": {"decision": "Input correction required", "actions": []}}

    final = state.get("final_result", {})
    vastu = state.get("vastu_result", {})
    numerology = state.get("numerology_result", {})
    score = float(final.get("score", 0) or 0)

    details = list(vastu.get("details", []))
    issues = [item for item in details if float(item.get("score", 0) or 0) < 7]
    issues.sort(key=lambda x: (_priority_rank(x.get("severity", "")), float(x.get("score", 0) or 0)))
    critical_count = sum(1 for item in issues if item.get("severity") in {"Critical", "High"})

    confidences = [x for x in (vastu.get("confidence"), numerology.get("confidence")) if x]
    confidence = "High" if confidences and all(x == "High" for x in confidences) else (
        "Moderate" if any(x in {"High", "Moderate"} for x in confidences) else "Limited"
    )
    decision, sentiment = _decision(score, critical_count, confidence)

    actions: list[dict[str, Any]] = []
    for item in issues[:5]:
        actions.append({
            "priority": item.get("severity", "Medium"),
            "area": item.get("area", "Property feature"),
            "finding": f"{item.get('area', 'Feature')} is in {item.get('direction', 'Unknown')}.",
            "why_it_matters": item.get("rationale", ""),
            "practical_action": item.get("non_structural_remedy", "Seek a qualified review."),
            "structural_option": item.get("structural_remedy", "Professional review required."),
        })

    strengths = list(vastu.get("strengths", []))[:3] + list(numerology.get("strengths", []))[:2]
    cautions = list(vastu.get("cautions", []))[:3] + list(numerology.get("cautions", []))[:2]

    synergy: list[str] = []
    if vastu.get("score") is not None and numerology.get("score") is not None:
        gap = abs(float(vastu.get("score", 0)) - float(numerology.get("score", 0)))
        if gap <= 1.5:
            synergy.append("Vastu and numerology results are broadly aligned.")
        else:
            synergy.append("Vastu and numerology differ materially; prioritise physical layout findings for property decisions.")
    elif vastu.get("score") is not None:
        synergy.append("The recommendation is based on Vastu because sufficient numerology data was not supplied.")
    elif numerology.get("score") is not None:
        synergy.append("The recommendation is based on numerology because sufficient Vastu data was not supplied.")

    return {
        "recommendation_result": {
            "decision": decision,
            "sentiment": sentiment,
            "confidence": confidence,
            "critical_issue_count": critical_count,
            "strengths": strengths,
            "cautions": cautions,
            "synergy_notes": synergy,
            "actions": actions,
            "next_steps": [
                "Verify room directions and the North reference before relying on the assessment.",
                "Discuss structural changes with a qualified architect or engineer.",
                "Complete legal, financial and physical due diligence independently.",
            ],
            "disclaimer": "This recommendation is belief-based and is not structural, legal, financial, scientific or investment advice.",
        }
    }
