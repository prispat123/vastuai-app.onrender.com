
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v604_version():
    assert "6.0.4" in (ROOT/"professional_app"/"version.py").read_text(encoding="utf-8")

def test_cloud_pdp_has_integer_compat_id():
    text=(ROOT/"platform_core"/"cloud_repository.py").read_text(encoding="utf-8")
    assert "legacy_pdp_id" in text
    assert "sync_cloud_buyers_from_pdps" in text
    assert "cloud_add_to_shortlist" in text

def test_numerology_cloud_branch():
    text=(ROOT/"professional_numerology"/"service.py").read_text(encoding="utf-8")
    assert "cloud_repository.enabled()" in text
    assert "history_service.list_analyses" in text

def test_ai_pdf_download():
    svc=(ROOT/"professional_app"/"services"/"ai_consultant_service.py").read_text(encoding="utf-8")
    ui=(ROOT/"professional_app"/"ui.py").read_text(encoding="utf-8")
    assert "def build_response_pdf" in svc
    assert "Download AI Response PDF" in ui
