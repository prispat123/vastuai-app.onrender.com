from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_ensure_seeded_checks_hash_version_and_count():
    source = (
        ROOT / "knowledge_engine" / "importer.py"
    ).read_text(encoding="utf-8")
    assert "expected_hash = source.source_hash()" in source
    assert "expected_version" in source
    assert "expected_rules = len(bundle" in source
    assert "import_json_master(source)" in source


def test_report_sidebar_section_is_forwarded():
    detail = (
        ROOT / "ui_pages" / "project_detail.py"
    ).read_text(encoding="utf-8")
    workspace = (
        ROOT / "ui_pages" / "professional_workspace.py"
    ).read_text(encoding="utf-8")
    assert "professional_workspace.render(project, section)" in detail
    assert "requested_section=section" in workspace


def test_professional_report_has_direct_page():
    source = (
        ROOT / "professional_app" / "ui.py"
    ).read_text(encoding="utf-8")
    assert "def render_saved_report_page()" in source
    assert 'requested_section == "Report"' in source
    assert "Download visual professional PDF" in source
    assert "Download complete export package" in source


def test_backward_compatible_professional_render_entry():
    source = (
        ROOT / "professional_app" / "ui.py"
    ).read_text(encoding="utf-8")
    assert "def render(project_id: int) -> None:" in source
    assert "def render_section(" in source
