# VastuAI v6.0.3 — Supabase Connection Resilience

- Retries transient httpx/PostgREST transport failures such as RemoteProtocolError.
- Rebuilds the Supabase query on each retry; authentication and RLS remain unchanged.
- Prevents short-lived HTTP/2 connection termination events from immediately crashing cloud-backed Professional pages.
- No scoring, Vastu, Numerology, OpenAI, authentication, or data ownership logic changed.
