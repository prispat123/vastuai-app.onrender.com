from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_professional_radio_uses_callback():
    source = (
        ROOT / "professional_app" / "ui.py"
    ).read_text(encoding="utf-8")
    assert "def change_professional_page()" in source
    assert "on_change=change_professional_page" in source
    assert "selected = st.radio(" not in source

def test_compare_and_dashboard_routes_exist():
    source = (
        ROOT / "professional_app" / "ui.py"
    ).read_text(encoding="utf-8")
    assert 'elif page == "Compare properties":' in source
    assert 'elif page == "Dashboard":' in source

def test_compact_typography_is_present():
    professional = (
        ROOT / "professional_app" / "ui.py"
    ).read_text(encoding="utf-8")
    platform = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'font-size:1.22rem!important' in professional
    assert '.vai-context' in platform and '.vai-chip' in platform
