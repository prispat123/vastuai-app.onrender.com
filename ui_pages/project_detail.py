from __future__ import annotations

import streamlit as st

from platform_core import projects
from platform_core.state import navigate
from ui_pages import professional_workspace, project_intelligence, professional_numerology

PROFESSIONAL_SECTIONS = [
    "Overview",
    "Property Details",
    "Layout Review",
    "Vastu Analysis",
    "Numerology",
    "Report",
    "Decision Profiles",
    "Buyer Workspace",
    "AI Portfolio Consultant",
    "AI Consultant",
    "Settings",
]

BUILDER_SECTIONS = [
    "Project Setup",
    "Documents & Layout Selection",
    "Layouts",
    "Analysis & Review",
    "Dashboard & Reports",
    "Knowledge Base",
    "AI Consultant",
]
def _render_overview(project) -> None:
    health = projects.project_health(project)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Project folder", "Ready" if health["folder_exists"] else "Missing")
    c2.metric("Metadata", "Ready" if health["metadata_exists"] else "Missing")
    c3.metric("Uploads", "Ready" if health["uploads_folder"] else "Missing")
    c4.metric("Analysis", "Ready" if health["analysis_folder"] else "Missing")

    st.write(f"**Client / Builder:** {project['client_or_builder'] or '—'}")
    st.write(f"**City:** {project['city'] or '—'}")
    st.write(f"**Status:** {project['status']}")
    st.write(f"**Description:** {project['description'] or '—'}")
    st.write(f"**Created:** {project['created_at']}")
    st.write(f"**Updated:** {project['updated_at']}")
    st.code(project["project_folder"])

    if project["workspace_type"] == "Professional":
        def open_professional_workspace() -> None:
            # project_section belongs to the sidebar radio widget.
            # Widget-owned state must be changed inside a callback.
            st.session_state.project_section = "Vastu Analysis"
            st.session_state.page = "Project"

        st.button(
            "Open Professional Assessment Workspace",
            type="primary",
            use_container_width=True,
            on_click=open_professional_workspace,
        )

def _render_settings(project) -> None:
    workspace = project["workspace_type"]
    with st.form(f"edit_project_{project['id']}"):
        name = st.text_input("Project name", project["name"])
        label = "Client name" if workspace == "Professional" else "Builder name"
        party = st.text_input(label, project["client_or_builder"] or "")
        city = st.text_input("City", project["city"] or "")
        description = st.text_area("Description", project["description"] or "")
        statuses = ["Active", "On Hold", "Completed", "Archived"]
        current = project["status"] if project["status"] in statuses else "Active"
        status = st.selectbox("Status", statuses, index=statuses.index(current))
        save = st.form_submit_button("Save Changes", type="primary")
    if save:
        projects.update_project(
            int(project["id"]),
            name=name,
            client_or_builder=party,
            city=city,
            description=description,
            status=status,
        )
        st.success("Project updated.")
        st.rerun()

def _render_placeholder(section: str, workspace: str) -> None:
    st.subheader(section)
    if workspace == "Professional":
        descriptions = {
            "Property Details": "Client and property information will be migrated here.",
            "Layout Review": "Layout image, North, entrance and room correction tools will be migrated here.",
            "Vastu Analysis": "The proven Professional analysis engine will be connected here.",
            "Numerology": "Professional numerology inputs and results will be connected here.",
            "Report": "The Professional client-report workflow will be connected here.",
        }
    else:
        descriptions = {
            "Documents": "PDF upload, page classification and document inventory will be migrated here.",
            "Apartments": "Apartment inventory and layout records will be migrated here.",
            "Review Layouts": "North, entrance and room review will be migrated here.",
            "Vastu Analysis": "Bulk apartment analysis will be connected here.",
            "Reports": "Builder project reports and exports will be connected here.",
        }
    st.info(descriptions.get(section, "This section will be migrated in the next sprint."))

def render() -> None:
    project_id = st.session_state.active_project_id
    if not project_id:
        navigate("Projects")
        return

    project = projects.get_project(int(project_id))
    if not project:
        st.session_state.active_project_id = None
        navigate("Projects")
        return

    workspace = project["workspace_type"]
    sections = (
        PROFESSIONAL_SECTIONS
        if workspace == "Professional"
        else BUILDER_SECTIONS
    )
    if st.session_state.project_section not in sections:
        st.session_state.project_section = "Project Setup"

    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.header(project["name"])
        st.caption(
            f"{workspace} workspace · {st.session_state.project_section}"
        )
    with header_right:
        if st.button("← Projects", use_container_width=True):
            navigate("Projects")

    if workspace == "Builder":
        st.markdown(
            '<div class="vai-builder-banner"><strong>Builder workspace</strong> · '
            'Project setup, layouts, professional review, knowledge intelligence and consolidated reporting.</div>',
            unsafe_allow_html=True,
        )

    section = st.session_state.project_section
    if workspace == "Builder":
        project_intelligence.render(project, section)
    elif section == "Overview":
        _render_overview(project)
    elif section == "Settings":
        _render_settings(project)
    elif workspace == "Professional" and section == "Numerology":
        professional_numerology.render(project)
    elif workspace == "Professional":
        # The complete Professional workflow is available from every
        # migrated Professional section. Its own horizontal navigation
        # controls Assessment, Results, Portfolio, Comparison and Dashboard.
        professional_workspace.render(project, section)
    else:
        _render_placeholder(section, workspace)
