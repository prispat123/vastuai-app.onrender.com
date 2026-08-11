from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_manual_north_instruction_is_injected():
    source = (
        ROOT / "professional_app" / "agents" / "vision_agent.py"
    ).read_text(encoding="utf-8")
    assert '.replace(' in source
    assert '"__NORTH_INSTRUCTION__"' in source
    assert "north_instruction" in source
    assert '.replace("north_instruction", north_orientation)' not in source


def test_manual_north_is_authoritative():
    source = (
        ROOT / "professional_app" / "agents" / "vision_agent.py"
    ).read_text(encoding="utf-8")
    assert "Do not require a printed North arrow." in source
    assert "1.0" in source
    assert "confirmed_north_orientation" in source


def test_confirm_north_forces_fresh_extraction():
    source = (
        ROOT / "project_intelligence" / "review_workflow.py"
    ).read_text(encoding="utf-8")
    assert 'north_orientation=north_orientation' in source
    assert 'force_refresh=True' in source
    assert "resolved_room_count" in source
    assert "cursor.rowcount != 1" in source


def test_ui_reports_derivation_result():
    source = (
        ROOT / "ui_pages" / "project_intelligence.py"
    ).read_text(encoding="utf-8")
    assert "Room-direction derivation failed" in source
    assert "room direction(s) were derived" in source
    assert "no room directions were confidently derived" in source
