from __future__ import annotations

import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf(project_name: str, result: dict) -> bytes:
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Professional Numerology Report - {project_name}",
        author="VastuAI",
    )
    numbers = result["calculated_numbers"]
    inputs = result["inputs"]
    story = [
        Paragraph("Professional Numerology Assessment", styles["Title"]),
        Paragraph(project_name, styles["Heading2"]),
        Spacer(1, 8 * mm),
        Table(
            [
                ["Intended user", inputs["intended_user_name"]],
                ["Date of birth", inputs["date_of_birth"]],
                ["Property identifier", inputs["property_identifier"]],
                ["Property name", inputs["property_name"] or "—"],
                ["Birth Number", numbers["birth_number"]],
                ["Life Path Number", numbers["life_path_number"]],
                ["Property Number", numbers["property_number"]],
                ["Numerology Score", f'{result["numerology_score"]:.1f}/100'],
                ["Grade", result["grade"]],
                ["Knowledge version", result["knowledge_version"]],
            ],
            colWidths=[55 * mm, 105 * mm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ECEFF1")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        ),
        Spacer(1, 7 * mm),
        Paragraph("Number Interpretations", styles["Heading2"]),
    ]
    for item in result["number_objects"]:
        story.append(Paragraph(f'<b>{item["title"]}</b>', styles["BodyText"]))
        story.append(Paragraph(item["summary"], styles["BodyText"]))
        story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Alignment Findings", styles["Heading2"]))
    for item in result["alignment_objects"]:
        story.append(Paragraph(f'<b>{item["title"]}</b>', styles["BodyText"]))
        story.append(Paragraph(item["summary"], styles["BodyText"]))
        if item.get("recommendation"):
            story.append(
                Paragraph(
                    f'<b>Guidance:</b> {item["recommendation"]}',
                    styles["BodyText"],
                )
            )
        story.append(Spacer(1, 3 * mm))

    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph(result["disclaimer"], styles["BodyText"]),
            Paragraph(
                "The Numerology assessment is independent of the Vastu "
                "assessment. The two scores must not be averaged or directly "
                "compared.",
                styles["BodyText"],
            ),
        ]
    )
    document.build(story)
    return buffer.getvalue()
