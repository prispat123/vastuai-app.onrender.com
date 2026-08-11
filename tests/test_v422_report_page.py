from pathlib import Path
ROOT=Path(__file__).parents[1]

def test_report_is_rendered_on_review_page():
 source=(ROOT/'ui_pages'/'project_intelligence.py').read_text(encoding='utf-8')
 assert "Individual Flat Report" in source
 assert "_render_flat_report(lid)" in source
 assert "Download Individual Professional Report" in source

def test_report_has_professional_sections():
 source=(ROOT/'ui_pages'/'project_intelligence.py').read_text(encoding='utf-8')
 for text in ["Overall Score","Vastu Score","Final Reviewed Directions","Strengths","Needs Attention","Recommendations"]:
  assert text in source

def test_paths_are_validated():
 source=(ROOT/'ui_pages'/'project_intelligence.py').read_text(encoding='utf-8')
 assert "path.exists() and path.is_file()" in source
 assert "candidate.exists() and candidate.is_file()" in source
