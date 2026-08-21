# VastuAI v6.0.5 - AI History + PDF Export Fix

- Fixes AI Portfolio Consultant `FOREIGN KEY constraint failed` by storing cloud-mode portfolio conversation history in Supabase `ai_conversations` instead of temporary SQLite.
- Stores individual AI Consultant conversation history in Supabase in cloud mode as well.
- Adds `Download AI Response PDF` to the individual AI Consultant response.
- Adds `Download AI Portfolio Response PDF` to the AI Portfolio Consultant response.
- Keeps local SQLite history as the fallback for non-cloud/portable mode.
- No assessment score, Vastu, Numerology, ranking or RLS logic changed.
