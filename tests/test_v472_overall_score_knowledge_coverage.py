from pathlib import Path
import json

from assessment_core.composite_score import (
    deterministic_summary,
    overall_professional_score,
)


ROOT = Path(__file__).parents[1]


def test_equal_weight_composite():
    result = overall_professional_score(7.5, 64.0)
    assert result["score"] == 7.0
    assert result["score_100"] == 69.5
    assert result["weights"] == {"vastu": 0.5, "numerology": 0.5}
    assert "equal weight" in result["footnote"].lower()


def test_single_domain_fallback_is_transparent():
    vastu_only = overall_professional_score(8.2, None)
    assert vastu_only["score"] == 8.2
    assert vastu_only["basis"] == "Vastu only"


def test_every_professional_direction_has_knowledge_object():
    vastu_rules = json.loads(
        (ROOT / "professional_app" / "config" / "vastu_rules.json")
        .read_text(encoding="utf-8")
    )
    rule_rows = []
    for path in (ROOT / "knowledge" / "rules").glob("*.json"):
        rule_rows.extend(
            json.loads(path.read_text(encoding="utf-8"))["rules"]
        )
    available = {
        (row["field"], row["direction"])
        for row in rule_rows
        if row.get("active", True)
    }
    assert len(rule_rows) == 130
    expected = {
        (field, direction)
        for field, config in vastu_rules.items()
        for direction in config["scores"]
    }
    assert expected <= available


def test_missing_report_ids_are_no_longer_expected():
    files = {
        path.name
        for path in (ROOT / "knowledge" / "rules").glob("*.json")
    }
    assert "children_bedroom.json" in files
    assert "guest_bedroom.json" in files


def test_scoring_agent_uses_equal_weight_helper():
    source = (
        ROOT / "professional_app" / "agents" / "scoring_agent.py"
    ).read_text(encoding="utf-8")
    assert "overall_professional_score(" in source
    assert "0.65" not in source
    assert "0.35" not in source


def test_core_explanation_is_deterministic():
    source = (
        ROOT / "professional_app" / "agents" / "explanation_agent.py"
    ).read_text(encoding="utf-8")
    assert "deterministic_summary(" in source
    assert "OpenAI" not in source
    assert "responses.create" not in source


def test_ui_and_pdf_explain_weighting():
    ui = (
        ROOT / "professional_app" / "ui.py"
    ).read_text(encoding="utf-8")
    pdf = (
        ROOT / "professional_app" / "services" / "pdf_service.py"
    ).read_text(encoding="utf-8")
    assert "Overall Professional Score" in ui
    assert "50% each" in ui
    assert "Overall Professional Score" in pdf
    assert 'final.get("footnote")' in pdf


def test_knowledge_coverage_dashboard_exists():
    source = (
        ROOT / "ui_pages" / "knowledge_components.py"
    ).read_text(encoding="utf-8")
    assert "Professional Knowledge Coverage" in source
    assert "Missing objects" in source
    assert "professional_coverage()" in source


def test_summary_grade_matches_numerology_score():
    summary = deterministic_summary(
        payload={"owner_name": "Buyer", "flat_number": "901"},
        vastu={"score": 7.5, "grade": "B+", "evaluated_count": 9, "coverage": 60},
        numerology={"score_100": 64.0, "grade": "Balanced"},
        final=overall_professional_score(7.5, 64.0),
        recommendation={"actions": []},
    )
    assert "64.0/100 (Balanced)" in summary
    assert "highly supportive" not in summary.lower()
