from __future__ import annotations

from collections import Counter
from typing import Any

from knowledge_engine.repository import KnowledgeRepository


UNKNOWN_VALUES = {"", "Unknown", "None", "N/A", None}


class KnowledgeEngine:
    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
    ):
        self.repository = repository or KnowledgeRepository()

    @staticmethod
    def _normalise_confidence(value: Any) -> float:
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            return 0.0
        if number > 1:
            number /= 100
        return max(0.0, min(1.0, number))

    def evaluate(
        self,
        observations: dict[str, Any],
        *,
        profile: str = "practical",
        detection_confidences: dict[str, float] | None = None,
    ) -> dict:
        profiles = self.repository.profiles()
        if profile not in profiles:
            raise ValueError(f"Unknown Knowledge profile: {profile}")

        detection_confidences = detection_confidences or {}
        recommendation_map = self.repository.recommendations()

        findings: list[dict] = []
        unresolved: list[str] = []

        supported_fields = sorted(
            {rule["field"] for rule in self.repository.rules()}
        )

        for field in supported_fields:
            observed = observations.get(field, "Unknown")
            if observed in UNKNOWN_VALUES:
                unresolved.append(field)
                continue

            matched = [
                rule
                for rule in self.repository.rules()
                if rule["field"] == field
                and rule["direction"] == str(observed)
            ]

            for rule in matched:
                detection = self._normalise_confidence(
                    detection_confidences.get(field, 1.0)
                )
                knowledge = self._normalise_confidence(
                    rule.get("knowledge_confidence", 0)
                )
                weight = float(
                    rule.get("profile_weights", {}).get(profile, 1.0)
                )

                enriched = dict(rule)
                enriched["observed_value"] = str(observed)
                enriched["detection_confidence"] = detection
                enriched["combined_confidence"] = round(
                    detection * knowledge,
                    3,
                )
                enriched["weighted_score_delta"] = round(
                    float(rule.get("score_delta", 0)) * weight,
                    2,
                )
                enriched["recommendations"] = [
                    recommendation_map[rec_id]
                    for rec_id in rule.get("recommendation_ids", [])
                    if rec_id in recommendation_map
                ]
                findings.append(enriched)

        strengths = [
            item for item in findings
            if item["polarity"] == "positive"
        ]
        concerns = [
            item for item in findings
            if item["polarity"] == "negative"
        ]

        severity_rank = {
            "Critical": 0,
            "High": 1,
            "Medium": 2,
            "Low": 3,
        }

        seen: set[str] = set()
        priority_actions: list[dict] = []

        for finding in sorted(
            concerns,
            key=lambda item: severity_rank.get(
                item.get("severity", "Low"),
                9,
            ),
        ):
            for recommendation in finding.get("recommendations", []):
                rec_id = recommendation["recommendation_id"]
                if rec_id in seen:
                    continue
                seen.add(rec_id)
                priority_actions.append(
                    {
                        **recommendation,
                        "triggered_by": finding["rule_id"],
                        "finding": finding["title"],
                        "severity": finding["severity"],
                        "combined_confidence": finding[
                            "combined_confidence"
                        ],
                    }
                )

        category_counts = Counter(
            item["category"] for item in concerns
        )

        average_confidence = (
            round(
                sum(
                    item["combined_confidence"]
                    for item in findings
                ) / len(findings),
                3,
            )
            if findings
            else 0.0
        )

        summary_parts = [
            f'Knowledge profile: {profiles[profile]["name"]}.',
            (
                f'{len(strengths)} favourable and '
                f'{len(concerns)} cautionary matches.'
            ),
        ]

        if category_counts:
            summary_parts.append(
                "Primary attention areas: "
                + ", ".join(
                    name for name, _ in category_counts.most_common(3)
                )
                + "."
            )

        if unresolved:
            summary_parts.append(
                f"{len(unresolved)} supported field(s) were unresolved."
            )

        return {
            "profile": profile,
            "profile_name": profiles[profile]["name"],
            "findings": findings,
            "strengths": strengths,
            "concerns": concerns,
            "unresolved_fields": unresolved,
            "average_confidence": average_confidence,
            "total_adjustment": round(
                sum(
                    item["weighted_score_delta"]
                    for item in findings
                ),
                2,
            ),
            "priority_actions": priority_actions,
            "reasoning_summary": " ".join(summary_parts),
        }
