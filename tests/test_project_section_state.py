from pathlib import Path

def test_project_section_change_uses_callback():
    source = (
        Path(__file__).parents[1]
        / "ui_pages"
        / "project_detail.py"
    ).read_text(encoding="utf-8")

    assert "def open_professional_workspace()" in source
    assert "on_click=open_professional_workspace" in source

    button_block = source.split(
        'st.button(\n            "Open Professional Assessment Workspace"',
        1,
    )[1]
    assert "st.rerun()" not in button_block.split(")", 1)[0]
