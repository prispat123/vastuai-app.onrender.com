from __future__ import annotations
import streamlit as st
from professional_app.ui import render_section as render_professional

def render(project, section: str | None = None) -> None:
    if project["workspace_type"] != "Professional":
        st.error("This page requires a Professional project.")
        return
    render_professional(int(project["id"]), requested_section=section)
