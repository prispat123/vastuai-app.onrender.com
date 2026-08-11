from pathlib import Path

def test_professional_modules_are_namespaced():
    root = Path(__file__).parents[1]
    assert (root / "professional_app" / "ui.py").exists()
    assert (root / "professional_app" / "agents" / "vastu_agent.py").exists()
    text = (root / "professional_app" / "graph.py").read_text(encoding="utf-8")
    assert "professional_app.agents" in text

def test_native_ui_has_render_function():
    text = (
        Path(__file__).parents[1] / "professional_app" / "ui.py"
    ).read_text(encoding="utf-8")
    assert "def render(project_id: int)" in text
    assert "runpy" not in text

def test_professional_history_is_project_scoped():
    text = (
        Path(__file__).parents[1]
        / "professional_app"
        / "services"
        / "history_service.py"
    ).read_text(encoding="utf-8")
    assert "professional_analyses" in text
    assert "project_id" in text
