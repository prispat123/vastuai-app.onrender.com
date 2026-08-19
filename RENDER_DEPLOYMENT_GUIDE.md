# VastuAI v5.8.2 — Free Render Beta Deployment Guide

This package is configured for a free, single-instance VastuAI beta deployment on Render in the Singapore region.

## What changed from v5.8.1

- Render service plan changed from `starter` to `free`.
- The paid persistent `disk:` block was removed.
- `VASTUAI_DATA_DIR` now points to `/tmp/vastuai-data`.
- No payment method should be required merely to create this free web-service instance, subject to Render account/workspace rules.

## Important beta limitation

Render Free web services use an ephemeral filesystem. Properties, buyers, uploaded plans, SQLite data, and other files created on the cloud instance can disappear whenever the service spins down, restarts, or redeploys. Do not use this build for durable production data.

Use v5.8.2 only to validate:
- HTTPS access without the desktop PC running
- Android responsive behavior
- PWA installation / Add to Home Screen
- Professional and Builder UI flows
- AI Consultant connectivity
- report-generation behavior during an active test session

## Step 1 — Replace the GitHub repository contents

Push the CONTENTS of this folder to the existing GitHub repository root. `render.yaml`, `app.py`, and `requirements.txt` must remain at the repository root.

Do not commit `.env`, API keys, local databases, or local data folders.

## Step 2 — Create the Render Blueprint

1. In Render, choose **New > Blueprint**.
2. Connect the GitHub repository containing this package.
3. Render reads `render.yaml`.
4. Confirm the service instance type is **Free**.
5. When prompted for `OPENAI_API_KEY`, enter it as a secret.
6. Apply/Create the Blueprint.

Expected configuration:
- Service: `vastuai-app`
- Region: Singapore
- Runtime: Python 3.13.14
- Plan: Free
- No persistent disk
- Temporary data directory: `/tmp/vastuai-data`

After deployment, Render supplies an HTTPS URL similar to:

`https://vastuai-app.onrender.com`

The first request after an idle period can take noticeably longer because a Free Render service spins down when idle.

## Step 3 — Validate the hosted beta

Open the Render HTTPS URL and test:
1. Home / workspace selection
2. Professional property creation and assessment
3. Results and reports
4. AI Consultant
5. Buyer Workspace / AI Portfolio Consultant
6. Builder flows and AI Consultant

Do not rely on saved cloud test data surviving a restart or idle spin-down.

## Step 4 — Add app.vastuai.in

After the `onrender.com` URL works:
1. Render > VastuAI service > Settings > Custom Domains.
2. Add `app.vastuai.in`.
3. Render shows the DNS target required for the domain.
4. At the DNS provider for `vastuai.in`, create the CNAME record exactly as Render specifies.
5. Return to Render and verify the domain.
6. Render provisions HTTPS/TLS for the custom domain.

## Step 5 — Android PWA test

Once the HTTPS URL loads:
1. Open it in Chrome on Android.
2. Use **Install app** / **Add to Home screen** when offered.
3. Launch VastuAI from the home-screen icon.
4. Confirm it works while the Windows desktop is switched off.

## Next architecture step

Before broader external testing or production use, move persistent application data away from local SQLite/ephemeral files to durable cloud storage with authentication and per-user isolation.


## v6.0.0 Supabase authentication

Add these Render environment variables before deploying v6.0.0:

- `SUPABASE_URL` = `https://dovbtkmxqtczinxmqrub.supabase.co`
- `SUPABASE_PUBLISHABLE_KEY` = the project's publishable key from Supabase
- `OPENAI_API_KEY` = your existing server-side OpenAI key

The publishable Supabase key is intended for application clients and is constrained
by Row Level Security. Never put a Supabase secret/service-role key in the client UI
or source repository.
