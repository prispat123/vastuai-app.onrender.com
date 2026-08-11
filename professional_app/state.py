from __future__ import annotations
from typing import Any, TypedDict


class PropertyState(TypedDict, total=False):
    owner_name: str
    dob: str
    flat_number: str
    assessment_year: int
    entrance_direction: str
    kitchen_direction: str
    master_bedroom_direction: str
    toilet_direction: str
    pooja_direction: str
    living_room_direction: str
    balcony_direction: str
    staircase_direction: str
    children_bedroom_direction: str
    guest_bedroom_direction: str
    dining_direction: str
    brahmasthan_direction: str
    underground_tank_direction: str
    overhead_tank_direction: str
    parking_direction: str
    validation_errors: list[str]
    analysis_readiness: dict[str, Any]
    vastu_result: dict[str, Any]
    numerology_result: dict[str, Any]
    final_result: dict[str, Any]
    recommendation_result: dict[str, Any]
    explanation: str
