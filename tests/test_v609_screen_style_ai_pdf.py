
from pathlib import Path
import io
ROOT=Path(__file__).resolve().parents[1]
SAMPLE="""Here is a direction-wise color plan.

How this is derived
- Vastu: room directions come from the assessment.
- Numerology: palettes come from the saved profile.

Room-by-room color suggestions
- Main entrance (East)
- Use: warm white with gold accents.
- Why: East aligns with Property No. 1.
- Kitchen (South-East)
- Use: cream or light blue.
- Why: South-East aligns with Personal Year 6.
"""
def _extract(pdf):
    from pypdf import PdfReader
    return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
def test_v609_version():
    assert "6.0.10" in (ROOT/"professional_app"/"version.py").read_text(encoding="utf-8")
def test_screen_style_pdf_clean_and_grouped():
    from professional_app.services.ai_consultant_service import build_response_pdf
    pdf=build_response_pdf(property_name="Avinya Enclave",question="Which colours?",answer=SAMPLE)
    text=_extract(pdf)
    assert pdf.startswith(b"%PDF")
    assert "Your question" in text
    assert "Consultant response" in text
    assert "Room-by-room color suggestions" in text
    assert "Main entrance (East)" in text
    assert "Use: warm white" in text
    assert "South-East" in text
    assert "■" not in text
def test_layout_helpers_present():
    text=(ROOT/"professional_app"/"services"/"ai_consultant_service.py").read_text(encoding="utf-8")
    assert "def section_band" in text
    assert "def topic_card" in text
