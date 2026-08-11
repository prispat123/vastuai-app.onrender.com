from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from platform_core.database import connect, initialize_database, transaction
from project_intelligence import gpt_context_service


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
VALID_EFFORTS = ["minimal", "low", "medium", "high"]
VALID_STYLES = [
    "Professional",
    "Consultant",
    "Builder Executive",
    "Buyer Friendly",
]


SYSTEM_INSTRUCTIONS = """
You are the optional explanation and Q&A layer for VastuAI.
The supplied JSON snapshot is the only factual source. Never invent or alter rooms, directions, scores, rules or recommendations.

Use four evidence labels correctly:
1. Verified observation: saved reviewed directions, scores, grades, confidence, tower, flat and Professional findings.
2. Stored Knowledge: a rule under stored_knowledge for that layout.
3. Applicable Knowledge: a deterministic local rule under applicable_knowledge matched from reviewed directions. Never call it stored unless it is under stored_knowledge.
4. Comparison: a room-by-room difference from verified directions or room_comparison_matrix.

For comparisons, identify shared features and meaningful differences. Explain each difference with applicable rule ID, polarity and severity. Use wording such as favourable differentiator, area of concern, consistent with, or may contribute. Never claim one room alone caused the final score. Mention Unknown rooms as limitations.

Prefer concrete wording such as: Flat 2 has an East balcony with applicable rule VK-057 marked positive, whereas Flat 1 has a West balcony with applicable rule VK-061 marked neutral.
Do not say no Knowledge inputs are available when applicable_knowledge contains matches.

Structure substantial comparisons as: Verified comparison; Stored Knowledge; Applicable Knowledge interpretation; Practical conclusion; Data limitations.
Vastu is belief-based and is not structural, legal, financial, medical, engineering or safety advice. Do not infer absent data. Do not recalculate scores.
""".strip()


def _ensure_tables() -> None:
    initialize_database()
    with transaction() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO gpt_settings(
                id,enabled,model_name,reasoning_effort,
                narrative_style,include_in_reports
            ) VALUES(1,1,?,?,?,0)
            """,
            (DEFAULT_MODEL, "low", "Professional"),
        )


def api_key_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def get_settings() -> dict[str, Any]:
    _ensure_tables()
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM gpt_settings WHERE id=1"
        ).fetchone()
    return dict(row)


def save_settings(
    *,
    enabled: bool,
    model_name: str,
    reasoning_effort: str,
    narrative_style: str,
    include_in_reports: bool,
) -> None:
    if reasoning_effort not in VALID_EFFORTS:
        raise ValueError("Invalid reasoning effort.")
    if narrative_style not in VALID_STYLES:
        raise ValueError("Invalid narrative style.")
    _ensure_tables()
    with transaction() as connection:
        connection.execute(
            """
            UPDATE gpt_settings SET
                enabled=?,
                model_name=?,
                reasoning_effort=?,
                narrative_style=?,
                include_in_reports=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=1
            """,
            (
                int(enabled),
                model_name.strip() or DEFAULT_MODEL,
                reasoning_effort,
                narrative_style,
                int(include_in_reports),
            ),
        )


def _client() -> OpenAI:
    if not api_key_configured():
        raise RuntimeError(
            "OPENAI_API_KEY is not configured. Core analysis and reports remain available without GPT."
        )
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _prompt(
    generation_type: str,
    context: dict,
    *,
    question: str = "",
    style: str,
) -> str:
    tasks = {
        "flat_explanation": (
            "Explain this individual flat assessment. Cover the main reasons "
            "for the stored score, strongest features, priority concerns and "
            "practical next steps. Do not change the score."
        ),
        "why_score": (
            "Answer: Why did this flat receive its stored score? Link each "
            "reason to the supplied directions, Professional findings and "
            "Knowledge rule IDs. Distinguish positive and negative factors."
        ),
        "tower_summary": (
            "Write an executive tower summary using only finalised layouts. "
            "Cover performance, strongest flats, lowest flats, recurring "
            "concerns, common Knowledge rules and prioritised actions."
        ),
        "building_summary": (
            "Write an executive building summary. Cover coverage, whether the "
            "building score is provisional, tower comparison, strongest and "
            "lowest layouts, recurring concerns and prioritised actions."
        ),
        "project_qa": (
            "Answer using only the snapshot. For comparisons use the room comparison matrix and contrast stored Knowledge with applicable Knowledge. Cite flat numbers, towers, scores and rule IDs. Explain positive, negative and neutral differences and say when data is unavailable."
        ),
    }
    if generation_type not in tasks:
        raise ValueError("Unsupported GPT generation type.")

    return (
        f"Narrative style: {style}\n\n"
        f"Task: {tasks[generation_type]}\n\n"
        + (f"User question: {question}\n\n" if question else "")
        + "Verified local snapshot:\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )


def _save_generation(
    *,
    project_id: int,
    layout_id: int | None,
    tower_name: str,
    generation_type: str,
    model_name: str,
    source_hash: str,
    source_snapshot: dict,
    prompt_text: str,
    output_text: str,
    status: str,
    error_text: str = "",
) -> int:
    _ensure_tables()
    with transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO gpt_generations(
                project_id,layout_id,tower_name,generation_type,
                model_name,source_hash,source_snapshot_json,prompt_text,
                output_text,status,error_text
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                int(project_id),
                int(layout_id) if layout_id is not None else None,
                tower_name,
                generation_type,
                model_name,
                source_hash,
                json.dumps(source_snapshot, ensure_ascii=False),
                prompt_text,
                output_text,
                status,
                error_text,
            ),
        )
        return int(cursor.lastrowid)


def generate_project_answer(*, project_id: int, question: str) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("Enter a question.")
    settings = get_settings()
    if not bool(settings["enabled"]):
        raise RuntimeError("AI Consultant is disabled in settings.")
    context = gpt_context_service.project_qa_context(project_id)
    model_name = settings["model_name"]
    prompt_text = _prompt(
        "project_qa",
        context,
        question=question.strip(),
        style=settings["narrative_style"],
    )
    try:
        response = _client().responses.create(
            model=model_name,
            instructions=SYSTEM_INSTRUCTIONS,
            input=prompt_text,
            reasoning={"effort": settings["reasoning_effort"]},
            store=False,
        )
        output_text = (response.output_text or "").strip()
        if not output_text:
            raise RuntimeError("The GPT response was empty.")
    except Exception as exc:
        generation_id = _save_generation(
            project_id=project_id,
            layout_id=None,
            tower_name="",
            generation_type="project_qa",
            model_name=model_name,
            source_hash=context["source_hash"],
            source_snapshot=context,
            prompt_text=prompt_text,
            output_text="",
            status="Failed",
            error_text=str(exc),
        )
        raise RuntimeError(f"AI Consultant request failed. Audit record {generation_id}: {exc}") from exc
    generation_id = _save_generation(
        project_id=project_id,
        layout_id=None,
        tower_name="",
        generation_type="project_qa",
        model_name=model_name,
        source_hash=context["source_hash"],
        source_snapshot=context,
        prompt_text=prompt_text,
        output_text=output_text,
        status="Completed",
    )
    return {
        "generation_id": generation_id,
        "generation_type": "project_qa",
        "model_name": model_name,
        "source_hash": context["source_hash"],
        "question": question.strip(),
        "output_text": output_text,
    }


def generate(*, project_id: int, generation_type: str = "project_qa", layout_id: int | None = None, tower_name: str = "", question: str = "") -> dict[str, Any]:
    if generation_type != "project_qa":
        raise ValueError(
            "AI Consultant supports project Q&A only. Use Analysis & Review or Dashboard & Reports for structured flat, tower and building reports, then ask the AI Consultant for explanations or comparisons."
        )
    return generate_project_answer(project_id=project_id, question=question)

def latest_generation(
    *,
    project_id: int,
    generation_type: str,
    layout_id: int | None = None,
    tower_name: str = "",
) -> dict | None:
    _ensure_tables()
    clauses = [
        "project_id=?",
        "generation_type=?",
        "status='Completed'",
    ]
    params: list[Any] = [int(project_id), generation_type]

    if layout_id is not None:
        clauses.append("layout_id=?")
        params.append(int(layout_id))
    else:
        clauses.append("layout_id IS NULL")

    clauses.append("tower_name=?")
    params.append(tower_name)

    with connect() as connection:
        row = connection.execute(
            f"""
            SELECT * FROM gpt_generations
            WHERE {' AND '.join(clauses)}
            ORDER BY id DESC LIMIT 1
            """,
            tuple(params),
        ).fetchone()
    return dict(row) if row else None


def history(project_id: int, limit: int = 100):
    _ensure_tables()
    with connect() as connection:
        return connection.execute(
            """
            SELECT id,generation_type,layout_id,tower_name,model_name,
                   status,error_text,created_at
            FROM gpt_generations
            WHERE project_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(project_id), int(limit)),
        ).fetchall()
