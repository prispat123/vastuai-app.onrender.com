
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_v606_version():
    assert "6.0.7" in (ROOT/"professional_app"/"version.py").read_text(encoding="utf-8")

def test_safe_filename_helper_exists():
    text=(ROOT/"professional_app"/"ui.py").read_text(encoding="utf-8")
    assert "def _safe_filename(" in text
    assert "Download AI Response PDF" in text
    assert "Download AI Portfolio Response PDF" in text

def test_header_spacing():
    app=(ROOT/"app.py").read_text(encoding="utf-8")
    ui=(ROOT/"professional_app"/"ui.py").read_text(encoding="utf-8")
    assert "padding-top:2.15rem" in app
    assert "padding:2.15rem 1.1rem 2.5rem 1.1rem" in ui
