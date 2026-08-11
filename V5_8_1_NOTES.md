# VastuAI Platform v5.8.1 — Render Deployment Ready

Deployment-only release based on v5.8.0 Mobile PWA Beta.

Changes:
- Added Render Blueprint (`render.yaml`).
- Pinned Python to 3.13.14.
- Added native Tesseract dependency via `packages.txt`.
- Configured Streamlit for Render `$PORT` and `0.0.0.0` binding.
- Configured `VASTUAI_DATA_DIR=/var/data` with a 1 GB persistent disk.
- Added secure unsynchronised `OPENAI_API_KEY` Blueprint variable.
- Added deployment and custom-domain instructions for `app.vastuai.in`.

No scoring, Professional, Builder, AI Consultant, PWA, report, persistence schema, or navigation logic was changed.
