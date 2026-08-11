from __future__ import annotations

import json
from pathlib import Path

from knowledge_engine import KnowledgeRepository


ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "professional_app" / "config" / "vastu_rules.json"


def professional_coverage() -> dict:
    configured = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    repository = KnowledgeRepository()
    active_rules = repository.rules()
    by_field: dict[str, set[str]] = {}
    for rule in active_rules:
        by_field.setdefault(rule["field"], set()).add(rule["direction"])

    rows = []
    missing_objects = []
    total_expected = 0
    total_available = 0

    for field, config in configured.items():
        expected = set(config.get("scores", {}))
        available = by_field.get(field, set())
        missing = sorted(expected - available)
        total_expected += len(expected)
        total_available += len(expected & available)
        for direction in missing:
            missing_objects.append({
                "field": field,
                "area": config.get("label", field),
                "direction": direction,
            })
        rows.append({
            "field": field,
            "area": config.get("label", field),
            "expected": len(expected),
            "available": len(expected & available),
            "coverage": (
                round(len(expected & available) / len(expected) * 100, 1)
                if expected else 100.0
            ),
            "missing": ", ".join(missing),
        })

    return {
        "overall_coverage": (
            round(total_available / total_expected * 100, 1)
            if total_expected else 100.0
        ),
        "expected_objects": total_expected,
        "available_objects": total_available,
        "missing_count": len(missing_objects),
        "rows": rows,
        "missing_objects": missing_objects,
    }
