# VastuAI v6.0.1 — Professional Cloud Persistence

## Permanent Professional source of truth
When a Supabase-authenticated user is signed in:
- Professional assessments are created, listed, loaded, updated and deleted in Supabase PostgreSQL.
- Every query is user-scoped and is also protected by Supabase Row Level Security.
- Stable per-user numeric `legacy_analysis_id` values preserve compatibility with the existing Streamlit UI.
- Canonical Property Decision Profiles are persisted in Supabase with the source assessment.

## OpenAI hosted configuration
The runtime now prefers server environment variables. A local `.env` only fills missing values and can no longer overwrite Render environment variables.

## Transitional scope
- Professional assessment + PDP persistence: cloud.
- Buyer Workspace/shortlists/AI conversation persistence: schema exists, application migration follows next.
- Builder persistence: still on the compatibility SQLite layer and will be migrated separately.
