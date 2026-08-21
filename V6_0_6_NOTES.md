# VastuAI v6.0.6 — PDF Helper + Header Visibility Fix

- Defines the missing `_safe_filename()` helper used by both AI PDF download buttons.
- Fixes `NameError: _safe_filename is not defined` in AI Consultant and AI Portfolio Consultant.
- Adds safe cross-platform PDF filenames.
- Increases top content spacing so the page header/context chips are fully visible under Streamlit's top bar.
- Applies the spacing fix on desktop and mobile.
