from pathlib import Path

from knowledge_engine import KnowledgeEngine, KnowledgeRepository

ROOT = Path(__file__).parents[1]


def test_repository_validates():
    repository = KnowledgeRepository()
    assert repository.validate() == []
    assert len(repository.rules()) >= 81
    assert set(repository.profiles()) == {
        "classical",
        "practical",
        "builder",
        "consultant",
    }


def test_engine_generates_explainable_results():
    result = KnowledgeEngine().evaluate(
        {
            "entrance_direction": "North-East",
            "kitchen_direction": "South-West",
            "master_bedroom_direction": "South-West",
            "toilet_direction": "North-East",
            "pooja_direction": "East",
            "living_room_direction": "North",
            "balcony_direction": "East",
            "staircase_direction": "South-West",
            "brahmasthan_direction": "Centre",
        },
        profile="builder",
    )
    assert result["findings"]
    assert result["strengths"]
    assert result["concerns"]
    assert result["priority_actions"]


def test_recalculation_calls_knowledge_service():
    source = (
        ROOT
        / "project_intelligence"
        / "recalculation_service.py"
    ).read_text(encoding="utf-8")
    assert "knowledge_service.evaluate_layout(" in source
    assert "'knowledge_assessment':knowledge" in source


def test_project_ui_has_no_module_level_stored_reference():
    source = (
        ROOT / "ui_pages" / "project_intelligence.py"
    ).read_text(encoding="utf-8")

    before_report_function = source.split(
        "def _render_flat_report(layout_id):",
        1,
    )[0]

    assert "stored.get('knowledge_assessment'" not in before_report_function


def test_knowledge_rendering_is_delegated():
    source = (
        ROOT / "ui_pages" / "project_intelligence.py"
    ).read_text(encoding="utf-8")
    assert "render_assessment(" in source
    assert "render_knowledge_base" in source

    helper = (
        ROOT / "ui_pages" / "knowledge_components.py"
    ).read_text(encoding="utf-8")
    assert "def render_assessment(" in helper
    assert "def render_knowledge_base(" in helper


def test_navigation_contains_knowledge_base():
    source = (
        ROOT / "ui_pages" / "project_detail.py"
    ).read_text(encoding="utf-8")
    assert '"Knowledge Base"' in source
