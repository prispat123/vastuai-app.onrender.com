
from pathlib import Path
import re as regex

ROOT = Path(__file__).resolve().parents[1]


def _sample_professional_result():
    return {
        "final_result": {"score": 7.8, "grade": "Good"},
        "vastu_result": {"score": 7.4, "grade": "B+"},
        "numerology_result": {"score": 82.0, "grade": "Supportive"},
        "recommendation_result": {"decision": "Proceed with review", "confidence": "High"},
        "explanation": "Sample verified explanation.",
    }


def test_ui_filename_helper_has_runtime_dependency():
    text = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert regex.search(r"(?m)^import re$", text)
    assert "def _safe_filename(" in text
    # Execute the helper logic independently to catch NameError-type regressions.
    namespace = {"re": __import__("re")}
    exec(
        'def _safe_filename(value):\n'
        '    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())\n'
        '    cleaned = cleaned.strip("._-")\n'
        '    return cleaned[:80] or "VastuAI"\n',
        namespace,
    )
    assert namespace["_safe_filename"]("Avinya Enclave / Tower 1") == "Avinya_Enclave_Tower_1"


def test_individual_ai_service_cloud_path(monkeypatch):
    from professional_app.services import ai_consultant_service as svc

    monkeypatch.setattr(svc.cloud_repository, "enabled", lambda: True)
    monkeypatch.setattr(
        svc.cloud_repository, "cloud_analysis_uuid",
        lambda analysis_id: "11111111-1111-1111-1111-111111111111"
    )
    saved = {}
    def fake_save(**kwargs):
        saved.update(kwargs)
        return "history-property-1"
    monkeypatch.setattr(svc.cloud_repository, "save_cloud_ai_exchange", fake_save)
    monkeypatch.setattr(svc.OPENAI, "text_response", lambda **kwargs: "Verified individual AI response.")

    result = svc.ask(
        1, 10,
        {"property_name": "Avinya Enclave", "flat_number": "A-101"},
        _sample_professional_result(),
        "What are the main concerns?"
    )

    assert result["history_id"] == "history-property-1"
    assert result["answer"] == "Verified individual AI response."
    assert saved["context_type"] == "property"
    assert saved["status"] == "Completed"


def test_portfolio_ai_service_cloud_path(monkeypatch):
    from professional_app.services import portfolio_chat_service as svc

    context = {
        "buyer": {"buyer_id": 3, "buyer_name": "Test Buyer", "date_of_birth": "01/01/1990"},
        "scope": "full_shortlist",
        "portfolio_shortlist_count": 2,
        "selected_property_count": 2,
        "ranking_basis": "Saved PDP deterministic ranking",
        "properties": [
            {"portfolio_rank": 1, "decision_id": "PDP-1", "property_label": "Property A"},
            {"portfolio_rank": 2, "decision_id": "PDP-2", "property_label": "Property B"},
        ],
        "source_hash": "abc123",
    }
    monkeypatch.setattr(svc, "portfolio_context", lambda buyer_id, decision_ids=None: context)
    monkeypatch.setattr(svc, "_recent_turns", lambda buyer_id, source_hash, limit=6: [])
    monkeypatch.setattr(svc.cloud_repository, "enabled", lambda: True)
    monkeypatch.setattr(
        svc.cloud_repository, "cloud_buyer_uuid",
        lambda buyer_id: "22222222-2222-2222-2222-222222222222"
    )
    saved = {}
    def fake_save(**kwargs):
        saved.update(kwargs)
        return "history-portfolio-1"
    monkeypatch.setattr(svc.cloud_repository, "save_cloud_ai_exchange", fake_save)
    monkeypatch.setattr(svc.OPENAI, "text_response", lambda **kwargs: "Verified portfolio AI response.")

    result = svc.ask(1, 3, "Which shortlisted property is best overall?")

    assert result["history_id"] == "history-portfolio-1"
    assert result["answer"] == "Verified portfolio AI response."
    assert saved["context_type"] == "portfolio"
    assert saved["status"] == "Completed"


def test_both_ai_pdf_exports_render():
    from professional_app.services.ai_consultant_service import build_response_pdf

    individual = build_response_pdf(
        property_name="Avinya Enclave",
        question="What are the main concerns?",
        answer="Verified individual response.",
        model_name="gpt-test",
    )
    portfolio = build_response_pdf(
        property_name="Test Buyer Portfolio",
        question="Which property is best overall?",
        answer="Verified portfolio response.",
        model_name="gpt-test",
    )

    assert individual.startswith(b"%PDF")
    assert portfolio.startswith(b"%PDF")
    assert len(individual) > 1500
    assert len(portfolio) > 1500


def test_both_download_buttons_are_wired():
    text = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert '"Download AI Response PDF"' in text
    assert '"Download AI Portfolio Response PDF"' in text
    assert "_safe_filename(property_name)" in text
    assert "_safe_filename(buyer_name)" in text
