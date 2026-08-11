# VastuAI v5.8.1 — Render Deployment Guide

This package is prepared for a single-instance VastuAI beta deployment on Render in the Singapore region.

## Why this configuration

- Streamlit is bound to `0.0.0.0` and Render's `$PORT`.
- Python is pinned to 3.13.14 to match the tested local runtime.
- `VASTUAI_DATA_DIR=/var/data` is backed by a 1 GB persistent Render disk.
- `OPENAI_API_KEY` is entered as a Render secret during initial Blueprint deployment and is not committed to Git.
- `packages.txt` installs the native Tesseract OCR package for floor-plan OCR support.
- The service is configured as `starter` because Render persistent disks require a paid web-service instance.

## Step 1 — Push this folder to GitHub

Create a new GitHub repository, for example `vastuai-platform`, and push the CONTENTS of this folder to the repository root. `render.yaml` must be at the repository root.

Do not commit `.env`, API keys, local databases, or local data folders.

## Step 2 — Create the Render service

1. Sign in to Render.
2. Choose **New > Blueprint**.
3. Connect the GitHub repository containing this package.
4. Render will detect `render.yaml`.
5. When prompted for `OPENAI_API_KEY`, paste the key into Render's secret field.
6. Create/apply the Blueprint.

The Blueprint requests:
- Web service: `vastuai-app`
- Region: Singapore
- Runtime: Python 3.13.14
- Plan: Starter
- Persistent disk: 1 GB mounted at `/var/data`

After deployment, Render supplies an HTTPS URL similar to:

`https://vastuai-app.onrender.com`

Open that URL first and validate Professional, Builder, AI Consultant, report download, and PWA behavior.

## Step 3 — Add app.vastuai.in

After the `onrender.com` URL works:

1. Render > VastuAI service > Settings > Custom Domains.
2. Add `app.vastuai.in`.
3. Render will show the DNS target required for the domain.
4. At the DNS provider for `vastuai.in`, create the CNAME record exactly as Render specifies.
5. Return to Render and click Verify.
6. Render provisions TLS automatically and redirects HTTP to HTTPS.

Do not change the root `vastuai.in` domain unless you intentionally want it to host the application too. `app.vastuai.in` leaves the root domain free for a future marketing/public website.

## Step 4 — Android PWA test

Once `https://app.vastuai.in` loads:

1. Open it in Chrome on Android.
2. Use Chrome's **Install app** / **Add to Home screen** action if offered.
3. Launch VastuAI from the home-screen icon.
4. Verify that it opens in standalone mode and connects without the desktop PC running.

## Existing local data

The cloud service starts with a new persistent data directory. Existing Windows SQLite/property data is NOT automatically uploaded. For a beta with shared test data, migrate the current VastuAI data into `/var/data` after the service is live. Do this only after taking a backup of the local data.

For multiple independent external testers, the next architecture step should be user authentication plus per-user data isolation (preferably a managed relational database) rather than having all testers share one SQLite database.
