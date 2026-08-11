# VastuAI v5.7.1 — Mobile Navigation Fix

- Fixes Streamlit session-state collision when opening a Professional property after the `project_section` navigation widget has been instantiated.
- Property opening and Add Property now queue the target section through `pending_project_section`; `app.py` applies it before sidebar widgets are created on the next rerun.
- Project creation uses the same safe navigation pattern.
- Retains all v5.7.0 mobile-responsive behavior.
