from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_numerology_ui_has_no_duplicate_input_form():
    source = (ROOT / "ui_pages" / "professional_numerology.py").read_text(encoding="utf-8")
    assert "Property Details source" in source
    assert "Run Numerology Assessment from Property Details" in source
    assert "date_input(" not in source
    assert "Save Numerology Inputs" not in source


def test_shared_snapshot_keeps_scores_independent():
    source = (ROOT / "assessment_core" / "individual_assessment.py").read_text(encoding="utf-8")
    assert '"averaging_allowed": False' in source
    assert '"direct_comparison_allowed": False' in source
    assert "individual_property_and_intended_user" in source


def test_individual_pdf_has_vastu_and_numerology_knowledge_ids():
    source = (ROOT / "professional_app" / "services" / "pdf_service.py").read_text(encoding="utf-8")
    assert "Knowledge ID" in source
    assert "Numerology Knowledge IDs" in source
    assert "vastu_knowledge" in source
    assert "numerology_knowledge" in source


def test_project_intelligence_reports_are_not_modified_for_numerology():
    source = (ROOT / "project_intelligence" / "report_export_service.py").read_text(encoding="utf-8")
    assert "professional_numerology" not in source
    assert "numerology_score" not in source


def test_numerology_assessment_is_tied_to_saved_professional_analysis():
    source = (ROOT / "professional_numerology" / "service.py").read_text(encoding="utf-8")
    assert "analysis_id" in source
    assert "professional_analyses" in source
    assert "payload_json" in source
