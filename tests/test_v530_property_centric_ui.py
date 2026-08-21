from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_professional_landing_is_property_centric():
    source = (ROOT / "ui_pages" / "projects.py").read_text(encoding="utf-8")
    assert 'Your Properties' in source
    assert 'Select property' in source
    assert 'Add Property' in source
    assert '_professional_properties' in source
    assert 'FROM professional_analyses pa' in source
    assert 'LEFT JOIN projects p ON p.id = pa.project_id' in source
    assert "WHERE p.workspace_type='Professional'" not in source


def test_individual_ai_consultant_has_suggested_questions():
    source = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert '### Suggested questions' in source
    assert 'Why did this property receive its overall score?' in source
    assert 'What are the main concerns or compromises I should know about?' in source
    assert 'What should I verify before making a buying decision?' in source


def test_platform_version_is_v532():
    assert '6.0.8' in (ROOT / 'professional_app' / 'version.py').read_text(encoding='utf-8')
    assert '6.0.8' in (ROOT / 'platform_core' / '__init__.py').read_text(encoding='utf-8')


def test_property_selector_uses_full_property_frame_not_filtered_view():
    source = (ROOT / "ui_pages" / "projects.py").read_text(encoding="utf-8")
    assert 'selector_frame = frame.sort_values("id", ascending=False)' in source
    assert 'for _, row in selector_frame.iterrows()' in source
    assert 'for _, row in view.iterrows()' not in source[source.index('selector_frame = frame.sort_values'):source.index('selected = next')]
