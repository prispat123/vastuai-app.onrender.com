from pathlib import Path

def test_navigation_sections_are_present():
    source = (Path(__file__).parents[1] / "ui_pages" / "project_detail.py").read_text(encoding="utf-8")
    assert '"Numerology"' in source
    assert '"Documents"' in source
    assert '"Review Layouts"' in source

def test_selection_activates_project():
    source = (Path(__file__).parents[1] / "ui_pages" / "projects.py").read_text(encoding="utf-8")
    assert "active_project_id" in source
    assert "on_change=activate_selected_project" in source
