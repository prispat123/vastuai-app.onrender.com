from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable
from platform_core.database import connect, transaction
from platform_core.projects import get_project
from platform_core.storage import STORAGE
from professional_app.engine_facade import analyse_professional_layout
from project_intelligence import service

ENGINE_VERSION = "PROFESSIONAL-1.0"

def _layouts(project_id: int, ids: Iterable[int] | None):
    with connect() as connection:
        if ids is None:
            return connection.execute("SELECT * FROM project_layouts WHERE project_id=? ORDER BY tower,floor,flat_number,id", (project_id,)).fetchall()
        ids = [int(value) for value in ids]
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        return connection.execute(f"SELECT * FROM project_layouts WHERE project_id=? AND id IN ({placeholders}) ORDER BY tower,floor,flat_number,id", (project_id, *ids)).fetchall()

def _room_rows(extraction: dict) -> list[dict]:
    rooms = extraction.get("rooms", {}) if isinstance(extraction.get("rooms"), dict) else {}
    labels = [("entrance_direction", "Main entrance"), ("kitchen_direction", "Kitchen"), ("master_bedroom_direction", "Master bedroom"), ("toilet_direction", "Toilet"), ("pooja_direction", "Pooja / meditation"), ("living_room_direction", "Living room"), ("balcony_direction", "Balcony"), ("staircase_direction", "Staircase"), ("children_bedroom_direction", "Children's bedroom"), ("guest_bedroom_direction", "Guest bedroom"), ("dining_direction", "Dining"), ("brahmasthan_direction", "Brahmasthan")]
    output = []
    for field, label in labels:
        raw = rooms.get(field, extraction.get(field, "Unknown"))
        confidence = 0
        if isinstance(raw, dict):
            confidence = raw.get("confidence", 0)
            raw = raw.get("value", "Unknown")
        output.append({"field": field, "room": label, "direction": raw or "Unknown", "confidence": confidence or 0})
    return output

def analyse_selected_layouts(project_id: int, layout_ids: Iterable[int] | None = None, *, north_reference: str = "Auto-detect", generate_reports: bool = True) -> dict:
    project = get_project(project_id)
    if not project:
        raise ValueError("Project not found.")
    layouts = _layouts(project_id, layout_ids)
    results = []
    completed = needs_review = failed = 0
    analysis_root = Path(project["project_folder"]) / "analysis" / "professional_engine"
    report_root = Path(project["project_folder"]) / "reports" / "individual_layouts"
    analysis_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)

    for layout in layouts:
        drawing = Path(layout["drawing_path"] or "")
        if not drawing.exists():
            needs_review += 1
            _update_status(layout, "Needs Review", None, 0)
            results.append({"layout_id": int(layout["id"]), "success": False, "reason": "Layout drawing is missing."})
            continue
        display_name = " · ".join(value for value in [layout["tower"] or "", layout["flat_number"] or "", layout["layout_type"] or ""] if value) or f"Layout {layout['id']}"
        try:
            result = analyse_professional_layout(drawing, property_name=display_name, flat_number=layout["flat_number"] or "", north_reference=north_reference, generate_pdf=generate_reports)
            extraction = result.extraction
            analysis = result.analysis
            room_rows = _room_rows(extraction)
            final = analysis.get("final_result", {})
            vastu = analysis.get("vastu_result", {})
            score = float(final.get("score", vastu.get("score", 0)) or 0)
            quality = float(extraction.get("vision_quality_score", 0) or 0)
            quality = quality / 100 if quality > 1 else quality
            coverage = float(vastu.get("coverage", 0) or 0)
            coverage = coverage / 100 if coverage > 1 else coverage
            confidence = round(max(0, min(1, quality * .7 + coverage * .3)), 3)
            north_detected = bool(extraction.get("north_detected", False))
            unresolved = [
                row for row in room_rows
                if row["direction"] in {"", "Unknown", None}
            ]
            review_reasons = []
            if not north_detected:
                review_reasons.append("North was not confidently detected.")
            if unresolved:
                review_reasons.append(
                    f"{len(unresolved)} room direction(s) require review."
                )

            # The Professional engine completed successfully, so the analysis
            # and report are saved. Manual-review warnings do not discard the
            # completed result.
            status = "Completed"
            completed += 1
            needs_review += int(bool(review_reasons))
            stored = {
                "engine_version": ENGINE_VERSION,
                "layout": dict(layout),
                "extraction": extraction,
                "payload": result.payload,
                "analysis": analysis,
                "room_rows": room_rows,
                "north_detected": north_detected,
                "confidence": confidence,
                "status": status,
                "review_reasons": review_reasons,
            }
            json_path = analysis_root / f"layout_{layout['id']}_professional.json"
            STORAGE.write_json(json_path, stored, overwrite=True)
            pdf_path = ""
            if result.pdf_bytes:
                report_file = report_root / f"layout_{layout['id']}_professional_report.pdf"
                STORAGE.save_bytes(report_file, result.pdf_bytes, overwrite=True)
                pdf_path = str(report_file)
            _persist(project_id, int(layout["id"]), score, confidence, status, analysis, str(json_path), pdf_path)
            _update_status(layout, status, score if status == "Completed" else None, confidence)
            results.append({"layout_id": int(layout["id"]), "success": True, "status": status, "score": score, "confidence": confidence, "json_path": str(json_path), "pdf_path": pdf_path, "north_detected": north_detected, "rooms": room_rows})
        except Exception as exc:
            failed += 1
            needs_review += 1
            _update_status(layout, "Needs Review", None, 0)
            results.append({"layout_id": int(layout["id"]), "success": False, "reason": str(exc)})

    service.add_timeline_event(project_id, "PROFESSIONAL_BATCH_ANALYSIS_COMPLETED", "Selected layouts analysed with Professional engine", f"{completed} completed; {needs_review} need review; {failed} failed")
    return {"engine_version": ENGINE_VERSION, "processed": len(layouts), "completed": completed, "needs_review": needs_review, "failed": failed, "results": results}

def _persist(project_id: int, layout_id: int, score: float, confidence: float, status: str, analysis: dict, json_path: str, pdf_path: str) -> None:
    vastu = analysis.get("vastu_result", {})
    final = analysis.get("final_result", {})
    recommendation = analysis.get("recommendation_result", {})
    sql = """INSERT INTO project_layout_analyses(project_id,layout_id,analysis_version,source_extraction_id,vastu_score,overall_score,confidence_label,confidence_value,grade,status,strengths_json,cautions_json,findings_json,recommendations_json,result_json_path) VALUES(?,?,?,NULL,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(layout_id,analysis_version) DO UPDATE SET vastu_score=excluded.vastu_score,overall_score=excluded.overall_score,confidence_label=excluded.confidence_label,confidence_value=excluded.confidence_value,grade=excluded.grade,status=excluded.status,strengths_json=excluded.strengths_json,cautions_json=excluded.cautions_json,findings_json=excluded.findings_json,recommendations_json=excluded.recommendations_json,result_json_path=excluded.result_json_path,updated_at=CURRENT_TIMESTAMP"""
    with transaction() as connection:
        connection.execute(sql, (project_id, layout_id, ENGINE_VERSION, float(vastu.get("score", 0) or 0), score, vastu.get("confidence", "Insufficient"), confidence, vastu.get("grade", final.get("grade", "")), status, json.dumps(vastu.get("strengths", [])), json.dumps(vastu.get("cautions", [])), json.dumps(vastu.get("details", [])), json.dumps(recommendation.get("actions", [])), json_path))
        if pdf_path:
            connection.execute("UPDATE project_layouts SET notes=TRIM(COALESCE(notes,'') || '\nProfessional report: ' || ?) WHERE id=?", (pdf_path, layout_id))

def _update_status(layout, status: str, score: float | None, confidence: float) -> None:
    with transaction() as connection:
        connection.execute("UPDATE project_layouts SET analysis_status=?,overall_score=?,confidence=?,last_analysis_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, score, confidence, int(layout["id"])))
