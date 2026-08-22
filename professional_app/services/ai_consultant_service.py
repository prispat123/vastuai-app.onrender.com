from __future__ import annotations
import hashlib
import json
import io
import html
import re
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
    """Create a screen-style, client-facing PDF of an AI Consultant response."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    SAGE = colors.HexColor("#5F8F76")
    DARK = colors.HexColor("#2F5D46")
    TEXT = colors.HexColor("#30443A")
    MUTED = colors.HexColor("#6F8178")
    BORDER = colors.HexColor("#C9DDD2")
    PALE = colors.HexColor("#EEF7F1")
    PALE_2 = colors.HexColor("#F7FBF8")
    AMBER = colors.HexColor("#FBF3DE")

    title = ParagraphStyle(
        "VastuAITitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=20, leading=24, textColor=DARK, alignment=TA_LEFT, spaceAfter=2*mm,
    )
    subtitle = ParagraphStyle(
        "VastuAISubtitle", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=13.5, leading=17, textColor=TEXT, spaceAfter=1*mm,
    )
    section = ParagraphStyle(
        "VastuAISection", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=11.5, leading=14.5, textColor=DARK, spaceAfter=0,
    )
    card_heading = ParagraphStyle(
        "VastuAICardHeading", parent=styles["BodyText"], fontName="Helvetica-Bold",
        fontSize=10.2, leading=13, textColor=DARK, spaceAfter=0,
    )
    body = ParagraphStyle(
        "VastuAIBody", parent=styles["BodyText"], fontName="Helvetica",
        fontSize=9.5, leading=14, textColor=TEXT, spaceAfter=1.6*mm,
    )
    bullet = ParagraphStyle(
        "VastuAIBullet", parent=body, leftIndent=5*mm, firstLineIndent=-3.2*mm,
        bulletIndent=1.5*mm, spaceAfter=1.2*mm,
    )
    detail = ParagraphStyle(
        "VastuAIDetail", parent=body,
        leftIndent=14*mm,
        rightIndent=4*mm,
        firstLineIndent=0,
        spaceAfter=1.4*mm,
    )
    small = ParagraphStyle(
        "VastuAISmall", parent=body, fontSize=7.5, leading=9.6, spaceAfter=0,
    )

    def normalize_text(value: str) -> str:
        t = str(value or "")
        for old, new in {
            "\u2010":"-", "\u2011":"-", "\u2012":"-", "\u2013":"-",
            "\u2014":"-", "\u2212":"-", "\u00a0":" ", "\u200b":"",
        }.items():
            t = t.replace(old, new)
        return t

    def clean_inline(value: str, *, bold_labels: bool = True) -> str:
        t = normalize_text(value).strip()
        t = re.sub(r"`(.+?)`", r"\1", t)
        t = html.escape(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        if bold_labels:
            t = re.sub(
                r"^(Use|Why|Note|Option A|Option B|Best overall|Recorded concern|Trade-offs versus runners-up|Knowledge used)\s*:",
                r"<b>\1:</b>", t, flags=re.I,
            )
        return t

    def is_separator(line: str) -> bool:
        cells = [c.strip() for c in normalize_text(line).strip().strip("|").split("|")]
        return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells)

    def looks_like_section_heading(lines, idx: int) -> bool:
        line = normalize_text(lines[idx]).strip()
        if not line or line.startswith(("-", "*", "|", "#")):
            return False
        if len(line) > 72 or line.endswith((".", ":", ";", "?", "!")):
            return False
        if idx + 1 >= len(lines):
            return False
        nxt = normalize_text(lines[idx + 1]).strip()
        return nxt.startswith(("-", "*")) or "|" in nxt

    def looks_like_topic_bullet(value: str) -> bool:
        t = normalize_text(value).strip()
        return (
            len(t) <= 72
            and not re.match(r"^(Use|Why|Note|Option A|Option B)\s*:", t, re.I)
            and (("(" in t and ")" in t) or ":" not in t)
        )

    def section_band(value: str):
        return Table(
            [[Paragraph(clean_inline(value, bold_labels=False), section)]],
            colWidths=[178*mm],
            style=TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),PALE),
                ("BOX",(0,0),(-1,-1),0.6,BORDER),
                ("LEFTPADDING",(0,0),(-1,-1),7),
                ("RIGHTPADDING",(0,0),(-1,-1),7),
                ("TOPPADDING",(0,0),(-1,-1),6),
                ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ]),
        )

    def topic_card(topic: str, details: list[str]):
        rows = [[Paragraph(clean_inline(topic), card_heading)]]
        rows.extend([[Paragraph(clean_inline(d), detail)] for d in details])
        return Table(
            rows, colWidths=[174*mm], hAlign="LEFT",
            style=TableStyle([
                ("BACKGROUND",(0,0),(-1,0),PALE),
                ("BACKGROUND",(0,1),(-1,-1),PALE_2),
                ("BOX",(0,0),(-1,-1),0.45,BORDER),
                ("LINEBELOW",(0,0),(-1,0),0.35,BORDER),
                ("LEFTPADDING",(0,0),(-1,-1),7),
                ("RIGHTPADDING",(0,0),(-1,-1),7),
                ("TOPPADDING",(0,0),(-1,-1),5),
                ("BOTTOMPADDING",(0,0),(-1,-1),5),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
            ]),
        )

    def add_markdown(flow, markdown: str) -> None:
        lines = normalize_text(markdown).replace("\\n", "\n").splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            if "|" in line and i + 1 < len(lines) and is_separator(lines[i + 1]):
                raw_rows = [line]
                i += 2
                while i < len(lines) and "|" in lines[i] and lines[i].strip():
                    raw_rows.append(lines[i].strip())
                    i += 1
                rows = [[Paragraph(clean_inline(c), small) for c in r.strip().strip("|").split("|")] for r in raw_rows]
                cols = max(len(r) for r in rows)
                for row in rows:
                    row.extend([Paragraph("", small)] * (cols - len(row)))
                table = Table(rows, colWidths=[178*mm/cols]*cols, repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("BACKGROUND",(0,0),(-1,0),SAGE),
                    ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                    ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE_2]),
                    ("GRID",(0,0),(-1,-1),0.35,BORDER),
                    ("VALIGN",(0,0),(-1,-1),"TOP"),
                    ("LEFTPADDING",(0,0),(-1,-1),3),
                    ("RIGHTPADDING",(0,0),(-1,-1),3),
                    ("TOPPADDING",(0,0),(-1,-1),4),
                    ("BOTTOMPADDING",(0,0),(-1,-1),4),
                ]))
                flow.extend([table, Spacer(1,4*mm)])
                continue

            if line.startswith(("### ","## ","# ")):
                flow.extend([section_band(line.lstrip("# ")),Spacer(1,2.5*mm)])
                i += 1
                continue

            if looks_like_section_heading(lines, i):
                flow.extend([section_band(line),Spacer(1,2.5*mm)])
                i += 1
                continue

            if re.match(r"^[-*]\s+", line):
                topic = re.sub(r"^[-*]\s+","",line).strip()
                if looks_like_topic_bullet(topic):
                    details = []
                    j = i + 1
                    while j < len(lines):
                        m = re.match(r"^[-*]\s+(.+)", lines[j].strip())
                        if not m:
                            break
                        d = m.group(1).strip()
                        if re.match(r"^(Use|Why|Note|Option A|Option B)\s*:", d, re.I):
                            details.append(d)
                            j += 1
                        else:
                            break
                    if details:
                        flow.extend([topic_card(topic,details),Spacer(1,2.5*mm)])
                        i = j
                        continue
                flow.append(Paragraph(clean_inline(topic), bullet, bulletText="•"))
                i += 1
                continue

            flow.append(Paragraph(clean_inline(line), body))
            i += 1

    def page_decor(canvas, doc):
        canvas.saveState()
        width, _ = A4
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(16*mm,12*mm,width-16*mm,12*mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica",7)
        canvas.drawString(16*mm,7.5*mm,"VastuAI - AI Consultant")
        canvas.drawRightString(width-16*mm,7.5*mm,f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer,pagesize=A4,leftMargin=16*mm,rightMargin=16*mm,
        topMargin=16*mm,bottomMargin=18*mm,
        title=f"VastuAI AI Consultant - {property_name}",author="VastuAI",
    )

    question_card = Table(
        [
            [Paragraph("Your question",card_heading)],
            [Paragraph(clean_inline(question),body)],
        ],
        colWidths=[178*mm],
        style=TableStyle([
            ("BACKGROUND",(0,0),(-1,0),SAGE),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("BACKGROUND",(0,1),(-1,1),PALE_2),
            ("BOX",(0,0),(-1,-1),0.55,BORDER),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("RIGHTPADDING",(0,0),(-1,-1),8),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]),
    )

    story = [
        Paragraph("VastuAI AI Consultant",title),
        Paragraph(clean_inline(property_name or "Property"),subtitle),
        Spacer(1,3*mm),
        question_card,
        Spacer(1,6*mm),
        section_band("Consultant response"),
        Spacer(1,3*mm),
    ]
    add_markdown(story,answer)

    story.extend([
        Spacer(1,4*mm),
        Table(
            [[Paragraph(
                "<b>Important note</b><br/>Vastu and Numerology are belief-based guidance. "
                "This AI response does not replace structural, legal, financial, safety, valuation or investment due diligence.",
                small,
            )]],
            colWidths=[178*mm],
            style=TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),AMBER),
                ("BOX",(0,0),(-1,-1),0.45,colors.HexColor("#E3D5A6")),
                ("LEFTPADDING",(0,0),(-1,-1),7),
                ("RIGHTPADDING",(0,0),(-1,-1),7),
                ("TOPPADDING",(0,0),(-1,-1),6),
                ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ]),
        ),
    ])
    doc.build(story,onFirstPage=page_decor,onLaterPages=page_decor)
    return buffer.getvalue()
