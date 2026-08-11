# Migration Roadmap

## v3.1 — Stable shell
Shared configuration, project store, navigation and persistence.

## v3.2 — Shared services
Logging, storage abstraction, cache and OpenAI client.

## v3.3 — Professional migration
Move the proven Professional pages into native platform modules.

## v3.4 — Builder migration
Move document processing and apartment inventory into native platform modules.

## v3.5 — Shared vision and Vastu engine
One analysis implementation used by both workspaces.

## v3.6 — Shared reports and legacy import
Professional and Builder templates plus import of prior project folders.

## v5.0.0 — Portfolio Consultant
- Compare a buyer's shortlisted immutable Property Decision Profiles across projects.
- Rank by saved Overall Professional Score; use critical/high count, Vastu and Numerology only as deterministic tie-breakers.
- Surface Best Overall, Best Vastu Fit and Best Numerology Fit.
- Explain strengths, concerns and shortlist trade-offs without recalculating assessment scores.
- Preserve Buyer Workspace shortlist ordering and persistence as an independent workflow.

### Next
- v5.1.x: conversational Portfolio Consultant grounded only in shortlisted PDPs.
- Later: AI Buying Advisor and Decision Pack.

## v5.1.0 — Conversational Portfolio Consultant
- Buyer-scoped conversational Q&A across shortlisted PDPs.
- Deterministic v5.0 portfolio ranking remains the source of truth.
- Recent conversation turns provide follow-up context without changing scores.
- Each generation stores model, shortlist snapshot hash, question, answer and status for auditability.
