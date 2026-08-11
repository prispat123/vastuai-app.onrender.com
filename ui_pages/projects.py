from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from assessment_core.record_compatibility import normalize_professional_result
from platform_core import projects
from platform_core.database import connect
from platform_core.state import navigate


def _workspace_label(workspace: str) -> str:
    return "Professional" if workspace == "Professional" else "Builder"


def _professional_properties() -> list[dict]:
    """Return saved Professional properties across all underlying projects."""
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT pa.*, p.name AS project_name, p.status AS project_status,
                   p.client_or_builder AS project_client, p.city AS project_city,
                   p.workspace_type AS project_workspace_type
            FROM professional_analyses pa
            LEFT JOIN projects p ON p.id = pa.project_id
            ORDER BY pa.id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _professional_container_project_id() -> int:
    """Reuse the most recent Professional project as the hidden data container."""
    rows = projects.list_projects("Professional")
    if rows:
        return int(rows[0]["id"])
    return projects.create_project(
        name="Professional Properties",
        workspace_type="Professional",
        description="System workspace for Professional property assessments.",
    )


def _open_property(row: dict) -> None:
    st.session_state.active_project_id = int(row["project_id"])
    st.session_state.pending_project_section = "Vastu Analysis"
    st.session_state.analysis_result = normalize_professional_result(
        json.loads(row.get("result_json") or "{}")
    )
    st.session_state.last_payload = json.loads(row.get("payload_json") or "{}")
    st.session_state.last_saved_analysis_id = int(row["id"])
    st.session_state.analysis_complete = True
    st.session_state.editing_analysis_id = None
    st.session_state.edit_payload = None
    st.session_state.active_page = "Results"
    st.session_state.professional_menu = "Results"
    st.session_state.selected_property_label = (
        row.get("property_label") or row.get("flat_number") or f"Property P{row['id']}"
    )
    st.session_state.selected_property_id = int(row["id"])
    st.session_state.page = "Project"


def _new_property() -> None:
    project_id = _professional_container_project_id()
    st.session_state.active_project_id = project_id
    st.session_state.pending_project_section = "Vastu Analysis"
    st.session_state.analysis_result = None
    st.session_state.analysis_complete = False
    st.session_state.last_payload = None
    st.session_state.last_saved_analysis_id = None
    st.session_state.editing_analysis_id = None
    st.session_state.edit_payload = None
    st.session_state.active_page = "New assessment"
    st.session_state.professional_menu = "New assessment"
    st.session_state.selected_property_label = "New property"
    st.session_state.selected_property_id = None
    st.session_state.page = "Project"


def _render_professional_properties() -> None:
    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown("## Your Properties")
        st.caption("Open an assessment, review its scores, or continue with AI guidance.")
    with top_right:
        if st.button("＋ Add Property", type="primary", use_container_width=True):
            _new_property()
            st.rerun()

    rows = _professional_properties()
    if not rows:
        st.info("No saved properties yet. Add your first property to begin.")
        if st.button("Add first property", type="primary", use_container_width=True):
            _new_property()
            st.rerun()
        return

    frame = pd.DataFrame(rows)
    frame["Property"] = frame.apply(
        lambda r: r.get("property_label") or r.get("flat_number") or f"Property P{r['id']}", axis=1
    )
    frame["Apartment"] = frame["flat_number"].fillna("").replace("", "—")
    frame["Owner"] = frame["owner_name"].fillna("").replace("", "—")
    frame["Overall"] = pd.to_numeric(frame["overall_score"], errors="coerce")
    frame["Vastu"] = pd.to_numeric(frame["vastu_score"], errors="coerce")
    frame["Numerology"] = pd.to_numeric(frame["numerology_score"], errors="coerce")

    search_col, sort_col = st.columns([3, 1])
    search = search_col.text_input(
        "Search properties",
        placeholder="Property name, apartment number or buyer",
        key="professional_property_search",
    )
    sort_by = sort_col.selectbox(
        "Sort",
        ["Newest", "Highest score", "Property name"],
        key="professional_property_sort",
    )

    view = frame.copy()
    if search.strip():
        q = search.strip().lower()
        view = view[
            view.apply(
                lambda r: q in " ".join(
                    str(r.get(c, "")) for c in ["Property", "Apartment", "Owner", "project_city"]
                ).lower(),
                axis=1,
            )
        ]
    if sort_by == "Highest score":
        view = view.sort_values("Overall", ascending=False, na_position="last")
    elif sort_by == "Property name":
        view = view.sort_values("Property")
    else:
        view = view.sort_values("id", ascending=False)

    if view.empty:
        st.warning("No properties match your search.")
        return

    # A small overview gives orientation without turning the landing page into a dashboard.
    m1, m2, m3 = st.columns(3)
    m1.metric("Properties", len(frame))
    m2.metric("Portfolio average", f"{frame['Overall'].dropna().mean():.1f}/10" if frame['Overall'].notna().any() else "—")
    best = frame.loc[frame["Overall"].idxmax(), "Property"] if frame["Overall"].notna().any() else "—"
    m3.metric("Highest rated", str(best))
    st.markdown("### Open a property")

    # IMPORTANT: the property switcher must always be built from the complete
    # saved-property collection. Search/sort filters are presentation controls
    # for the table below and must never narrow the navigation selector.
    selector_frame = frame.sort_values("id", ascending=False)
    labels = {
        int(row["id"]): (
            f"{row['Property']}"
            + (f" · Apt {row['Apartment']}" if row["Apartment"] != "—" else "")
            + (f" · {row['Overall']:.1f}/10" if pd.notna(row['Overall']) else "")
        )
        for _, row in selector_frame.iterrows()
    }
    selector_options = list(labels)
    preferred_id = st.session_state.get("selected_property_id")
    selector_index = (
        selector_options.index(int(preferred_id))
        if preferred_id is not None and int(preferred_id) in selector_options
        else 0
    )
    selected_id = st.selectbox(
        "Select property",
        selector_options,
        index=selector_index,
        format_func=lambda value: labels[int(value)],
        key="professional_property_selector",
    )
    selected = next(row for row in rows if int(row["id"]) == int(selected_id))

    with st.container(border=True):
        left, overall, vastu, numero, right = st.columns([3.2, 1, 1, 1, 1.25])
        left.markdown(f"### {selected.get('property_label') or selected.get('flat_number') or f'Property P{selected_id}'}")
        left.caption(f"Buyer · {selected.get('owner_name') or 'Not specified'}  |  Apartment · {selected.get('flat_number') or 'Not specified'}")
        overall.metric("Overall", f"{float(selected.get('overall_score') or 0):.1f}/10")
        vastu.metric("Vastu", f"{float(selected.get('vastu_score') or 0):.1f}/10")
        numero.metric("Numerology", f"{float(selected.get('numerology_score') or 0):.1f}/10")
        if right.button("Open Property →", type="primary", use_container_width=True):
            _open_property(selected)
            st.rerun()

    st.markdown("### Property library")
    st.dataframe(
        view[["Property", "Apartment", "Owner", "Overall", "Vastu", "Numerology"]],
        use_container_width=True,
        hide_index=True,
    )


def _render_project_mode(workspace: str) -> None:
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.header(f"{_workspace_label(workspace)} Projects")
    with top_right:
        if st.button("← Platform", use_container_width=True):
            st.session_state.workspace = None
            st.session_state.active_project_id = None
            navigate("Home")

    tab_list, tab_new = st.tabs(["Projects", "New Project"])
    with tab_new:
        with st.form(f"new_project_{workspace}"):
            name = st.text_input("Project name")
            party_label = "Client name" if workspace == "Professional" else "Builder / Developer"
            client_or_builder = st.text_input(party_label)
            city = st.text_input("City")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Create Project", type="primary", use_container_width=True)
        if submitted:
            try:
                project_id = projects.create_project(
                    name=name, workspace_type=workspace,
                    client_or_builder=client_or_builder, city=city, description=description,
                )
                st.success("Project created successfully.")
                st.session_state.active_project_id = project_id
                st.session_state.pending_project_section = "Project Details" if workspace == "Builder" else "Overview"
                st.session_state.page = "Project"
                st.rerun()
            except Exception as exc:
                st.error(f"Could not create project: {exc}")

    with tab_list:
        rows = projects.list_projects(workspace)
        if not rows:
            st.info("No projects yet. Use the New Project tab.")
            return
        dataframe = pd.DataFrame([dict(row) for row in rows])
        st.dataframe(
            dataframe[["name", "client_or_builder", "city", "status", "created_at", "updated_at"]],
            use_container_width=True, hide_index=True,
        )
        labels = {f"{row['name']} · {row['client_or_builder'] or 'Not specified'}": row for row in rows}
        select_key = f"selected_project_{workspace}"

        def activate_selected_project() -> None:
            label = st.session_state.get(select_key)
            if not label:
                return
            selected_row = labels[label]
            st.session_state.active_project_id = int(selected_row["id"])
            st.session_state.project_section = "Project Details"

        selected_label = st.selectbox(
            "Select project", list(labels), index=None, placeholder="Choose a project",
            key=select_key, on_change=activate_selected_project,
        )
        if not selected_label:
            return
        selected = labels[selected_label]
        if st.button("Open Project", type="primary", use_container_width=True):
            navigate("Project", project_id=int(selected["id"]))


def render() -> None:
    workspace = st.session_state.workspace
    notice = st.session_state.pop("navigation_notice", None)
    if notice:
        st.info(notice)
    if workspace not in {"Professional", "Builder"}:
        navigate("Home")
        return
    if workspace == "Professional":
        _render_professional_properties()
    else:
        _render_project_mode(workspace)
