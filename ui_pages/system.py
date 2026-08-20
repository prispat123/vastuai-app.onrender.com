from __future__ import annotations
import pandas as pd
import streamlit as st
from platform_core.cache import ANALYSIS_CACHE, DOCUMENT_CACHE, VISION_CACHE
from platform_core.runtime import diagnostics

def render() -> None:
    st.header("Platform Services")
    data = diagnostics()
    openai = data.pop("openai")
    c1, c2, c3 = st.columns(3)
    c1.metric("Database", "Ready" if data["database_connection"] == "Ready" else "Error")
    c2.metric("Data directory", "Writable" if data["data_directory_writable"] else "Read-only")
    c3.metric("OpenAI", "Configured" if openai["configured"] else "Not configured")
    st.subheader("Runtime")
    st.dataframe(
        pd.DataFrame([{"Setting": k, "Value": v} for k, v in data.items()]),
        use_container_width=True,
        hide_index=True,
    )
    st.subheader("OpenAI configuration")
    st.json(openai)
    if not openai["env_file_exists"]:
        st.error(f"Root .env was not found at: {openai['env_path']}")
    elif not openai["configured"]:
        st.error(
            "The root .env exists, but OPENAI_API_KEY is blank or could not "
            "be parsed."
        )
    else:
        st.success("OpenAI API key is available to the running VastuAI service.")
    st.subheader("Shared cache")
    c1, c2, c3 = st.columns(3)
    if c1.button("Clear Vision Cache", use_container_width=True):
        st.success(f"Removed {VISION_CACHE.clear()} cached item(s).")
    if c2.button("Clear Analysis Cache", use_container_width=True):
        st.success(f"Removed {ANALYSIS_CACHE.clear()} cached item(s).")
    if c3.button("Clear Document Cache", use_container_width=True):
        st.success(f"Removed {DOCUMENT_CACHE.clear()} cached item(s).")
