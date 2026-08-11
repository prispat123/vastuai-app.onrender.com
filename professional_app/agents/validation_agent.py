from __future__ import annotations

from datetime import date

from professional_app.state import PropertyState

VALID_DIRECTIONS = {
    "North", "North-East", "East", "South-East", "South",
    "South-West", "West", "North-West", "Centre",
}

VASTU_FIELDS = (
    ("entrance_direction", "Main entrance"),
    ("kitchen_direction", "Kitchen"),
    ("master_bedroom_direction", "Master bedroom"),
    ("toilet_direction", "Toilet"),
    ("pooja_direction", "Pooja/meditation room"),
    ("living_room_direction", "Living room"),
    ("balcony_direction", "Balcony"),
    ("staircase_direction", "Staircase"),
    ("children_bedroom_direction", "Children's bedroom"),
    ("guest_bedroom_direction", "Guest bedroom"),
    ("dining_direction", "Dining area"),
    ("brahmasthan_direction", "Brahmasthan"),
    ("underground_tank_direction", "Underground tank / borewell"),
    ("overhead_tank_direction", "Overhead tank"),
    ("parking_direction", "Parking"),
)


def validation_agent(state: PropertyState) -> dict:
    errors: list[str] = []
    dob_text = str(state.get("dob", "")).strip()
    flat_number = str(state.get("flat_number", "")).strip()

    valid_vastu = [key for key, _ in VASTU_FIELDS if state.get(key) in VALID_DIRECTIONS]
    vastu_ready = state.get("entrance_direction") in VALID_DIRECTIONS and len(valid_vastu) >= 3

    dob_valid = False
    if dob_text:
        try:
            dob = date.fromisoformat(dob_text)
            dob_valid = date(1900, 1, 1) <= dob <= date.today()
            if not dob_valid:
                errors.append("Date of birth must be between 1 January 1900 and today.")
        except ValueError:
            errors.append("Date of birth is invalid.")

    numerology_ready = bool(flat_number and dob_valid)

    if not vastu_ready and not numerology_ready:
        errors.append(
            "Provide either the main entrance and at least two other confirmed "
            "Vastu directions, or a property number and valid date of birth."
        )

    return {
        "validation_errors": errors,
        "analysis_readiness": {
            "vastu_ready": vastu_ready,
            "numerology_ready": numerology_ready,
            "confirmed_vastu_count": len(valid_vastu),
            "available_vastu_fields": valid_vastu,
        },
    }
