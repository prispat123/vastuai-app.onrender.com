from __future__ import annotations

import streamlit as st

from platform_core import __version__, projects as project_store
from platform_core.database import initialize_database
from platform_core.state import initialize_state, navigate
from pwa_support import install_pwa_metadata
from ui_pages import home, projects, project_detail, system

st.set_page_config(
    page_title="VastuAI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="auto",
)

install_pwa_metadata()

initialize_database()
initialize_state()

st.markdown(
    """
    <style>
    :root {
      --vai-radius:16px;
      --vai-sage:#78B58F; --vai-sage-dark:#527C63; --vai-sage-deep:#365F48;
      --vai-mint:#EEF8F1; --vai-mint-2:#E2F2E7; --vai-mint-3:#D7ECDD;
      --vai-cream:#FFF9EC; --vai-amber:#F4D99B; --vai-peach:#FCE9DE;
      --vai-coral:#E9A38F; --vai-red:#D9827A; --vai-ink:#30443A;
      --vai-muted:#65796D; --vai-border:#D6E8DB; --vai-surface:#FBFEFC;
      --vai-page-title:1.72rem; --vai-section-title:1.30rem; --vai-subtitle:1.04rem;
      --vai-body:.94rem; --vai-label:.86rem; --vai-caption:.78rem; --vai-metric:1.22rem;
    }
    html, body, [class*="css"] {font-size:16px;}
    .block-container {max-width:1480px;padding-top:1rem;padding-bottom:3rem;}
    .stApp {background:linear-gradient(180deg,#FCFEFC 0%,#F3FAF5 100%);color:var(--vai-ink);}
    .stApp p, .stApp li, .stApp span, .stApp div[data-testid="stMarkdownContainer"] p {font-size:var(--vai-body);line-height:1.48;}
    .stApp h1 {font-size:var(--vai-page-title)!important;line-height:1.18!important;letter-spacing:-.025em!important;color:var(--vai-sage-deep)!important;font-weight:700!important;}
    .stApp h2 {font-size:var(--vai-section-title)!important;line-height:1.22!important;letter-spacing:-.015em!important;color:var(--vai-sage-deep)!important;font-weight:700!important;}
    .stApp h3 {font-size:var(--vai-subtitle)!important;line-height:1.28!important;color:#416953!important;font-weight:700!important;}
    .stApp h4 {font-size:.96rem!important;line-height:1.3!important;color:#416953!important;font-weight:700!important;}
    .stCaption, div[data-testid="stCaptionContainer"], div[data-testid="stCaptionContainer"] p {font-size:var(--vai-caption)!important;color:var(--vai-muted)!important;line-height:1.4!important;}
    label, div[data-testid="stWidgetLabel"] p {font-size:var(--vai-label)!important;font-weight:600!important;color:#486154!important;}

    section[data-testid="stSidebar"] {border-right:1px solid var(--vai-border);background:linear-gradient(180deg,#EAF6ED 0%,#F8FCF9 100%);}
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span {font-size:.86rem!important;line-height:1.4!important;}
    section[data-testid="stSidebar"] h1 {font-size:1.28rem!important;letter-spacing:-.02em!important;}
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {font-size:1rem!important;}

    div[data-testid="stMetric"] {padding:.78rem .88rem!important;border:1px solid #CFE3D5;border-radius:14px!important;background:linear-gradient(135deg,#F1FAF4 0%,#FBFEFC 100%);box-shadow:0 1px 4px rgba(53,95,72,.04);}
    div[data-testid="stMetricLabel"] p {font-size:.72rem!important;line-height:1.05!important;text-transform:uppercase;letter-spacing:.045em;color:#60776A!important;}
    div[data-testid="stMetricValue"] {font-size:var(--vai-metric)!important;line-height:1.12!important;overflow-wrap:anywhere;color:var(--vai-sage-deep)!important;font-weight:700!important;}
    div[data-testid="stMetricDelta"] {font-size:.70rem!important;}

    div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {border-radius:11px;min-height:2.55rem;font-size:.88rem!important;font-weight:650;border-color:#B9D8C3;background:#F7FCF8;color:#365F48;}
    div[data-testid="stButton"] button:hover, div[data-testid="stDownloadButton"] button:hover {border-color:#8FC4A1;background:#EDF8F0;color:#2F5941;}
    div[data-testid="stButton"] button[kind="primary"] {background:var(--vai-sage)!important;border-color:var(--vai-sage)!important;color:white!important;}
    div[data-testid="stButton"] button[kind="primary"]:hover {background:#699F7D!important;border-color:#699F7D!important;}

    div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {background:#FCFEFC!important;border-color:#CFE3D5!important;font-size:.90rem!important;}
    div[data-testid="stSelectbox"] > div > div, div[data-testid="stMultiSelect"] > div > div {background:#FCFEFC!important;border-color:#CFE3D5!important;font-size:.90rem!important;}
    div[data-testid="stSelectbox"] > div > div, div[data-testid="stTextInput"] > div > div {border-radius:11px;}

    .stTabs [data-baseweb="tab-list"] {gap:.35rem;border-bottom:1px solid #D8E9DD;}
    .stTabs [data-baseweb="tab"] {background:#EEF8F1;border-radius:10px 10px 0 0;color:#486154;font-size:.86rem!important;}
    .stTabs [aria-selected="true"] {background:#DCEFE2!important;color:#315C43!important;font-weight:700!important;}
    div[data-testid="stDataFrame"] {border:1px solid #D8E9DD;border-radius:14px;overflow:hidden;background:#FCFEFC;}
    div[data-testid="stExpander"] {border:1px solid #D8E9DD!important;border-radius:13px!important;background:#FBFEFC!important;}
    div[data-testid="stAlert"] {border-radius:13px!important;font-size:.88rem!important;}
    div[data-testid="stAlert"] p {font-size:.88rem!important;}

    .vai-context {display:flex;gap:.55rem;align-items:center;flex-wrap:wrap;margin:.1rem 0 .9rem;}
    .vai-chip {padding:.38rem .65rem;border:1px solid #CFE3D5;border-radius:999px;font-size:.78rem!important;background:#F4FAF6;color:#486154;}
    .vai-chip strong{color:#315C43;}
    .vai-builder-banner {padding:.85rem 1rem;border:1px solid #CFE3D5;border-radius:15px;background:linear-gradient(135deg,#EDF8F0 0%,#FFF9EC 100%);margin:.1rem 0 1rem;color:#365F48;}
    .vai-builder-banner strong{font-size:.90rem;}
    .vai-status-good{background:#DDF3E5;color:#315C43;border:1px solid #BFDCC8;}
    .vai-status-medium{background:#FFF2CD;color:#745C23;border:1px solid #EEDCA2;}
    .vai-status-caution{background:#FCE9DE;color:#8A5747;border:1px solid #EEC5B7;}
    .vai-status-critical{background:#F8DDDA;color:#8B413C;border:1px solid #E7B3AE;}

    /* v5.7.1 mobile-responsive design system */
    @media (max-width: 768px) {
      :root {
        --vai-page-title:1.42rem; --vai-section-title:1.16rem; --vai-subtitle:1rem;
        --vai-body:.91rem; --vai-label:.84rem; --vai-caption:.76rem; --vai-metric:1.12rem;
      }
      .block-container {padding:.65rem .72rem 2rem!important;max-width:100%!important;}
      header[data-testid="stHeader"] {background:rgba(252,254,252,.94)!important;}
      section[data-testid="stSidebar"] {width:min(88vw,320px)!important;}
      section[data-testid="stSidebar"] > div {width:100%!important;}

      /* Streamlit columns should become a vertical mobile flow. */
      div[data-testid="stHorizontalBlock"] {flex-direction:column!important;gap:.58rem!important;}
      div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width:100%!important;min-width:100%!important;flex:1 1 100%!important;
      }

      div[data-testid="stMetric"] {padding:.62rem .72rem!important;}
      div[data-testid="stButton"], div[data-testid="stDownloadButton"] {width:100%!important;}
      div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {
        width:100%!important;min-height:2.7rem!important;white-space:normal!important;
      }
      div[data-testid="stFormSubmitButton"] button {width:100%!important;min-height:2.7rem!important;}

      /* Inputs and uploads remain touch-friendly. */
      input, textarea, [data-baseweb="select"] > div {font-size:16px!important;}
      div[data-testid="stFileUploader"] section {padding:.7rem!important;}
      div[data-testid="stFileUploaderDropzone"] {min-height:86px!important;}

      /* Tabs remain usable without compressing labels. */
      .stTabs [data-baseweb="tab-list"] {overflow-x:auto!important;flex-wrap:nowrap!important;scrollbar-width:thin;}
      .stTabs [data-baseweb="tab"] {flex:0 0 auto!important;white-space:nowrap!important;padding:.48rem .7rem!important;}

      /* Dataframes/tables may scroll horizontally instead of crushing columns. */
      div[data-testid="stDataFrame"], div[data-testid="stTable"] {overflow-x:auto!important;max-width:100%!important;}
      div[data-testid="stDataFrame"] > div {min-width:620px;}

      /* Keep charts/images inside the viewport. */
      div[data-testid="stPlotlyChart"], div[data-testid="stPyplot"], div[data-testid="stImage"] {max-width:100%!important;overflow-x:auto!important;}
      div[data-testid="stImage"] img {max-width:100%!important;height:auto!important;}

      .vai-context {gap:.35rem;margin-bottom:.65rem;}
      .vai-chip {font-size:.72rem!important;padding:.31rem .5rem;}
      .vai-builder-banner {padding:.7rem .75rem;margin-bottom:.7rem;}
      .hero {padding:.88rem .9rem!important;border-radius:14px!important;}
      .consult-card {padding:.82rem .85rem!important;}
      .step-card {min-height:0!important;}
    }

    @media (max-width: 420px) {
      .block-container {padding-left:.55rem!important;padding-right:.55rem!important;}
      div[data-testid="stDataFrame"] > div {min-width:560px;}
      .vai-chip {max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pending_section = st.session_state.pop("pending_project_section", None)
if pending_section:
    st.session_state.project_section = pending_section
    st.session_state.page = "Project"

active_project = None
if st.session_state.active_project_id:
    active_project = project_store.get_project(
        int(st.session_state.active_project_id)
    )
    if active_project is None:
        st.session_state.active_project_id = None
        st.session_state.project_section = "Overview"

with st.sidebar:
    st.title("🧭 VastuAI Platform")
    st.caption(f"Version {__version__}")

    if st.button("🏠 Home", use_container_width=True, key="nav_home"):
        st.session_state.workspace = None
        st.session_state.active_project_id = None
        st.session_state.project_section = "Overview"
        navigate("Home")

    if st.button("⚙ Platform Services", use_container_width=True, key="nav_system"):
        navigate("System")

    if st.session_state.workspace in {"Professional", "Builder"}:
        nav_label = "🏡 Properties" if st.session_state.workspace == "Professional" else "📂 Projects"
        if st.button(nav_label, use_container_width=True, key="nav_projects"):
            navigate("Projects")

        def open_project_details() -> None:
            if active_project is None:
                st.session_state.requested_project_section = "Project Details"
                st.session_state.navigation_notice = (
                    "Select or create a project to open Project Details."
                )
                st.session_state.page = "Projects"
            else:
                st.session_state.project_section = (
                    "Project Details"
                    if active_project["workspace_type"] == "Builder"
                    else "Overview"
                )
                st.session_state.page = "Project"

        if st.session_state.workspace == "Builder":
            st.button(
                "📋 Project Details",
                use_container_width=True,
                key="nav_project_detail",
                on_click=open_project_details,
            )

        if active_project is not None:
            st.divider()
            if st.session_state.workspace == "Professional":
                st.markdown("**Current Property**")
                st.caption(st.session_state.get("selected_property_label") or "Assessment workspace")
            else:
                st.markdown("**Current Project**")
                st.caption(active_project["name"])

            sections = (
                project_detail.PROFESSIONAL_SECTIONS
                if active_project["workspace_type"] == "Professional"
                else project_detail.BUILDER_SECTIONS
            )

            def open_project_section() -> None:
                st.session_state.page = "Project"

            st.radio(
                "Project navigation",
                sections,
                key="project_section",
                label_visibility="collapsed",
                on_change=open_project_section,
            )

        st.divider()
        st.write(f"**Workspace:** {st.session_state.workspace}")
        if active_project is not None:
            if st.session_state.workspace == "Professional":
                st.write(f"**Property:** {st.session_state.get('selected_property_label') or 'Assessment workspace'}")
            else:
                st.write(f"**Project:** {active_project['name']}")
                st.caption(f"Status: {active_project['status']}")
    else:
        st.info("Choose Professional or Builder from Home.")

# Persistent compact context bar on every page.
if st.session_state.workspace in {"Professional", "Builder"}:
    project_name = active_project["name"] if active_project is not None else "Not selected"
    if st.session_state.workspace == "Professional":
        context_name = st.session_state.get("selected_property_label") or "No property selected"
        record = (f"P{st.session_state.get('selected_property_id')}"
                  if st.session_state.get("selected_property_id") else "New assessment")
        st.markdown(
            f'<div class="vai-context"><span class="vai-chip"><strong>Professional</strong></span>'
            f'<span class="vai-chip">Property · <strong>{context_name}</strong></span>'
            f'<span class="vai-chip">{record}</span><span class="vai-chip">v{__version__}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        status = active_project["status"] if active_project is not None else "—"
        st.markdown(
            f'<div class="vai-context"><span class="vai-chip"><strong>Builder</strong></span>'
            f'<span class="vai-chip">Project · <strong>{project_name}</strong></span>'
            f'<span class="vai-chip">{status}</span><span class="vai-chip">v{__version__}</span></div>',
            unsafe_allow_html=True,
        )
else:
    st.caption(f"VastuAI Platform v{__version__}")

PAGES = {
    "Home": home.render,
    "Projects": projects.render,
    "Project": project_detail.render,
    "System": system.render,
}

PAGES.get(st.session_state.page, home.render)()
