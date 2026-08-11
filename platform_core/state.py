from __future__ import annotations
import streamlit as st

DEFAULTS = {
    "page": "Home",
    "workspace": None,
    "active_project_id": None,
    "project_section": "Overview",
    "requested_project_section": None,
    "navigation_notice": None,
    "pending_project_section": None,
}

def initialize_state() -> None:
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

def navigate(page: str, *, workspace=None, project_id=None) -> None:
    st.session_state.page = page
    if workspace is not None:
        st.session_state.workspace = workspace
    if project_id is not None:
        st.session_state.active_project_id = project_id
    st.rerun()

def clear_project() -> None:
    st.session_state.active_project_id = None
    st.session_state.project_section = "Overview"
