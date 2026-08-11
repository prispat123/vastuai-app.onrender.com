from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_report_service_uses_actual_review_columns_only():
    source = (
        ROOT / "project_intelligence" / "report_export_service.py"
    ).read_text(encoding="utf-8")

    assert "rs.derived_json" in source
    assert "rs.reviewed_json" in source
    assert 'row["derived_json"]' in source
    assert 'row["reviewed_json"]' in source
    assert "derived_directions_json" not in source
    assert "reviewed_directions_json" not in source


def test_report_schema_is_checked_before_query():
    source = (
        ROOT / "project_intelligence" / "report_export_service.py"
    ).read_text(encoding="utf-8")

    assert "PRAGMA table_info(layout_review_state)" in source
    assert "The layout review database schema is incomplete" in source


def test_pdf_generation_is_not_eager_on_page_render():
    source = (
        ROOT / "ui_pages" / "project_intelligence.py"
    ).read_text(encoding="utf-8")

    assert "Generate Enhanced Individual PDF" in source
    assert "Generate Building PDF" in source
    assert "Generate Dashboard PDF" in source
    assert "Generate Selected Tower PDF" in source
    assert "Generate Excel Workbook" in source


def test_generation_errors_are_visible():
    source = (
        ROOT / "ui_pages" / "project_intelligence.py"
    ).read_text(encoding="utf-8")

    assert "Enhanced PDF generation failed" in source
    assert "Building PDF generation failed" in source
    assert "Tower PDF generation failed" in source
    assert "Excel generation failed" in source
