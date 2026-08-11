from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from numerology_engine.calculations import (
    birth_number,
    life_path_number,
    property_number,
)
from numerology_engine.repository import NumerologyRepository


class NumerologyEngine:
    def __init__(self, repository: NumerologyRepository | None = None):
        self.repository = repository or NumerologyRepository()

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 90:
            return "Excellent"
        if score >= 80:
            return "Very Good"
        if score >= 70:
            return "Good"
        if score >= 60:
            return "Balanced"
        return "Review"

    def evaluate(
        self,
        *,
        intended_user_name: str,
        date_of_birth: date,
        property_identifier: str,
        property_name: str = "",
        method_profile: str = "foundational",
    ) -> dict[str, Any]:
        birth = birth_number(date_of_birth)
        life = life_path_number(date_of_birth)
        prop = property_number(property_identifier)

        number_objects = [
            self.repository.object_for_number("birth_number", birth),
            self.repository.object_for_number("life_path_number", life),
            self.repository.object_for_number("property_number", prop),
        ]
        number_objects = [row for row in number_objects if row]

        alignment_ids = []
        if prop == birth:
            alignment_ids.append("NUM-ALIGN-EXACT-BIRTH")
        if prop == life:
            alignment_ids.append("NUM-ALIGN-EXACT-LIFE")
        if birth == life == prop:
            alignment_ids.append("NUM-ALIGN-BOTH")
        if not alignment_ids:
            alignment_ids.append("NUM-ALIGN-NO-EXACT")

        alignments = [
            self.repository.alignment_object(object_id)
            for object_id in alignment_ids
        ]
        alignments = [row for row in alignments if row]

        # A transparent starter score. The score is independent of Vastu and
        # is based only on the versioned alignment objects in this profile.
        score = 64.0 + sum(
            float(row.get("score_delta", 0) or 0)
            for row in alignments
        )
        score = max(0.0, min(100.0, score))

        confidences = [
            float(row.get("confidence", 0) or 0)
            for row in number_objects + alignments
        ]
        confidence = (
            round(sum(confidences) / len(confidences), 3)
            if confidences
            else 0.0
        )

        result = {
            "domain": "professional_numerology",
            "scope": "individual_property_and_intended_user",
            "method_profile": method_profile,
            "knowledge_version": self.repository.meta()[
                "knowledge_version"
            ],
            "inputs": {
                "intended_user_name": intended_user_name.strip(),
                "date_of_birth": date_of_birth.isoformat(),
                "property_identifier": property_identifier.strip(),
                "property_name": property_name.strip(),
            },
            "calculated_numbers": {
                "birth_number": birth,
                "life_path_number": life,
                "property_number": prop,
            },
            "number_objects": number_objects,
            "alignment_objects": alignments,
            "numerology_score": round(score, 1),
            "grade": self._grade(score),
            "confidence": confidence,
            "disclaimer": (
                "Numerology is belief-based and interpretations vary by "
                "school. This assessment is independent of the Vastu score "
                "and does not assess a tower, building or project."
            ),
        }
        result["input_hash"] = hashlib.sha256(
            json.dumps(
                result["inputs"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return result
