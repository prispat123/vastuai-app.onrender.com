from pathlib import Path


def test_property_navigation_queues_sidebar_section_before_rerun():
    source = (Path(__file__).parents[1] / 'ui_pages' / 'projects.py').read_text(encoding='utf-8')
    open_block = source.split('def _open_property(row: dict) -> None:', 1)[1].split('\n\ndef _new_property', 1)[0]
    new_block = source.split('def _new_property() -> None:', 1)[1].split('\n\ndef ', 1)[0]
    assert 'pending_project_section = "Vastu Analysis"' in open_block
    assert 'project_section = "Vastu Analysis"' not in open_block.replace('pending_project_section', '')
    assert 'pending_project_section = "Vastu Analysis"' in new_block
