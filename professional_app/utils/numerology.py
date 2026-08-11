from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


CHALDEAN_VALUES: dict[str, int] = {
    "A": 1, "I": 1, "J": 1, "Q": 1, "Y": 1,
    "B": 2, "K": 2, "R": 2,
    "C": 3, "G": 3, "L": 3, "S": 3,
    "D": 4, "M": 4, "T": 4,
    "E": 5, "H": 5, "N": 5, "X": 5,
    "U": 6, "V": 6, "W": 6,
    "O": 7, "Z": 7,
    "F": 8, "P": 8,
}

DEFAULT_COMPATIBILITY: dict[int, set[int]] = {
    1: {1, 2, 4, 7},
    2: {1, 2, 4, 7},
    3: {3, 6, 9},
    4: {1, 2, 4, 7},
    5: {5, 6},
    6: {3, 5, 6, 9},
    7: {1, 2, 4, 7},
    8: {8},
    9: {3, 6, 9},
}

RULES_PATH = Path(__file__).resolve().parents[1] / "config" / "numerology_rules.json"


def load_rules() -> dict[str, Any]:
    try:
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def reduce_to_root(number: int, preserve_master: bool = False) -> int:
    number = abs(int(number))
    if preserve_master and number in {11, 22, 33}:
        return number
    while number > 9:
        number = sum(int(digit) for digit in str(number))
        if preserve_master and number in {11, 22, 33}:
            return number
    return number


def normalise_name(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(ch for ch in ascii_name.upper() if ch.isalpha())


def chaldean_name_number(name: str) -> dict[str, int | str]:
    cleaned = normalise_name(name)
    compound = sum(CHALDEAN_VALUES.get(ch, 0) for ch in cleaned)
    return {
        "cleaned_name": cleaned,
        "compound_number": compound,
        "root_number": reduce_to_root(compound) if compound else 0,
    }


def birth_number(dob: date) -> int:
    return reduce_to_root(dob.day)


def destiny_number(dob: date) -> int:
    return reduce_to_root(sum(int(ch) for ch in dob.strftime("%d%m%Y")))


def attitude_number(dob: date) -> int:
    """Day + month root; used here as an optional supporting indicator."""
    return reduce_to_root(dob.day + dob.month)


def personal_year_number(dob: date, year: int | None = None) -> int:
    target_year = year or date.today().year
    return reduce_to_root(dob.day + dob.month + sum(int(x) for x in str(target_year)))


def property_number(flat_number: str) -> dict[str, int | str]:
    """Supports 1203, A-1203, Villa 8B and similar identifiers."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", str(flat_number)).upper()
    total = 0
    breakdown: list[str] = []
    for ch in cleaned:
        value = int(ch) if ch.isdigit() else CHALDEAN_VALUES.get(ch, 0)
        total += value
        breakdown.append(f"{ch}={value}")
    return {
        "cleaned_property_number": cleaned,
        "compound_number": total,
        "root_number": reduce_to_root(total) if total else 0,
        "breakdown": breakdown,
    }


def compatibility_map(rules: dict[str, Any]) -> dict[int, set[int]]:
    configured = rules.get("compatibility", {})
    result: dict[int, set[int]] = {}
    for number in range(1, 10):
        values = configured.get(str(number))
        result[number] = set(int(x) for x in values) if isinstance(values, list) else DEFAULT_COMPATIBILITY[number]
    return result


def pair_assessment(reference: int, property_root: int, compatibility: dict[int, set[int]]) -> dict[str, Any]:
    if not reference or not property_root:
        return {"score_5": 0.0, "status": "Not assessed", "explanation": "Required number is unavailable."}
    if property_root == reference:
        return {"score_5": 5.0, "status": "Exact match", "explanation": f"Property root {property_root} exactly matches {reference}."}
    if property_root in compatibility.get(reference, set()):
        return {"score_5": 4.0, "status": "Compatible", "explanation": f"Property root {property_root} is in the configured compatibility group for {reference}."}
    return {"score_5": 2.0, "status": "Caution", "explanation": f"Property root {property_root} is outside the configured compatibility group for {reference}."}


def number_profile(number: int, rules: dict[str, Any]) -> dict[str, Any]:
    profile = rules.get("number_profiles", {}).get(str(number), {})
    return {
        "number": number,
        "planet": profile.get("planet", "Not configured"),
        "keywords": profile.get("keywords", []),
        "supportive_directions": profile.get("supportive_directions", []),
        "supportive_colours": profile.get("supportive_colours", []),
        "summary": profile.get("summary", "No interpretation configured."),
    }


def compound_interpretation(compound: int, rules: dict[str, Any]) -> str:
    return rules.get("compound_notes", {}).get(str(compound), "No specific compound-number note is configured; interpret primarily through the root number.")


def confidence_label(coverage: int) -> str:
    if coverage >= 100:
        return "High"
    if coverage >= 75:
        return "Moderate"
    if coverage >= 50:
        return "Limited"
    return "Insufficient information"


def calculate_numerology(owner_name: str, dob: date, flat_number: str, assessment_year: int | None = None) -> dict[str, object]:
    rules = load_rules()
    compatibility = compatibility_map(rules)
    name_result = chaldean_name_number(owner_name)
    property_result = property_number(flat_number)

    birth = birth_number(dob)
    destiny = destiny_number(dob)
    attitude = attitude_number(dob)
    personal_year = personal_year_number(dob, assessment_year)
    name_root = int(name_result["root_number"])
    property_root = int(property_result["root_number"])

    comparisons: list[dict[str, Any]] = []
    weights = {"Birth number": 0.40, "Destiny number": 0.40}
    if name_root:
        weights["Name number"] = 0.20
    else:
        # Missing optional name must not reduce the score.
        weights = {"Birth number": 0.50, "Destiny number": 0.50}

    references = {"Birth number": birth, "Destiny number": destiny, "Name number": name_root}
    weighted = 0.0
    for label, weight in weights.items():
        assessment = pair_assessment(references[label], property_root, compatibility)
        weighted += float(assessment["score_5"]) * weight
        comparisons.append({"reference": label, "number": references[label], "weight": weight, **assessment})

    score_10 = round(weighted * 2, 1)
    coverage = 100 if name_root else 80
    strengths = [x["explanation"] for x in comparisons if x["status"] in {"Exact match", "Compatible"}]
    cautions = [x["explanation"] for x in comparisons if x["status"] == "Caution"]

    return {
        "system": "Chaldean-inspired configurable engine",
        "assessment_year": assessment_year or date.today().year,
        "birth_number": birth,
        "destiny_number": destiny,
        "attitude_number": attitude,
        "personal_year_number": personal_year,
        "name_compound_number": name_result["compound_number"],
        "name_root_number": name_root,
        "property_cleaned_number": property_result["cleaned_property_number"],
        "property_breakdown": property_result["breakdown"],
        "property_compound_number": property_result["compound_number"],
        "property_root_number": property_root,
        "property_compound_note": compound_interpretation(int(property_result["compound_number"]), rules),
        "score": score_10,
        "coverage": coverage,
        "confidence": confidence_label(coverage),
        "comparisons": comparisons,
        "profiles": {
            "birth": number_profile(birth, rules),
            "destiny": number_profile(destiny, rules),
            "name": number_profile(name_root, rules) if name_root else {},
            "property": number_profile(property_root, rules),
            "personal_year": number_profile(personal_year, rules),
        },
        "strengths": strengths,
        "cautions": cautions,
        "disclaimer": "Numerology is a belief-based interpretive practice and is not scientifically validated.",
    }
