
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_v6010_version():
    assert "6.0.10" in (ROOT/"professional_app"/"version.py").read_text(encoding="utf-8")

def test_room_points_are_indented_under_room_heading():
    text = (ROOT/"professional_app"/"services"/"ai_consultant_service.py").read_text(encoding="utf-8")
    assert "leftIndent=14*mm" in text
    assert "rightIndent=4*mm" in text
    assert "def topic_card" in text
