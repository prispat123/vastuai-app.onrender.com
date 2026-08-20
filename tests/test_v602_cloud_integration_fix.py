from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_property_landing_uses_cloud_repository():
    text=(ROOT/'ui_pages'/'projects.py').read_text(encoding='utf-8')
    assert 'cloud_repository.enabled()' in text
    assert 'cloud_repository.list_professional_analyses' in text
    assert 'active_project_id = _professional_container_project_id()' in text

def test_openai_health_reports_runtime_env_without_secret():
    text=(ROOT/'platform_core'/'openai_service.py').read_text(encoding='utf-8')
    assert 'runtime_env_present' in text
    assert 'streamlit_secret_present' in text

def test_professional_openai_warning_mentions_render_runtime():
    text=(ROOT/'professional_app'/'ui.py').read_text(encoding='utf-8')
    assert 'Render service Environment variable named exactly OPENAI_API_KEY' in text
