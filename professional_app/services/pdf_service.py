from __future__ import annotations

from assessment_core.record_compatibility import normalize_professional_result

import io
from datetime import datetime
from typing import Any

from assessment_core import build_snapshot

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm

from professional_app.services.chart_service import build_direction_wheel_png, build_room_scores_png, direction_balance
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _safe(value: Any, default: str = "N/A") -> str:
    return str(value) if value not in (None, "") else default


def build_pdf(payload: dict[str, Any], result: dict[str, Any]) -> bytes:
    result = normalize_professional_result(result)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#285943")))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#285943"), spaceBefore=10, spaceAfter=7))
    styles.add(ParagraphStyle(name="SmallMuted", parent=styles["BodyText"], fontSize=8, textColor=colors.grey))

    final = result.get("final_result", {})
    vastu = result.get("vastu_result", {})
    numerology = result.get("numerology_result", {})
    assessment_snapshot = build_snapshot(
        payload=payload,
        professional_result=result,
    )
    vastu_knowledge = assessment_snapshot["vastu"]["knowledge"]
    numerology_knowledge = assessment_snapshot["numerology"]["knowledge_result"]
    recommendation = result.get("recommendation_result", {})
    details = vastu.get("details", [])
    story = [
        Paragraph("VastuAI Professional Property Report", styles["TitleCenter"]),
        Spacer(1, 5*mm),
        Paragraph(f"Generated {datetime.now().strftime('%d %B %Y, %H:%M')}", styles["SmallMuted"]),
        Spacer(1, 8*mm),
    ]

    summary = [
        ["Property", _safe(payload.get("property_name"), "Unnamed property")],
        ["Apartment / property number", _safe(payload.get("flat_number"), "Not provided")],
        ["Owner", _safe(payload.get("owner_name"), "Not provided")],
        ["Overall Professional Score", f'{final.get("score", 0)}/10'],
        ["Overall rating", _safe(final.get("rating"), "Not rated")],
        ["Vastu score", f'{vastu.get("score")}/10' if vastu.get("score") is not None else "Not assessed"],
        ["Vastu grade", _safe(vastu.get("grade"), "Not assessed")],
        ["Numerology score", (
            f'{numerology.get("score_100")}/100'
            if numerology.get("score_100") is not None
            else "Not assessed"
        )],
        ["Numerology grade", _safe(
            numerology.get("grade"),
            "Not assessed",
        )],
        ["Decision", _safe(recommendation.get("decision"))],
        ["Confidence", _safe(recommendation.get("confidence"))],
    ]
    table = Table(summary, colWidths=[48*mm, 110*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#EAF2EE")),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#B8C8C0")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))
    story += [
        table,
        Spacer(1, 3*mm),
        Paragraph(_safe(final.get("footnote"), ""), styles["SmallMuted"]),
        Spacer(1, 5*mm),
        Paragraph("Executive summary", styles["Section"]),
        Paragraph(_safe(result.get("explanation"), "No explanation available."), styles["BodyText"]),
    ]

    if details:
        story += [PageBreak(), Paragraph("Visual assessment dashboard", styles["Section"])]
        story.append(Paragraph("The directional wheel summarises average room scores by compass sector. Directions with no assessed rooms are shown at zero and should not be interpreted as defects.", styles["SmallMuted"]))
        story.append(Spacer(1, 3*mm))
        direction_image = Image(io.BytesIO(build_direction_wheel_png(details)), width=145*mm, height=126*mm)
        direction_image.hAlign = "CENTER"
        story.append(direction_image)
        story.append(Spacer(1, 3*mm))
        balance_rows = [["Direction", "Average score", "Rooms assessed"]]
        for row in direction_balance(details):
            balance_rows.append([row["direction"], f'{row["average_score"]:g}/10', str(row["room_count"])])
        bt = Table(balance_rows, repeatRows=1, colWidths=[58*mm, 45*mm, 45*mm])
        bt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#285943")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("PADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(bt)
        story += [PageBreak(), Paragraph("Room-wise score profile", styles["Section"])]
        room_height = min(155*mm, max(78*mm, (45 + len(details) * 7) * mm))
        room_image = Image(io.BytesIO(build_room_scores_png(details)), width=165*mm, height=room_height)
        room_image.hAlign = "CENTER"
        story.append(room_image)
        story.append(Paragraph("Scores are presented on a 0-10 scale. Review the detailed findings and remedies before drawing conclusions from the chart alone.", styles["SmallMuted"]))

    story += [PageBreak(), Paragraph("Vastu assessment", styles["Section"])]
    if details:
        rows = [["Knowledge ID", "Area", "Direction", "Score", "Severity", "Finding"]]
        for item in details:
            matching = [
                finding for finding in vastu_knowledge.get("findings", [])
                if finding.get("field") == item.get("field")
            ]
            knowledge_ids = ", ".join(
                finding.get("rule_id", "") for finding in matching
            ) or "—"
            rows.append([
                knowledge_ids, _safe(item.get("area")),
                _safe(item.get("direction")),
                f"{_safe(item.get('score'), '0')}/10",
                _safe(item.get("severity")),
                Paragraph(_safe(item.get("rationale"), ""), styles["BodyText"])
            ])
        vt = Table(rows, repeatRows=1, colWidths=[25*mm, 25*mm, 20*mm, 16*mm, 20*mm, 56*mm])
        vt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#285943")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("PADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(vt)
    else:
        story.append(Paragraph("Vastu was not assessed.", styles["BodyText"]))

    story += [PageBreak(), Paragraph("Numerology assessment", styles["Section"])]
    if numerology_knowledge:
        numbers = numerology_knowledge.get("calculated_numbers", {})
        nrows = [
            ["Metric", "Value"],
            ["Birth Number", _safe(numbers.get("birth_number"))],
            ["Life Path Number", _safe(numbers.get("life_path_number"))],
            ["Property Number", _safe(numbers.get("property_number"))],
            ["Numerology score", f'{numerology_knowledge.get("numerology_score", 0)}/100'],
            ["Grade", _safe(numerology_knowledge.get("grade"))],
            ["Knowledge version", _safe(numerology_knowledge.get("knowledge_version"))],
        ]
        nt = Table(nrows, colWidths=[60*mm, 90*mm])
        nt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#285943")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .3, colors.grey), ("PADDING", (0,0), (-1,-1), 5)]))
        story.append(nt)
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("Numerology Knowledge IDs", styles["Section"]))
        id_rows = [["Knowledge ID", "Domain", "Finding"]]
        for item in numerology_knowledge.get("number_objects", []) + numerology_knowledge.get("alignment_objects", []):
            id_rows.append([
                item.get("object_id", "—"),
                item.get("domain", "—"),
                Paragraph(item.get("title", ""), styles["BodyText"]),
            ])
        nit = Table(id_rows, repeatRows=1, colWidths=[48*mm, 38*mm, 76*mm])
        nit.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#285943")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), .3, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("PADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(nit)
    else:
        story.append(Paragraph("Numerology was not assessed. Add a property number and valid date of birth in Property Details.", styles["BodyText"]))

    story += [Spacer(1, 5*mm), Paragraph(
        _safe(final.get("footnote"), ""),
        styles["SmallMuted"],
    )]

    story += [Paragraph("Prioritised recommendations", styles["Section"])]
    actions = recommendation.get("actions", [])
    if actions:
        for idx, action in enumerate(actions, 1):
            story.append(Paragraph(f"<b>{idx}. {_safe(action.get('priority'))}: {_safe(action.get('area'))}</b>", styles["BodyText"]))
            story.append(Paragraph(f"Finding: {_safe(action.get('finding'), '')}", styles["BodyText"]))
            story.append(Paragraph(f"Practical action: {_safe(action.get('practical_action'), '')}", styles["BodyText"]))
            story.append(Spacer(1, 3*mm))
    else:
        story.append(Paragraph("No priority actions were generated.", styles["BodyText"]))

    story += [Spacer(1, 8*mm), Paragraph("Disclaimer", styles["Section"]), Paragraph("This report provides belief-based Vastu and numerology guidance. It is not structural, legal, financial, scientific, safety, valuation or investment advice. Engage qualified professionals before making property decisions or structural alterations.", styles["SmallMuted"])]
    doc.build(story)
    return buffer.getvalue()


def build_comparison_pdf(rows: list[dict[str, Any]]) -> bytes:
    """Build a portfolio comparison report containing only the supplied records."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm,
        topMargin=14*mm, bottomMargin=14*mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ComparisonTitle", parent=styles["Title"], alignment=TA_CENTER,
        textColor=colors.HexColor("#285943"),
    ))
    styles.add(ParagraphStyle(
        name="ComparisonSmall", parent=styles["BodyText"], fontSize=8,
        textColor=colors.grey,
    ))
    story = [
        Paragraph("VastuAI Selected Property Comparison", styles["ComparisonTitle"]),
        Spacer(1, 3*mm),
        Paragraph(
            f"Generated {datetime.now().strftime('%d %B %Y, %H:%M')} · {len(rows)} selected records",
            styles["ComparisonSmall"],
        ),
        Spacer(1, 7*mm),
    ]
    ordered = sorted(rows, key=lambda row: float(row.get("overall_score") or 0), reverse=True)
    table_rows = [["Rank", "Key", "Property", "Apartment", "Overall Professional", "Vastu", "Numerology", "Confidence"]]
    for rank, row in enumerate(ordered, 1):
        table_rows.append([
            str(rank), f"P{row.get('id')}", _safe(row.get("property_label"), "Unnamed"),
            _safe(row.get("flat_number"), "Not provided"),
            _safe(row.get("overall_score"), "0"), _safe(row.get("vastu_score"), "N/A"),
            _safe(row.get("numerology_score"), "N/A"), _safe(row.get("confidence"), "N/A"),
        ])
    table = Table(table_rows, repeatRows=1, colWidths=[12*mm, 14*mm, 42*mm, 28*mm, 18*mm, 18*mm, 22*mm, 25*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#285943")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 7.5),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(table)
    story += [Spacer(1, 7*mm), Paragraph("Selected-record notes", styles["Heading2"])]
    for rank, row in enumerate(ordered, 1):
        name = _safe(row.get("property_label"), "Unnamed property")
        apartment = _safe(row.get("flat_number"), "Not provided")
        story.append(Paragraph(
            f"<b>{rank}. P{row.get('id')} — {name} ({apartment})</b>: "
            f"overall {_safe(row.get('overall_score'), '0')}/10; "
            f"Vastu {_safe(row.get('vastu_score'), 'N/A')}; "
            f"numerology {_safe(row.get('numerology_score'), 'N/A')}; "
            f"confidence {_safe(row.get('confidence'), 'N/A')}.",
            styles["BodyText"],
        ))
        story.append(Spacer(1, 2*mm))
    story += [Spacer(1, 5*mm), Paragraph(
        "Overall Professional Score gives equal importance to Vastu and Numerology (50% each) when both are available. The underlying assessments remain independent. This comparison is belief-based guidance and must be considered alongside structural, legal, financial and location due diligence.",
        styles["ComparisonSmall"],
    )]
    doc.build(story)
    return buffer.getvalue()
