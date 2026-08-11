# VastuAI Platform v5.3.2 — Property Discovery Fix

- Professional Properties now reads saved rows directly from `professional_analyses`.
- Project metadata is joined only optionally (`LEFT JOIN`) and can no longer hide saved property assessments.
- Existing `project_id` is retained for opening each property and all downstream PDP / buyer / AI workflows.
- Property selector continues to use the complete saved-property collection, independent of search/sort filters.
