from __future__ import annotations
import streamlit as st
from platform_core.state import navigate
from platform_core.config import CONFIG
from platform_core.runtime import diagnostics

def render() -> None:
    st.markdown(
        """
        <div style="padding:1.15rem 1.2rem;border:1px solid #D5E8DB;border-radius:18px;
                    background:linear-gradient(135deg,#EEF8F1 0%,#FFF9EC 100%);margin-bottom:1rem">
          <div style="font-size:2rem;font-weight:700;color:#30443A">🧭 VastuAI Platform</div>
          <div style="margin-top:.3rem;color:#5B6F63">Choose the workspace that matches the assessment you want to perform.</div>
        </div>
        """, unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### 🏡 VastuAI Professional")
            st.write(
                "Assess individual properties, create buyer shortlists, use AI consultation, "
                "numerology and client-ready reporting."
            )
            if st.button(
                "Open Professional",
                type="primary",
                use_container_width=True,
                key="open_professional",
            ):
                navigate("Projects", workspace="Professional")

    with right:
        with st.container(border=True):
            st.markdown("### 🏗️ VastuAI Builder")
            st.write(
                "Manage builder developments, document inventory, apartments, "
                "bulk analysis and consolidated project reports."
            )
            if st.button(
                "Open Builder",
                type="primary",
                use_container_width=True,
                key="open_builder",
            ):
                navigate("Projects", workspace="Builder")

    st.divider()
    st.subheader("Runtime status")
    health = diagnostics()
    c1, c2, c3 = st.columns(3)
    c1.metric("Data repository", "Ready" if health["data_directory_writable"] else "Read-only")
    c2.metric("Database", health["database_connection"])
    c3.metric("OpenAI key", "Configured" if health["openai"]["configured"] else "Not configured")
    st.caption(f"Data directory: {CONFIG.data_dir}")
