from __future__ import annotations
from typing import Any


def rank_properties(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda x: float(x.get("overall_score") or 0), reverse=True)
    return [{**row, "rank": index} for index, row in enumerate(ranked, 1)]
