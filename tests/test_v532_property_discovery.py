from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_professional_property_discovery_does_not_require_project_workspace_filter():
    source = (ROOT / "ui_pages" / "projects.py").read_text(encoding="utf-8")
    start = source.index("def _professional_properties")
    end = source.index("def _professional_container_project_id")
    block = source[start:end]
    assert "FROM professional_analyses pa" in block
    assert "LEFT JOIN projects p ON p.id = pa.project_id" in block
    assert "WHERE p.workspace_type='Professional'" not in block
