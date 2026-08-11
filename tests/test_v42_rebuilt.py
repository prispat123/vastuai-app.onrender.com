from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_nav():
 s=(ROOT/'ui_pages/project_detail.py').read_text();assert all(x in s for x in ['Project Setup','Documents & Layout Selection','Layouts','Analysis & Review','Dashboard & Reports'])
def test_review():
 s=(ROOT/'ui_pages/project_intelligence.py').read_text();assert 'Confirm North and Derive Room Directions' in s;assert 'Recalculate Score and Regenerate Report' in s
def test_statuses():
 s=(ROOT/'project_intelligence/review_workflow.py').read_text();assert 'Analysed — North Review Required' in s;assert 'Reviewed — Recalculation Required' in s;assert 'Finalised' in s
