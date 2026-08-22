from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_v605_version():
    assert '6.0.10' in (ROOT/"professional_app"/"version.py").read_text(encoding="utf-8")

def test_cloud_ai_history_helpers():
    text=(ROOT/"platform_core"/"cloud_repository.py").read_text(encoding="utf-8")
    assert "save_cloud_ai_exchange" in text
    assert "list_cloud_ai_exchanges" in text

def test_portfolio_history_uses_cloud_when_authenticated():
    text=(ROOT/"professional_app"/"services"/"portfolio_chat_service.py").read_text(encoding="utf-8")
    assert "cloud_repository.enabled()" in text
    assert 'context_type="portfolio"' in text

def test_individual_history_uses_cloud_when_authenticated():
    text=(ROOT/"professional_app"/"services"/"ai_consultant_service.py").read_text(encoding="utf-8")
    assert 'context_type="property"' in text

def test_both_pdf_buttons_present():
    text=(ROOT/"professional_app"/"ui.py").read_text(encoding="utf-8")
    assert '"Download AI Response PDF"' in text
    assert '"Download AI Portfolio Response PDF"' in text
