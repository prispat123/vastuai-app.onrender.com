from pathlib import Path


def test_no_streamlit_auto_pages_collision():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "pages").exists()
    assert (root / "ui_pages").exists()
    assert (root / "ui_pages" / "home.py").exists()
    assert (root / "ui_pages" / "projects.py").exists()
    assert (root / "ui_pages" / "project_detail.py").exists()
