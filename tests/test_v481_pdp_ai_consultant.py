from pathlib import Path
ROOT = Path(__file__).parents[1]

def test_pdp_schema_and_service():
    db = (ROOT/"platform_core"/"database.py").read_text(encoding="utf-8")
    service = (ROOT/"professional_app"/"services"/"pdp_service.py").read_text(encoding="utf-8")
    assert "property_decision_profiles" in db
    assert "PDP-" in service
    assert '"overall_professional"' in service
    assert '"vastu"' in service
    assert '"numerology"' in service

def test_navigation_and_pages():
    detail = (ROOT/"ui_pages"/"project_detail.py").read_text(encoding="utf-8")
    ui = (ROOT/"professional_app"/"ui.py").read_text(encoding="utf-8")
    assert '"Decision Profiles"' in detail
    assert '"AI Consultant"' in detail
    assert "render_decision_profiles_page" in ui
    assert "render_ai_consultant_page" in ui
    assert "render_decision_profiles_page" in ui

def test_consultant_is_explanatory():
    source = (ROOT/"professional_app"/"services"/"ai_consultant_service.py").read_text(encoding="utf-8")
    assert "Never calculate or change scores" in source
    assert "Knowledge used" in source
