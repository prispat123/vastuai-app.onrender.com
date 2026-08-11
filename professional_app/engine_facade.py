from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from professional_app.graph import analyze_property
from professional_app.services.floorplan_service import analyse_floor_plan
from professional_app.services.pdf_service import build_pdf

@dataclass
class ProfessionalLayoutResult:
    extraction: dict[str, Any]
    payload: dict[str, Any]
    analysis: dict[str, Any]
    pdf_bytes: bytes | None

def extract_layout(image_path: str | Path, *, north_reference: str = "Auto-detect") -> dict[str, Any]:
    return dict(analyse_floor_plan(Path(image_path).read_bytes(), mode="Detailed", north_orientation=north_reference) or {})

def extraction_to_payload(extraction: dict[str, Any], *, property_name: str, flat_number: str = "") -> dict[str, Any]:
    payload = {"property_name": property_name, "flat_number": flat_number, "owner_name": ""}
    rooms = extraction.get("rooms", {}) if isinstance(extraction.get("rooms"), dict) else {}
    fields = ["entrance_direction", "kitchen_direction", "master_bedroom_direction", "toilet_direction", "pooja_direction", "living_room_direction", "balcony_direction", "staircase_direction", "children_bedroom_direction", "guest_bedroom_direction", "dining_direction", "brahmasthan_direction", "underground_tank_direction", "overhead_tank_direction", "parking_direction"]
    for field in fields:
        raw = rooms.get(field, extraction.get(field, "Unknown"))
        if isinstance(raw, dict):
            raw = raw.get("value", "Unknown")
        payload[field] = raw or "Unknown"
    payload["layout_extraction_confidence"] = extraction.get("vision_quality_score", 0)
    payload["north_detected"] = extraction.get("north_detected", False)
    payload["north_confidence"] = extraction.get("north_confidence", 0)
    payload["north_description"] = extraction.get("north_description", "")
    return payload

def analyse_professional_layout(image_path: str | Path, *, property_name: str, flat_number: str = "", north_reference: str = "Auto-detect", generate_pdf: bool = True) -> ProfessionalLayoutResult:
    extraction = extract_layout(image_path, north_reference=north_reference)
    payload = extraction_to_payload(extraction, property_name=property_name, flat_number=flat_number)
    analysis = analyze_property(payload)
    pdf_bytes = build_pdf(payload, analysis) if generate_pdf else None
    return ProfessionalLayoutResult(extraction, payload, analysis, pdf_bytes)
