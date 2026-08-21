# VastuAI v6.0.7 — Both AI Screens Regression Fix

- Fixes the deployed `NameError: name 're' is not defined` in `_safe_filename()`.
- Runs service-level cloud-path tests for both AI Consultant and AI Portfolio Consultant.
- Renders and validates PDF bytes for both individual and portfolio AI responses.
- Verifies both Streamlit download buttons are wired to safe filenames.
- Keeps v6.0.6 header-spacing correction.
