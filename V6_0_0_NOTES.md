# VastuAI v6.0.0 — Authentication + Cloud Foundation

## Added
- Supabase email/password sign-up, sign-in and sign-out.
- Authenticated user UUID stored in Streamlit session state.
- Login gate before Professional/Builder workspace access.
- Permanent PostgreSQL cloud repository module for user-scoped Professional records.
- Supabase publishable-key configuration through environment variables.
- Existing deterministic Vastu, Numerology, LangGraph, report and AI logic retained.

## Database
The Supabase project contains `profiles`, `projects`, `professional_analyses`,
`property_decision_profiles`, `buyers`, `buyer_shortlists` and `ai_conversations`.
RLS is enabled so authenticated users can access only their own rows.

## Important migration status
v6.0.0 establishes authentication and the cloud repository boundary.
The existing SQLite services are retained temporarily for compatibility while
Professional persistence is migrated service-by-service in v6.0.1. Do not
remove the local database yet.

## Render environment
Set:
- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY
- OPENAI_API_KEY
