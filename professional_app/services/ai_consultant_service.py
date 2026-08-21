from __future__ import annotations
import hashlib
import json
import io
import html
from typing import Any

from platform_core.database import connect, initialize_database, transaction
from platform_core import cloud_repository
from platform_core.openai_service import OPENAI
from assessment_core.record_compatibility import normalize_professional_result

INSTRUCTIONS = """
You are VastuAI's Professional AI Consultant for an individual buyer.
Use only the supplied saved assessment. Explain findings, recommendations,
scores and referenced VK/NUM Knowledge IDs. Never calculate or change scores,
invent rules, rooms, directions, remedies or property facts. Vastu and
Numerology are belief-based. Do not present answers as structural, legal,
financial, scientific, safety, valuation or investment advice.
When relevant, finish with a concise 'Knowledge used' line containing only
Knowledge IDs present in the snapshot.
""".strip()


def _context(payload: dict, stored_result: dict) -> dict:
    result = normalize_professional_result(stored_result)
    context = {
        "property": payload,
        "overall_professional": result.get("final_result", {}),
        "vastu": result.get("vastu_result", {}),
        "numerology": result.get("numerology_result", {}),
        "recommendations": result.get("recommendation_result", {}),
        "executive_summary": result.get("explanation", ""),
    }
    raw = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str).encode()
    context["source_hash"] = hashlib.sha256(raw).hexdigest()
    return context


def ask(project_id: int, analysis_id: int, payload: dict, result: dict, question: str) -> dict:
    if not question.strip():
        raise ValueError("Enter a question.")
    context = _context(payload, result)
    model = OPENAI.models.default_model
    try:
        answer = OPENAI.text_response(
            instructions=INSTRUCTIONS,
            input_text=(
                f"Question: {question.strip()}\n\n"
                + json.dumps(context, ensure_ascii=False, indent=2, default=str)
            ),
            model=model,
        ).strip()
        status, error = "Completed", ""
    except Exception as exc:
        answer, status, error = "", "Failed", str(exc)
    if cloud_repository.enabled():
        context_uuid = cloud_repository.cloud_analysis_uuid(int(analysis_id))
        if not context_uuid:
            raise RuntimeError("Cloud assessment context was not found for AI Consultant history.")
        history_id = cloud_repository.save_cloud_ai_exchange(
            context_type="property",
            context_id=context_uuid,
            mode="property",
            question=question.strip(),
            answer=answer,
            model_name=model,
            source_hash=context["source_hash"],
            status=status,
            error_text=error,
        )
    else:
        initialize_database()
        with transaction() as connection:
            cursor = connection.execute(
                """INSERT INTO professional_ai_consultant_history(
                   project_id,analysis_id,mode,model_name,source_hash,
                   question_text,answer_text,status,error_text)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    int(project_id), int(analysis_id), "property", model,
                    context["source_hash"], question.strip(), answer, status, error,
                ),
            )
            history_id = int(cursor.lastrowid)
    if error:
        raise RuntimeError(f"AI Consultant request failed. Audit record {history_id}: {error}")
    return {
        "history_id": history_id, "model_name": model,
        "source_hash": context["source_hash"], "answer": answer,
    }


def history(project_id: int, analysis_id: int) -> list[dict]:
    if cloud_repository.enabled():
        context_uuid = cloud_repository.cloud_analysis_uuid(int(analysis_id))
        if not context_uuid:
            return []
        return cloud_repository.list_cloud_ai_exchanges(
            context_type="property", context_id=context_uuid, limit=100
        )
    initialize_database()
    with connect() as connection:
        return [dict(row) for row in connection.execute(
            """SELECT id,model_name,question_text,answer_text,status,error_text,created_at
               FROM professional_ai_consultant_history
               WHERE project_id=? AND analysis_id=?
               ORDER BY id DESC LIMIT 100""",
            (int(project_id), int(analysis_id)),
        ).fetchall()]


def build_response_pdf(*, property_name: str, question: str, answer: str, model_name: str = "") -> bytes:
    """Create a compact client-friendly PDF of one AI Consultant response."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "VastuAITitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=24, textColor=colors.HexColor("#285943"), alignment=TA_LEFT,
    )
    heading = ParagraphStyle(
        "VastuAIHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11, leading=14, textColor=colors.HexColor("#285943"),
    )
    body = ParagraphStyle(
        "VastuAIBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.5, leading=14, textColor=colors.HexColor("#30443A"),
    )
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
        topMargin=18*mm, bottomMargin=18*mm,
        title=f"VastuAI AI Consultant - {property_name}", author="VastuAI",
    )
    story = [
        Paragraph("VastuAI AI Consultant", title),
        Paragraph(html.escape(property_name or "Property"), styles["Heading2"]),
        Spacer(1, 5*mm),
        Table(
            [["Question", Paragraph(html.escape(question), body)],
             ["Model", html.escape(model_name or "VastuAI AI Consultant")]],
            colWidths=[30*mm, 130*mm],
            style=TableStyle([
                ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#EAF2EE")),
                ("TEXTCOLOR",(0,0),(0,-1),colors.HexColor("#285943")),
                ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
                ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#B8D2C5")),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("PADDING",(0,0),(-1,-1),6),
            ])
        ),
        Spacer(1, 7*mm),
        Paragraph("Consultant response", heading),
        Spacer(1, 2*mm),
    ]
    for para in str(answer or "").split("\\n"):
        text = para.strip()
        if text:
            story.append(Paragraph(html.escape(text), body))
            story.append(Spacer(1, 2*mm))
    story += [
        Spacer(1, 5*mm),
        Paragraph(
            "Vastu and Numerology are belief-based guidance. This AI response does not replace structural, "
            "legal, financial, safety, valuation or investment due diligence.", body
        )
    ]
    doc.build(story)
    return buffer.getvalue()
