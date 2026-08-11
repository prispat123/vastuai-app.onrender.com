import json
from pathlib import Path

from assessment_core.record_compatibility import (
    normalize_numerology_result,
    normalize_professional_result,
)


ROOT = Path(__file__).parents[1]


def test_legacy_score_converts_to_100_scale():
    result = normalize_numerology_result(
        {"score": 6.4, "grade": "Balanced"}
    )
    assert result["score"] == 6.4
    assert result["score_100"] == 64.0
    assert result["grade"] == "Balanced"


def test_grade_is_reconstructed_when_missing():
    result = normalize_numerology_result({"score": 8.6})
    assert result["score_100"] == 86.0
    assert result["grade"] == "Very Good"


def test_current_record_remains_current():
    result = normalize_numerology_result(
        {"score": 7.8, "score_100": 78.0, "grade": "Good"}
    )
    assert result == {
        "score": 7.8,
        "score_100": 78.0,
        "grade": "Good",
    }


def test_legacy_final_score_uses_current_equal_weight_formula():
    stored = {
        "vastu_result": {"score": 7.5, "grade": "B+"},
        "numerology_result": {"score": 6.4, "grade": "Balanced"},
        "final_result": {
            "score": 7.1,
            "rating": "Good",
            "basis": "Legacy formula",
        },
    }
    result = normalize_professional_result(stored)
    assert result["numerology_result"]["score_100"] == 64.0
    assert result["final_result"]["score"] == 7.0
    assert result["final_result"]["weights"] == {
        "vastu": 0.5,
        "numerology": 0.5,
    }


def test_normalization_does_not_mutate_source():
    stored = {
        "vastu_result": {"score": 8.0},
        "numerology_result": {"score": 6.4},
    }
    normalize_professional_result(stored)
    assert "score_100" not in stored["numerology_result"]


def test_history_service_normalizes_loaded_json():
    source = (
        ROOT
        / "professional_app"
        / "services"
        / "history_service.py"
    ).read_text(encoding="utf-8")
    assert "normalize_professional_result" in source
    assert 'json.loads(item.pop("result_json"))' in source


def test_pdf_has_compatibility_boundary():
    source = (
        ROOT
        / "professional_app"
        / "services"
        / "pdf_service.py"
    ).read_text(encoding="utf-8")
    assert "result = normalize_professional_result(result)" in source


def test_pdf_does_not_require_new_knowledge_result():
    source = (
        ROOT
        / "professional_app"
        / "services"
        / "pdf_service.py"
    ).read_text(encoding="utf-8")
    assert 'if numerology.get("score_100") is not None' in source
    assert 'if numerology_knowledge else "Not assessed"' not in source
