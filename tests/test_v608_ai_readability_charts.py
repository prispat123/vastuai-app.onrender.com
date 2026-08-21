from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ai_pdf_accepts_markdown_table_and_real_newlines():
    from professional_app.services.ai_consultant_service import build_response_pdf

    answer = """## Ranking
| Rank | Property | Score | Trade-off |
|---|---|---:|---|
| 1 | Property A | 7.8 | Strong Vastu |
| 2 | Property B | 7.5 | West balcony |

- Review legal due diligence.
"""
    pdf = build_response_pdf(
        property_name="Test Buyer Portfolio",
        question="Which property is best?",
        answer=answer,
        model_name="gpt-test",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1800


def test_ai_screens_hide_internal_generation_metadata():
    text = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert 'Generation {answer["history_id"]}' not in text
    assert "AI response generated from the current saved shortlist context." in text
    assert "AI response generated from the selected saved assessment." in text


def test_individual_history_is_user_facing():
    text = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert '"When": row.get("created_at")' in text
    assert '"Question": row.get("question_text")' in text
    assert '"Response": row.get("answer_text")' in text
    assert '"Status": row.get("status")' in text


def test_dashboard_explains_score_vs_severity_colours():
    text = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert "Room colours show score bands" in text
    assert "independent of issue severity" in text
    assert "single-colour 100% pie is therefore expected" in text


def test_version_is_608():
    from professional_app.version import __version__
    assert __version__ == "6.0.8"
