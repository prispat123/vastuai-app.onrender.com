from __future__ import annotations

import io
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PASTEL_GREEN = "#A8D5BA"
PASTEL_GREEN_DARK = "#5F8F72"
PASTEL_AMBER = "#F6D6A8"
PASTEL_CORAL = "#F3B6A7"

def _score_color(value: float) -> str:
    if value >= 8: return PASTEL_GREEN
    if value >= 6: return "#C7D8C6"
    if value >= 4: return PASTEL_AMBER
    return PASTEL_CORAL

DIRECTION_ORDER = [
    "North", "North-East", "East", "South-East",
    "South", "South-West", "West", "North-West",
]


def normalise_direction(value: Any) -> str:
    raw = str(value or "").strip().title().replace(" ", "-")
    aliases = {
        "Northeast": "North-East", "North-East": "North-East",
        "Southeast": "South-East", "South-East": "South-East",
        "Southwest": "South-West", "South-West": "South-West",
        "Northwest": "North-West", "North-West": "North-West",
        "North": "North", "East": "East", "South": "South", "West": "West",
    }
    return aliases.get(raw, raw)


def direction_balance(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = {direction: [] for direction in DIRECTION_ORDER}
    for item in details or []:
        direction = normalise_direction(item.get("direction"))
        if direction in grouped:
            try:
                grouped[direction].append(float(item.get("score", 0) or 0))
            except (TypeError, ValueError):
                grouped[direction].append(0.0)
    return [
        {
            "direction": direction,
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            "room_count": len(scores),
        }
        for direction, scores in grouped.items()
    ]


def room_scores(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in details or []:
        try:
            score = round(float(item.get("score", 0) or 0), 2)
        except (TypeError, ValueError):
            score = 0.0
        rows.append({
            "area": str(item.get("area") or "Area"),
            "direction": str(item.get("direction") or "Unknown"),
            "score": score,
            "severity": str(item.get("severity") or "N/A"),
            "status": str(item.get("status") or "N/A"),
        })
    return rows


def build_direction_wheel_png(details: list[dict[str, Any]], dpi: int = 160) -> bytes:
    summary = direction_balance(details)
    scores = [row["average_score"] for row in summary]
    angles = np.linspace(0, 2 * np.pi, len(DIRECTION_ORDER), endpoint=False).tolist()
    closed_angles = angles + angles[:1]
    closed_scores = scores + scores[:1]

    fig = plt.figure(figsize=(6.4, 5.8))
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.plot(closed_angles, closed_scores, marker="o", linewidth=2, color=PASTEL_GREEN_DARK, label="Average room score")
    ax.fill(closed_angles, closed_scores, alpha=0.16)
    ax.set_xticks(angles)
    ax.set_xticklabels(DIRECTION_ORDER, fontsize=8)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_title("Directional Balance Wheel", pad=20)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.20), fontsize=8)
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output.getvalue()


def build_room_scores_png(details: list[dict[str, Any]], dpi: int = 160) -> bytes:
    rows = room_scores(details)
    labels = [row["area"] for row in rows]
    scores = [row["score"] for row in rows]
    height = max(3.2, min(9.5, 1.4 + len(rows) * 0.42))
    fig, ax = plt.subplots(figsize=(7.2, height))
    if rows:
        positions = np.arange(len(rows))
        ax.barh(positions, scores, color=[_score_color(v) for v in scores], label="Room score")
        ax.set_yticks(positions)
        ax.set_yticklabels(labels, fontsize=8)
        ax.invert_yaxis()
        for index, score in enumerate(scores):
            ax.text(min(score + 0.12, 9.6), index, f"{score:g}", va="center", fontsize=8)
    else:
        ax.text(0.5, 0.5, "No room-level Vastu scores available", ha="center", va="center", transform=ax.transAxes)
    ax.set_xlim(0, 10)
    ax.set_xlabel("Score out of 10")
    ax.set_title("Room-wise Vastu Scores")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    return output.getvalue()
