from __future__ import annotations

import pandas as pd
import streamlit as st

from professional_numerology import report_service, service


def _result(project, saved_property: dict, result: dict) -> None:
    st.divider()
    st.subheader("Numerology Assessment")
    numbers = result["calculated_numbers"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Birth Number", numbers["birth_number"])
    c2.metric("Life Path", numbers["life_path_number"])
    c3.metric("Property Number", numbers["property_number"])
    c4.metric("Numerology Score", f'{result["numerology_score"]:.1f}/100')
    st.write(f'**Grade:** {result["grade"]}')
    st.caption(
        f'Knowledge version {result["knowledge_version"]} · '
        f'Confidence {result["confidence"]:.0%}'
    )

    st.markdown("#### Numerology Knowledge IDs")
    rows = result["number_objects"] + result["alignment_objects"]
    st.dataframe(
        pd.DataFrame([
            {
                "Knowledge ID": item["object_id"],
                "Domain": item["domain"],
                "Title": item["title"],
                "Interpretation": item["summary"],
                "Version": item["version"],
            }
            for item in rows
        ]),
        use_container_width=True,
        hide_index=True,
    )

    st.info(result["disclaimer"])
    st.warning(
        "This Numerology score is independent of the Vastu score. "
        "Do not average or directly compare the two scores."
    )

    pdf = report_service.build_pdf(project["name"], result)
    st.download_button(
        "Download Individual Numerology PDF",
        data=pdf,
        file_name="professional_numerology_report.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
    )


def render(project) -> None:
    st.header("Professional Numerology")
    st.caption(
        "Individual-property assessment for the intended buyer. Numerology "
        "uses the buyer and property information already saved in Property "
        "Details, does not assess a tower, building or project, and is not "
        "entered again on this page."
    )

    properties = service.list_properties(int(project["id"]))
    if not properties:
        st.info(
            "No saved individual property is available. Complete and save "
            "Property Details first."
        )
        return

    labels = {
        f'P{row["id"]} · {row["property_label"]} · '
        f'{row["flat_number"] or "No property number"}': row
        for row in properties
    }
    selected_label = st.selectbox("Individual property", list(labels))
    selected = labels[selected_label]
    saved = service.get_property(int(project["id"]), int(selected["id"]))
    payload = saved["payload"] if saved else {}

    st.markdown("#### Property Details source")
    source_rows = [
        ["Property", payload.get("property_name") or selected["property_label"]],
        ["Intended user", payload.get("owner_name") or "Not provided"],
        ["Date of birth", payload.get("dob") or "Not provided"],
        ["Property number", payload.get("flat_number") or "Not provided"],
        ["Assessment year", payload.get("assessment_year") or "Not provided"],
    ]
    st.dataframe(
        pd.DataFrame(source_rows, columns=["Field", "Saved value"]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "To correct these values, open Property Details and edit the saved "
        "Professional property record."
    )

    missing = []
    if not str(payload.get("dob") or "").strip():
        missing.append("date of birth")
    if not str(payload.get("flat_number") or "").strip():
        missing.append("property number")
    if missing:
        st.warning("Missing in Property Details: " + ", ".join(missing) + ".")

    if st.button(
        "Run Numerology Assessment from Property Details",
        type="primary",
        use_container_width=True,
        disabled=bool(missing),
    ):
        try:
            with st.spinner("Evaluating local Numerology Knowledge Objects..."):
                response = service.run_assessment(
                    int(project["id"]), int(selected["id"])
                )
                st.session_state[
                    f'numerology_result_{selected["id"]}'
                ] = response["result"]
        except Exception as exc:
            st.error(str(exc))
        else:
            st.success("Numerology assessment completed from Property Details.")

    result = st.session_state.get(f'numerology_result_{selected["id"]}')
    if not result:
        result = service.latest_assessment(
            int(project["id"]), int(selected["id"])
        )
    if result:
        _result(project, saved, result)

    with st.expander("Numerology Knowledge Objects", expanded=False):
        query = st.text_input("Search Numerology Knowledge")
        st.dataframe(
            pd.DataFrame(service.repository().list_objects(query)),
            use_container_width=True,
            hide_index=True,
        )
