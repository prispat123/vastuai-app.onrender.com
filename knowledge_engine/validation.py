from __future__ import annotations

from typing import Any


VALID_POLARITIES = {"positive", "negative", "neutral"}
VALID_SEVERITIES = {"Critical", "High", "Medium", "Low"}


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    manifest = bundle.get("manifest", {})
    rules = bundle.get("rules", [])
    recommendations = bundle.get("recommendations", [])
    profiles = bundle.get("profiles", {})
    links = bundle.get("links", [])

    if not manifest.get("knowledge_version"):
        errors.append("Manifest knowledge_version is required.")
    if not isinstance(manifest.get("schema_version"), int):
        errors.append("Manifest schema_version must be an integer.")

    rule_ids = [str(row.get("rule_id", "")).strip() for row in rules]
    rec_ids = [
        str(row.get("recommendation_id", "")).strip()
        for row in recommendations
    ]

    if any(not value for value in rule_ids):
        errors.append("Every rule requires a rule_id.")
    if len(rule_ids) != len(set(rule_ids)):
        errors.append("Duplicate rule IDs found.")

    if any(not value for value in rec_ids):
        errors.append("Every recommendation requires an ID.")
    if len(rec_ids) != len(set(rec_ids)):
        errors.append("Duplicate recommendation IDs found.")

    rule_set = set(rule_ids)
    rec_set = set(rec_ids)

    for rule in rules:
        rule_id = rule.get("rule_id", "?")
        if rule.get("polarity") not in VALID_POLARITIES:
            errors.append(f"{rule_id}: invalid polarity.")
        if rule.get("severity") not in VALID_SEVERITIES:
            errors.append(f"{rule_id}: invalid severity.")
        try:
            confidence = float(rule.get("knowledge_confidence", 0))
        except (TypeError, ValueError):
            errors.append(f"{rule_id}: confidence is not numeric.")
        else:
            if not 0 <= confidence <= 1:
                errors.append(f"{rule_id}: confidence must be 0–1.")

        for rec_id in rule.get("recommendation_ids", []):
            if rec_id not in rec_set:
                errors.append(
                    f"{rule_id}: recommendation {rec_id} does not exist."
                )

    if not profiles:
        errors.append("At least one profile is required.")

    for link in links:
        source = link.get("source_rule_id")
        target = link.get("target_rule_id")
        if source not in rule_set:
            errors.append(f"Link source {source} does not exist.")
        if target not in rule_set:
            errors.append(f"Link target {target} does not exist.")
        if source == target:
            errors.append(f"Rule {source} cannot link to itself.")

    return errors
