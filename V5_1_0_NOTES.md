# VastuAI Platform v5.1.0 — Conversational Portfolio Consultant

## Added
- Conversational portfolio Q&A inside the existing Portfolio Consultant page.
- Buyer-scoped portfolio snapshot generated from the deterministic v5.0 ranking service.
- Multi-turn context from recent completed portfolio conversations.
- Audit history stored per buyer with model, source hash, question, answer and status.
- Starter prompts for best choice, top-two comparison and Vastu-risk comparison.

## Guardrails
- Saved PDP scores remain immutable and are never recalculated by the chat layer.
- The deterministic Portfolio Consultant ranking remains the source of truth.
- The AI is instructed not to invent property facts, Vastu/Numerology rules, remedies, prices or investment claims.
- Missing facts must be identified as unavailable in the saved PDPs.
- Vastu and Numerology are explicitly treated as belief-based decision support.
