from __future__ import annotations

import base64
import json
from typing import Any

from platform_core.openai_service import OPENAI


ALLOWED_DIRECTIONS = {
    "North", "North-East", "East", "South-East", "South",
    "South-West", "West", "North-West", "Centre", "Unknown",
}

ROOM_KEYS = (
    "entrance_direction",
    "kitchen_direction",
    "master_bedroom_direction",
    "toilet_direction",
    "pooja_direction",
    "living_room_direction",
    "balcony_direction",
    "staircase_direction",
)


def _normalise_direction(value: Any) -> str:
    text = str(value or "Unknown").strip().title().replace("Northeast", "North-East")
    text = text.replace("Southeast", "South-East").replace("Southwest", "South-West")
    text = text.replace("Northwest", "North-West")
    return text if text in ALLOWED_DIRECTIONS else "Unknown"


def inspect_floor_plan(
    image_bytes: bytes,
    detail: str = "high",
    north_orientation: str = "Auto-detect",
) -> dict[str, Any]:
    """Use an OpenAI vision-capable model to validate and extract a floor plan."""
    if not OPENAI.configured:
        raise RuntimeError(
            "OPENAI_API_KEY is required for automatic North-arrow detection and layout extraction."
        )

    model = OPENAI.models.vision_model
    data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")

    manual_north = north_orientation != "Auto-detect"
    north_instruction = (
        f"The user has confirmed that {north_orientation} is North. "
        "Treat this as authoritative, set north_detected=true, and derive room directions from it. "
        "Do not require a printed North arrow."
        if manual_north
        else
        "Auto-detect North only from a clearly printed or drawn North arrow/compass. "
        "If it is absent or unreadable, set north_detected=false and return Unknown room directions."
    )

    prompt = """
You are validating a residential floor plan for a Vastu assessment.
Return JSON only.
__NORTH_INSTRUCTION__

Hard rules:
1. Decide whether the image is genuinely a floor plan.
2. When North is user-confirmed, use that orientation as authoritative.
3. When Auto-detect is selected, never infer North from page orientation, text orientation, sunlight, roads, or convention.
4. Derive each visible room's cardinal direction from its geometric location relative to the confirmed or detected North.
5. Use only: North, North-East, East, South-East, South, South-West, West, North-West, Centre, Unknown.
6. Confidence values must be between 0 and 1.
7. Do not invent rooms that are not visible.

Return this exact object shape:
{
  "is_floor_plan": true,
  "north_detected": true,
  "north_confidence": 0.0,
  "north_description": "",
  "vision_quality_score": 0,
  "issues": [],
  "rooms": {
    "entrance_direction": {"value": "Unknown", "confidence": 0.0},
    "kitchen_direction": {"value": "Unknown", "confidence": 0.0},
    "master_bedroom_direction": {"value": "Unknown", "confidence": 0.0},
    "toilet_direction": {"value": "Unknown", "confidence": 0.0},
    "pooja_direction": {"value": "Unknown", "confidence": 0.0},
    "living_room_direction": {"value": "Unknown", "confidence": 0.0},
    "balcony_direction": {"value": "Unknown", "confidence": 0.0},
    "staircase_direction": {"value": "Unknown", "confidence": 0.0}
  },
  "notes": ""
}
""".strip().replace(
        "__NORTH_INSTRUCTION__",
        north_instruction,
    )

    client = OPENAI.client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": detail}},
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)
    rooms = parsed.get("rooms") if isinstance(parsed.get("rooms"), dict) else {}

    normalised_rooms: dict[str, dict[str, Any]] = {}
    for key in ROOM_KEYS:
        item = rooms.get(key, {}) if isinstance(rooms.get(key), dict) else {}
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0) or 0.0)))
        value = _normalise_direction(item.get("value"))
        minimum_confidence = 0.40 if manual_north else 0.60
        if confidence < minimum_confidence:
            value = "Unknown"
        normalised_rooms[key] = {"value": value, "confidence": confidence}

    return {
        "is_floor_plan": bool(parsed.get("is_floor_plan", False)),
        "north_detected": True if manual_north else bool(parsed.get("north_detected", False)),
        "north_confidence": (
            1.0
            if manual_north
            else max(
                0.0,
                min(
                    1.0,
                    float(parsed.get("north_confidence", 0.0) or 0.0),
                ),
            )
        ),
        "north_description": (
            f"User confirmed: {north_orientation}"
            if manual_north
            else str(parsed.get("north_description", "")).strip()
        ),
        "confirmed_north_orientation": (
            north_orientation if manual_north else ""
        ),
        "vision_quality_score": int(parsed.get("vision_quality_score", 0) or 0),
        "issues": [str(x) for x in parsed.get("issues", []) if str(x).strip()],
        "rooms": normalised_rooms,
        "notes": str(parsed.get("notes", "")).strip(),
        "model": model,
    }
