from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any, Callable

from professional_app.services.chart_service import build_direction_wheel_png, build_room_scores_png, direction_balance, room_scores


def to_json_bytes(payload: dict[str, Any], result: dict[str, Any]) -> bytes:
    enriched = {
        "payload": payload,
        "result": result,
        "report_visuals": {
            "direction_balance": direction_balance(result.get("vastu_result", {}).get("details", [])),
            "room_scores": room_scores(result.get("vastu_result", {}).get("details", [])),
        },
    }
    return json.dumps(enriched, indent=2, ensure_ascii=False, default=str).encode("utf-8")


def to_csv_bytes(payload: dict[str, Any], result: dict[str, Any]) -> bytes:
    final = result.get("final_result", {})
    vastu = result.get("vastu_result", {})
    numerology = result.get("numerology_result", {})
    recommendation = result.get("recommendation_result", {})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        "property", "owner", "apartment_number", "overall_score", "rating",
        "vastu_score", "vastu_grade", "vastu_coverage", "numerology_score",
        "numerology_coverage", "decision", "confidence", "critical_issues"
    ])
    writer.writeheader()
    writer.writerow({
        "property": payload.get("property_name") or payload.get("flat_number") or "Unnamed property",
        "owner": payload.get("owner_name", ""),
        "apartment_number": payload.get("flat_number", ""),
        "overall_score": final.get("score", ""),
        "rating": final.get("rating", ""),
        "vastu_score": vastu.get("score", ""),
        "vastu_grade": vastu.get("grade", ""),
        "vastu_coverage": vastu.get("coverage", ""),
        "numerology_score": numerology.get("score", ""),
        "numerology_coverage": numerology.get("coverage", ""),
        "decision": recommendation.get("decision", ""),
        "confidence": recommendation.get("confidence", ""),
        "critical_issues": recommendation.get("critical_issue_count", 0),
    })
    return output.getvalue().encode("utf-8")


def to_room_scores_csv_bytes(result: dict[str, Any]) -> bytes:
    output = io.StringIO()
    fields = ["area", "direction", "score", "severity", "status"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(room_scores(result.get("vastu_result", {}).get("details", [])))
    return output.getvalue().encode("utf-8")


def to_direction_balance_csv_bytes(result: dict[str, Any]) -> bytes:
    output = io.StringIO()
    fields = ["direction", "average_score", "room_count"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(direction_balance(result.get("vastu_result", {}).get("details", [])))
    return output.getvalue().encode("utf-8")


def build_export_bundle(
    payload: dict[str, Any],
    result: dict[str, Any],
    pdf_builder: Callable[[dict[str, Any], dict[str, Any]], bytes],
    report_text: str = "",
) -> bytes:
    details = result.get("vastu_result", {}).get("details", [])
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("VastuAI_Professional_Report.pdf", pdf_builder(payload, result))
        archive.writestr("assessment_summary.csv", to_csv_bytes(payload, result))
        archive.writestr("room_scores.csv", to_room_scores_csv_bytes(result))
        archive.writestr("direction_balance.csv", to_direction_balance_csv_bytes(result))
        archive.writestr("assessment_data.json", to_json_bytes(payload, result))
        archive.writestr("report.txt", report_text.encode("utf-8"))
        archive.writestr("directional_balance_wheel.png", build_direction_wheel_png(details))
        archive.writestr("room_scores.png", build_room_scores_png(details))
    return output.getvalue()
