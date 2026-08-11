# VastuAI Platform v5.8.2 — Free Render Beta

## Purpose
Provide a no-paid-disk Render deployment for HTTPS/PWA beta testing.

## Changes
- Render Blueprint web-service plan is `free`.
- Removed persistent Render disk requirement.
- Cloud data directory changed to `/tmp/vastuai-data`.
- Updated deployment documentation to clearly warn that cloud SQLite/uploads are ephemeral and may be lost on spin-down, restart, or redeploy.
- Application, scoring, Professional, Builder, reports, AI, LangGraph, and PWA behavior are otherwise unchanged from v5.8.1.
