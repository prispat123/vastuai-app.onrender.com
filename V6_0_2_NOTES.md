# VastuAI v6.0.2 — Professional Cloud Integration Fix

## Fixed
- Professional Properties landing page now reads Supabase for authenticated users instead of SQLite.
- Opening a permanent cloud property no longer depends on an old ephemeral SQLite project ID.
- Saved Portfolio, Reports and AI Consultant continue through the cloud-backed history service.
- Re-login now rediscovers the signed-in user's permanent Professional records from Supabase.
- OpenAI diagnostics now report whether the running Render process can actually see OPENAI_API_KEY; local .env is not required.

## Confirmed before release
The Supabase Professional table already contained records created through v6.0.1. The issue was read-path integration, not data loss.
