from __future__ import annotations
import hashlib
import json
from typing import Any

from platform_core.database import connect, initialize_database, transaction
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
    initialize_database()
    with connect() as connection:
        return [dict(row) for row in connection.execute(
            """SELECT id,model_name,question_text,answer_text,status,error_text,created_at
               FROM professional_ai_consultant_history
               WHERE project_id=? AND analysis_id=?
               ORDER BY id DESC LIMIT 100""",
            (int(project_id), int(analysis_id)),
        ).fetchall()]
