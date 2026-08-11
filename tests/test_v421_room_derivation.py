from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_manual_north_prompt_is_authoritative():
    source=(ROOT/"professional_app"/"agents"/"vision_agent.py").read_text(encoding="utf-8")
    assert "Treat this as authoritative" in source
    assert "Do not require a printed North arrow" in source
    assert "True if manual_north" in source

def test_confirm_north_forces_fresh_professional_extraction():
    source=(ROOT/"project_intelligence"/"review_workflow.py").read_text(encoding="utf-8")
    assert "force_refresh=True" in source
    assert "analyse_floor_plan" in source
