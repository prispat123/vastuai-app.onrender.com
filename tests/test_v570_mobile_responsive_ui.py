from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_app_uses_auto_sidebar_for_mobile():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'initial_sidebar_state="auto"' in source


def test_global_mobile_breakpoint_stacks_columns():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '@media (max-width: 768px)' in source
    assert 'div[data-testid="stHorizontalBlock"] {flex-direction:column!important' in source
    assert 'div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]' in source


def test_mobile_tabs_tables_and_buttons_are_touch_safe():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'overflow-x:auto!important' in source
    assert 'width:100%!important;min-height:2.7rem!important' in source
    assert '.stTabs [data-baseweb="tab-list"]' in source


def test_mobile_release_version():
    assert '6.0.0' in (ROOT / 'professional_app' / 'version.py').read_text(encoding='utf-8')
    assert '6.0.0' in (ROOT / 'platform_core' / '__init__.py').read_text(encoding='utf-8')
