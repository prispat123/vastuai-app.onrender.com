from pathlib import Path
ROOT=Path(__file__).parents[1]

def test_ui_is_q_and_a_focused():
    s=(ROOT/'ui_pages'/'gpt_intelligence.py').read_text(encoding='utf-8')
    assert 'st.tabs(["Q&A", "History"])' in s
    assert 'Explain This Flat' not in s
    assert 'Generate Tower Executive Summary' not in s
    assert 'Generate Building Executive Summary' not in s
    assert s.count('"Ask AI Consultant"') == 1

def test_settings_are_compact():
    s=(ROOT/'ui_pages'/'gpt_intelligence.py').read_text(encoding='utf-8')
    assert 'st.expander("AI Consultant Settings"' in s
    assert 'Reasoning effort' in s
    assert 'Answer style' in s

def test_reports_are_highlighted():
    s=(ROOT/'ui_pages'/'gpt_intelligence.py').read_text(encoding='utf-8')
    assert 'For structured and in-depth details' in s
    assert 'Dashboard & Reports' in s

def test_service_is_qa_only():
    s=(ROOT/'project_intelligence'/'gpt_service.py').read_text(encoding='utf-8')
    assert 'def generate_project_answer(' in s
    assert 'AI Consultant supports project Q&A only' in s

def test_numerology_scope_is_individual_only():
    s=(ROOT/'architecture'/'NUMEROLOGY_SCOPE.md').read_text(encoding='utf-8')
    assert 'only to an individual property' in s
    assert 'must not independently score or assess an entire tower' in s
    assert 'must not be directly compared or averaged' in s

def test_low_default_for_speed():
    db=(ROOT/'platform_core'/'database.py').read_text(encoding='utf-8')
    svc=(ROOT/'project_intelligence'/'gpt_service.py').read_text(encoding='utf-8')
    assert "reasoning_effort TEXT NOT NULL DEFAULT 'low'" in db
    assert '(DEFAULT_MODEL, "low", "Professional")' in svc
