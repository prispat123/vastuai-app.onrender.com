from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from platform_core.database import connect, transaction
from platform_core.projects import get_project
from platform_core.storage import STORAGE
from professional_app.agents.validation_agent import validation_agent
from professional_app.agents.vastu_agent import vastu_agent
from professional_app.agents.scoring_agent import scoring_agent
from professional_app.agents.recommendation_agent import recommendation_agent
from project_intelligence import service

ANALYSIS_VERSION = "PROFESSIONAL-1.0"
# Legacy dashboard test/reference: VSS-1.0 has been superseded by the shared Professional engine.

def _latest_extraction(layout_id: int):
    with connect() as connection:
        return connection.execute(
            """
            SELECT le.*
            FROM layout_extractions le
            WHERE le.layout_id=?
            ORDER BY le.id DESC LIMIT 1
            """,
            (int(layout_id),),
        ).fetchone()

def _layout_payload(layout, extraction) -> dict[str, Any]:
    rooms = json.loads(extraction["rooms_json"] or "{}") if extraction else {}
    payload: dict[str, Any] = {
        "property_name": layout["flat_number"] or layout["layout_type"] or f'Layout {layout["id"]}',
        "flat_number": layout["flat_number"] or "",
        "entrance_direction": (
            extraction["entrance_direction"] if extraction else "Unknown"
        ),
    }
    for field in [
        "kitchen_direction",
        "master_bedroom_direction",
        "toilet_direction",
        "pooja_direction",
        "living_room_direction",
        "balcony_direction",
        "staircase_direction",
        "children_bedroom_direction",
        "guest_bedroom_direction",
        "dining_direction",
        "brahmasthan_direction",
        "underground_tank_direction",
        "overhead_tank_direction",
        "parking_direction",
    ]:
        item = rooms.get(field, {})
        payload[field] = (
            item.get("value", "Unknown")
            if isinstance(item, dict)
            else str(item or "Unknown")
        )
    return payload

def _confidence_value(extraction, vastu_result: dict) -> float:
    vision = float(extraction["vision_confidence"] or 0) if extraction else 0.0
    coverage = float(vastu_result.get("coverage", 0) or 0) / 100
    return round(max(0.0, min(1.0, vision * 0.65 + coverage * 0.35)), 3)

def analyse_layout(layout_id: int) -> dict:
    with connect() as connection:
        layout = connection.execute(
            "SELECT * FROM project_layouts WHERE id=?",
            (int(layout_id),),
        ).fetchone()
    if not layout:
        raise ValueError("Layout not found.")

    extraction = _latest_extraction(layout_id)
    if not extraction:
        service.update_layout(
            int(layout_id),
            tower=layout["tower"] or "",
            flat_number=layout["flat_number"] or "",
            layout_type=layout["layout_type"] or "",
            floor=layout["floor"] or "",
            analysis_status="Needs Review",
            notes=(layout["notes"] or "") + "\nNo approved extraction found.",
        )
        return {
            "layout_id": int(layout_id),
            "success": False,
            "reason": "No approved extraction found.",
        }

    state = _layout_payload(layout, extraction)
    validation = validation_agent(state)
    state.update(validation)
    state.update(vastu_agent(state))
    state.update(scoring_agent(state))
    state.update(recommendation_agent(state))

    errors = state.get("validation_errors", [])
    vastu = state.get("vastu_result", {})
    final = state.get("final_result", {})
    recommendation = state.get("recommendation_result", {})
    confidence = _confidence_value(extraction, vastu)

    if errors or not vastu:
        status = "Needs Review"
        score = 0.0
    else:
        status = "Completed"
        score = float(final.get("score", vastu.get("score", 0)) or 0)

    result = {
        "analysis_version": ANALYSIS_VERSION,
        "layout": dict(layout),
        "source_extraction_id": int(extraction["id"]),
        "payload": state,
        "vastu_result": vastu,
        "final_result": final,
        "recommendation_result": recommendation,
        "confidence_value": confidence,
        "errors": errors,
    }

    project = get_project(int(layout["project_id"]))
    output_dir = Path(project["project_folder"]) / "analysis" / "layouts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'layout_{layout_id}_{ANALYSIS_VERSION.replace(".", "_")}.json'
    STORAGE.write_json(output_path, result, overwrite=True)

    with transaction() as connection:
        connection.execute(
            """
            INSERT INTO project_layout_analyses(
                project_id,layout_id,analysis_version,source_extraction_id,
                vastu_score,overall_score,confidence_label,confidence_value,
                grade,status,strengths_json,cautions_json,findings_json,
                recommendations_json,result_json_path
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(layout_id,analysis_version) DO UPDATE SET
                source_extraction_id=excluded.source_extraction_id,
                vastu_score=excluded.vastu_score,
                overall_score=excluded.overall_score,
                confidence_label=excluded.confidence_label,
                confidence_value=excluded.confidence_value,
                grade=excluded.grade,
                status=excluded.status,
                strengths_json=excluded.strengths_json,
                cautions_json=excluded.cautions_json,
                findings_json=excluded.findings_json,
                recommendations_json=excluded.recommendations_json,
                result_json_path=excluded.result_json_path,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                int(layout["project_id"]),
                int(layout_id),
                ANALYSIS_VERSION,
                int(extraction["id"]),
                float(vastu.get("score", 0) or 0),
                score,
                vastu.get("confidence", "Insufficient"),
                confidence,
                vastu.get("grade", ""),
                status,
                json.dumps(vastu.get("strengths", [])),
                json.dumps(vastu.get("cautions", [])),
                json.dumps(vastu.get("details", [])),
                json.dumps(recommendation.get("actions", [])),
                str(output_path),
            ),
        )
        connection.execute(
            """
            UPDATE project_layouts SET
                analysis_status=?,
                overall_score=?,
                confidence=?,
                last_analysis_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (status, score if status == "Completed" else None, confidence, int(layout_id)),
        )

    return {
        "layout_id": int(layout_id),
        "success": status == "Completed",
        "status": status,
        "score": score,
        "confidence": confidence,
        "errors": errors,
    }

def analyse_project(project_id: int, *, include_completed: bool = True) -> dict:
    rows = service.list_layouts(project_id)
    selected = [
        row for row in rows
        if include_completed or row["analysis_status"] != "Completed"
    ]
    completed = needs_review = failed = 0
    results = []

    for layout in selected:
        try:
            result = analyse_layout(int(layout["id"]))
            results.append(result)
            if result.get("success"):
                completed += 1
            else:
                needs_review += 1
        except Exception as exc:
            failed += 1
            needs_review += 1
            results.append({
                "layout_id": int(layout["id"]),
                "success": False,
                "reason": str(exc),
            })

    snapshot = project_summary(project_id)
    with transaction() as connection:
        connection.execute(
            """
            INSERT INTO project_analysis_snapshots(
                project_id,analysis_version,project_score,layout_count,
                analysed_count,needs_review_count,confidence_value,summary_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                int(project_id),
                ANALYSIS_VERSION,
                snapshot.get("project_score"),
                snapshot["layout_count"],
                snapshot["analysed_count"],
                snapshot["needs_review_count"],
                snapshot["average_confidence"],
                json.dumps(snapshot, default=str),
            ),
        )

    service.add_timeline_event(
        project_id,
        "PROJECT_ANALYSIS_COMPLETED",
        "Project-wide Vastu analysis completed",
        (
            f"{completed} completed; {needs_review} need review; "
            f"{failed} processing error(s)"
        ),
    )
    return {
        "processed": len(selected),
        "completed": completed,
        "needs_review": needs_review,
        "failed": failed,
        "results": results,
        "summary": snapshot,
    }

def list_analysis_rows(project_id: int):
    with connect() as connection:
        return connection.execute(
            """
            SELECT pl.*, pa.vastu_score,pa.overall_score analysis_score,
                   pa.confidence_label,pa.confidence_value analysis_confidence,
                   pa.grade,pa.status analysis_result_status,
                   pa.findings_json,pa.recommendations_json,pa.result_json_path
            FROM project_layouts pl
            LEFT JOIN project_layout_analyses pa
              ON pa.layout_id=pl.id AND pa.analysis_version=?
            WHERE pl.project_id=?
            ORDER BY pa.overall_score DESC,pl.tower,pl.flat_number
            """,
            (ANALYSIS_VERSION, int(project_id)),
        ).fetchall()

def project_summary(project_id: int) -> dict:
    rows = list_analysis_rows(project_id)
    analysed = [r for r in rows if r["analysis_result_status"] == "Completed"]
    review = [r for r in rows if r["analysis_status"] == "Needs Review"]

    scores = [float(r["analysis_score"]) for r in analysed if r["analysis_score"] is not None]
    confidences = [
        float(r["analysis_confidence"])
        for r in analysed
        if r["analysis_confidence"] is not None
    ]

    tower_scores: dict[str, list[float]] = defaultdict(list)
    type_scores: dict[str, list[float]] = defaultdict(list)
    issue_counter: Counter[str] = Counter()
    direction_counter: Counter[str] = Counter()
    recommendation_counter: Counter[str] = Counter()

    for row in analysed:
        score = float(row["analysis_score"] or 0)
        tower_scores[row["tower"] or "Unspecified"].append(score)
        type_scores[row["layout_type"] or "Unspecified"].append(score)

        for finding in json.loads(row["findings_json"] or "[]"):
            direction = str(finding.get("direction", "Unknown"))
            area = str(finding.get("area", finding.get("field", "Finding")))
            finding_score = float(finding.get("score", 0) or 0)
            direction_counter[direction] += 1
            if finding_score < 7:
                issue_counter[f"{area} · {direction}"] += 1

        for recommendation in json.loads(row["recommendations_json"] or "[]"):
            area = str(recommendation.get("area", "General review"))
            recommendation_counter[area] += 1

    def averages(mapping):
        return [
            {
                "name": name,
                "score": round(sum(values) / len(values), 2),
                "count": len(values),
            }
            for name, values in mapping.items()
        ]

    ranked_layouts = [
        {
            "id": int(row["id"]),
            "tower": row["tower"] or "—",
            "flat_number": row["flat_number"] or f'Layout {row["id"]}',
            "layout_type": row["layout_type"] or "—",
            "score": float(row["analysis_score"] or 0),
            "confidence": float(row["analysis_confidence"] or 0),
            "grade": row["grade"] or "",
        }
        for row in analysed
    ]

    project_score = round(sum(scores) / len(scores), 2) if scores else None
    average_confidence = (
        round(sum(confidences) / len(confidences), 3)
        if confidences else 0.0
    )

    return {
        "analysis_version": ANALYSIS_VERSION,
        "layout_count": len(rows),
        "analysed_count": len(analysed),
        "pending_count": len(rows) - len(analysed),
        "needs_review_count": len(review),
        "project_score": project_score,
        "average_confidence": average_confidence,
        "tower_ranking": sorted(averages(tower_scores), key=lambda x: x["score"], reverse=True),
        "layout_type_ranking": sorted(averages(type_scores), key=lambda x: x["score"], reverse=True),
        "layout_ranking": sorted(ranked_layouts, key=lambda x: x["score"], reverse=True),
        "common_issues": [
            {"issue": issue, "count": count}
            for issue, count in issue_counter.most_common(12)
        ],
        "direction_distribution": [
            {"direction": direction, "count": count}
            for direction, count in direction_counter.most_common()
        ],
        "recommendation_priorities": [
            {"area": area, "count": count}
            for area, count in recommendation_counter.most_common(10)
        ],
    }

def executive_recommendations(summary: dict) -> list[str]:
    recommendations = []
    if summary["project_score"] is None:
        return ["Complete layout extraction and analysis before generating project recommendations."]

    if summary["needs_review_count"]:
        recommendations.append(
            f'Review {summary["needs_review_count"]} layout(s) with missing or low-confidence information.'
        )
    if summary["common_issues"]:
        top = summary["common_issues"][0]
        recommendations.append(
            f'Prioritise the recurring issue “{top["issue"]}”, found {top["count"]} time(s).'
        )
    if summary["tower_ranking"]:
        best = summary["tower_ranking"][0]
        worst = summary["tower_ranking"][-1]
        if len(summary["tower_ranking"]) > 1:
            recommendations.append(
                f'Use {best["name"]} as the internal benchmark and review why '
                f'{worst["name"]} scores {best["score"] - worst["score"]:.1f} points lower.'
            )
    low_layouts = [x for x in summary["layout_ranking"] if x["score"] < 6]
    if low_layouts:
        recommendations.append(
            f'Review or redesign {len(low_layouts)} layout(s) scoring below 6/10.'
        )
    if summary["average_confidence"] < 0.75:
        recommendations.append(
            "Improve North and room verification before relying on project-level comparisons."
        )
    if not recommendations:
        recommendations.append(
            "The analysed layouts show broadly consistent results; continue with detailed design-stage review."
        )
    return recommendations
