from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_report_service_has_all_exports():
    source = (
        ROOT / "project_intelligence" / "report_export_service.py"
    ).read_text(encoding="utf-8")
    for name in [
        "individual_flat_pdf",
        "tower_pdf",
        "building_pdf",
        "dashboard_pdf",
        "excel_export",
        "csv_exports",
    ]:
        assert f"def {name}(" in source


def test_reports_are_true_pdf_generators():
    source = (
        ROOT / "project_intelligence" / "report_export_service.py"
    ).read_text(encoding="utf-8")
    assert "SimpleDocTemplate" in source
    assert "reportlab" in source
    assert "mime='application/pdf'" not in source


def test_dashboard_exposes_pdf_and_excel_buttons():
    source = (
        ROOT / "ui_pages" / "project_intelligence.py"
    ).read_text(encoding="utf-8")
    assert "Download Building PDF" in source
    assert "Download Dashboard PDF" in source
    assert "Download Selected Tower PDF" in source
    assert "Download Excel Workbook" in source
    assert "Download Selected CSV" in source


def test_individual_page_exposes_enhanced_pdf():
    source = (
        ROOT / "ui_pages" / "project_intelligence.py"
    ).read_text(encoding="utf-8")
    assert "Download Enhanced Individual PDF" in source
    assert "individual_flat_pdf(" in source


def test_openpyxl_is_declared():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "openpyxl" in requirements
