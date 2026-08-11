from __future__ import annotations

import hashlib
import json
from typing import Any

from platform_core.database import connect, initialize_database, transaction
from platform_core.openai_service import OPENAI
from professional_app.services import portfolio_consultant_service

INSTRUCTIONS = """
You are VastuAI's Conversational Portfolio Consultant for one buyer.
Answer only from the supplied buyer portfolio snapshot and prior conversation turns.
The snapshot contains immutable saved Property Decision Profiles (PDPs) and a deterministic
portfolio ranking. Never recalculate, change, estimate or invent scores, rules, rooms,
directions, remedies, property facts, prices, legal facts or investment returns.

When comparing properties, identify them by their supplied PDP decision IDs. Start with a compact
markdown comparison table using only fields present in the supplied snapshot, then explain the
reasoning and trade-offs. Respect the deterministic ranking/order already present in the snapshot;
do not create a different scoring formula or recalculate any score. If the snapshot is scoped to
two selected properties, compare only those two properties and do not introduce other shortlisted
properties. If the user asks for information that is not present in the snapshot, say that it is
not available in the saved PDPs. If asked which property to choose, explain the strongest option
within the supplied scope and its recorded concerns rather than presenting the answer as a
guaranteed buying outcome.

Vastu and Numerology are belief-based. Do not present the response as structural, legal,
financial, scientific, safety, valuation or investment advice. Keep answers practical and
concise. Mention the relevant PDP decision IDs in comparison answers.
""".strip()


def _safe_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "portfolio_rank": row.get("portfolio_rank"),
        "decision_id": row.get("decision_id"),
        "project_name": row.get("project_name"),
        "property_label": row.get("property_label"),
        "overall_score": row.get("overall_score"),
        "vastu_score": row.get("vastu_score"),
        "numerology_score_100": row.get("numerology_score_100"),
        "critical_high_count": row.get("critical_high_count", 0),
        "pdp_decision": row.get("recommendation"),
        "strengths": list(row.get("strengths") or []),
        "concerns": list(row.get("concerns") or []),
        "tradeoff": row.get("tradeoff"),
    }


def portfolio_context(buyer_id: int, decision_ids: list[str] | None = None) -> dict[str, Any]:
    portfolio = portfolio_consultant_service.analyse_shortlist(int(buyer_id))
    if not portfolio.get("ranked"):
        raise ValueError("The selected buyer has no shortlisted properties.")

    ranked = list(portfolio["ranked"])
    selected_ids = [str(value) for value in (decision_ids or []) if str(value).strip()]
    if selected_ids:
        wanted = set(selected_ids)
        selected = [row for row in ranked if str(row.get("decision_id")) in wanted]
        if len(selected) != len(wanted):
            raise ValueError("One or more selected properties are not in this buyer's shortlist.")
        ranked = selected

    buyer = portfolio["buyer"]
    scope = "selected_properties" if selected_ids else "full_shortlist"
    context = {
        "buyer": {
            "buyer_id": int(buyer["id"]),
            "buyer_name": buyer.get("buyer_name", ""),
            "date_of_birth": buyer.get("date_of_birth", ""),
        },
        "scope": scope,
        "portfolio_shortlist_count": portfolio["shortlist_count"],
        "selected_property_count": len(ranked),
        "ranking_basis": portfolio["ranking_basis"],
        "properties": [_safe_row(row) for row in ranked],
    }
    if not selected_ids:
        context.update({
            "consultant_recommendation": portfolio["recommendation"],
            "best_overall_decision_id": portfolio["best_overall"].get("decision_id"),
            "best_vastu_decision_id": portfolio["best_vastu"].get("decision_id"),
            "best_numerology_decision_id": portfolio["best_numerology"].get("decision_id"),
        })
    elif ranked:
        context["strongest_selected_decision_id"] = ranked[0].get("decision_id")

    raw = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    context["source_hash"] = hashlib.sha256(raw).hexdigest()
    return context

def history(buyer_id: int, limit: int = 100) -> list[dict[str, Any]]:
    initialize_database()
    with connect() as connection:
        return [
            dict(row)
            for row in connection.execute(
                """SELECT id,buyer_id,model_name,source_hash,question_text,answer_text,
                          status,error_text,created_at
                   FROM portfolio_ai_consultant_history
                   WHERE buyer_id=?
                   ORDER BY id DESC LIMIT ?""",
                (int(buyer_id), int(limit)),
            ).fetchall()
        ]


def _recent_turns(buyer_id: int, source_hash: str, limit: int = 6) -> list[dict[str, str]]:
    rows = [
        row for row in reversed(history(int(buyer_id), limit=100))
        if row.get("source_hash") == source_hash
    ][-limit:]
    turns: list[dict[str, str]] = []
    for row in rows:
        if row.get("status") != "Completed" or not row.get("answer_text"):
            continue
        turns.append({
            "question": str(row.get("question_text") or ""),
            "answer": str(row.get("answer_text") or ""),
        })
    return turns


def ask(
    project_id: int,
    buyer_id: int,
    question: str,
    *,
    decision_ids: list[str] | None = None,
) -> dict[str, Any]:
    question = str(question or "").strip()
    if not question:
        raise ValueError("Enter a portfolio question.")

    context = portfolio_context(int(buyer_id), decision_ids=decision_ids)
    prior_turns = _recent_turns(int(buyer_id), context["source_hash"])
    model = OPENAI.models.default_model
    prompt = {
        "question": question,
        "portfolio_snapshot": context,
        "recent_conversation": prior_turns,
    }

    try:
        answer = OPENAI.text_response(
            instructions=INSTRUCTIONS,
            input_text=json.dumps(prompt, ensure_ascii=False, indent=2, default=str),
            model=model,
        ).strip()
        status, error = "Completed", ""
    except Exception as exc:
        answer, status, error = "", "Failed", str(exc)

    initialize_database()
    with transaction() as connection:
        cursor = connection.execute(
            """INSERT INTO portfolio_ai_consultant_history(
               project_id,buyer_id,model_name,source_hash,question_text,answer_text,status,error_text)
               VALUES(?,?,?,?,?,?,?,?)""",
            (
                int(project_id), int(buyer_id), model, context["source_hash"],
                question, answer, status, error,
            ),
        )
        history_id = int(cursor.lastrowid)

    if error:
        raise RuntimeError(
            f"Portfolio Consultant request failed. Audit record {history_id}: {error}"
        )

    return {
        "history_id": history_id,
        "model_name": model,
        "source_hash": context["source_hash"],
        "answer": answer,
    }
