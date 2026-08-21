# VastuAI v6.0.4 - Professional Cloud Completion

- Professional Numerology side menu now reads the authenticated user's permanent Supabase assessments.
- Cloud PDPs use stable per-user numeric compatibility IDs, eliminating UUID -> int crashes.
- Buyer Workspace is cloud-backed: buyers are created from PDP identity, shortlist rows are permanent, and ordering/removal is persisted in Supabase.
- AI Portfolio Consultant can use the cloud-backed Buyer Workspace/shortlist without relying on temporary SQLite shortlist data.
- Individual AI Consultant now includes a Download AI Response PDF button.
- Authentication and Supabase Row Level Security remain the ownership boundary.
