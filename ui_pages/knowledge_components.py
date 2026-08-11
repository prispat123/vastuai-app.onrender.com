from __future__ import annotations

import pandas as pd
import streamlit as st

from project_intelligence import knowledge_service
from knowledge_engine.coverage import professional_coverage


def render_assessment(knowledge: dict | None) -> None:
    if not knowledge:
        return

    st.markdown("#### Knowledge Engine Findings")
    st.caption(
        f'Profile: {knowledge.get("profile_name", "—")} · '
        f'Knowledge confidence: '
        f'{float(knowledge.get("average_confidence", 0) or 0):.0%}'
    )

    summary = knowledge.get("reasoning_summary", "")
    if summary:
        st.info(summary)

    findings = knowledge.get("findings", [])
    if findings:
        frame = pd.DataFrame(
            [
                {
                    "Rule ID": item.get("rule_id"),
                    "Category": item.get("category"),
                    "Finding": item.get("title"),
                    "Direction": item.get("observed_value"),
                    "Polarity": item.get("polarity"),
                    "Severity": item.get("severity"),
                    "Confidence": item.get("combined_confidence"),
                }
                for item in findings
            ]
        )
        st.dataframe(frame, use_container_width=True, hide_index=True)

    actions = knowledge.get("priority_actions", [])
    if actions:
        st.markdown("#### Knowledge Recommendations")
        for action in actions:
            with st.expander(
                f'{action.get("severity", "Medium")} · '
                f'{action.get("recommendation_id", "")} · '
                f'{action.get("title", "Recommendation")}'
            ):
                st.write(
                    f'Triggered by {action.get("triggered_by", "")} — '
                    f'{action.get("finding", "")}'
                )
                for step in action.get("actions", []):
                    st.write(f"• {step}")
                for limitation in action.get("limitations", []):
                    st.caption(f"Limitation: {limitation}")


def _render_data_management() -> None:
    status = knowledge_service.knowledge_status()
    meta = status.get("meta") or {}
    counts = status["counts"]

    st.subheader("Local Knowledge Runtime")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Rules", counts["rules"])
    c2.metric("Recommendations", counts["recommendations"])
    c3.metric("Profiles", counts["profiles"])
    c4.metric("Relationships", counts["links"])

    st.caption(
        f'Runtime version: {meta.get("knowledge_version", "Not imported")} · '
        f'Imported: {meta.get("imported_at", "—")} · '
        "Storage: local SQLite"
    )

    left, right = st.columns(2)
    if left.button(
        "Validate and Refresh from JSON Master",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Validating and importing Knowledge Objects..."):
            try:
                result = knowledge_service.refresh_from_json()
            except Exception as exc:
                st.error(f"Knowledge import failed: {exc}")
            else:
                st.success(
                    f'{result["rules_imported"]} rules, '
                    f'{result["recommendations_imported"]} recommendations, '
                    f'{result["profiles_imported"]} profiles and '
                    f'{result["links_imported"]} relationships imported.'
                )
                st.rerun()

    right.download_button(
        "Export Local Knowledge Backup",
        data=knowledge_service.export_backup_bytes(),
        file_name=(
            f'vastuai_knowledge_backup_'
            f'{meta.get("knowledge_version", "unversioned")}.json'
        ),
        mime="application/json",
        use_container_width=True,
    )


def render_knowledge_base(project) -> None:
    st.header("Knowledge Base")
    st.caption(
        "The JSON bundle is the editable master source. Validated Knowledge "
        "Objects are imported into the local SQLite database and evaluated "
        "offline. No API call is required."
    )

    _render_data_management()

    with st.expander("Professional Knowledge Coverage", expanded=False):
        coverage = professional_coverage()
        c1, c2, c3 = st.columns(3)
        c1.metric("Directional coverage", f'{coverage["overall_coverage"]:.1f}%')
        c2.metric("Available objects", coverage["available_objects"])
        c3.metric("Missing objects", coverage["missing_count"])
        st.dataframe(
            pd.DataFrame(coverage["rows"]),
            use_container_width=True,
            hide_index=True,
        )
        if coverage["missing_count"]:
            st.warning(
                "Coverage gaps remain. Add versioned Knowledge Objects for "
                "the listed field-direction combinations."
            )
        else:
            st.success(
                "Every directional rule evaluated by the Professional engine "
                "has a corresponding VK Knowledge Object."
            )

    st.divider()

    repository = knowledge_service.repository()
    errors = repository.validate()
    if errors:
        st.error("\n".join(errors))
    else:
        st.success("Local Knowledge database validation passed.")

    profiles = repository.profiles()
    current = knowledge_service.get_profile(int(project["id"]))
    profile_keys = list(profiles)

    selected_profile = st.selectbox(
        "Project knowledge profile",
        profile_keys,
        index=profile_keys.index(current) if current in profile_keys else 0,
        format_func=lambda key: profiles[key]["name"],
    )

    selected_profile_data = profiles[selected_profile]
    st.caption(selected_profile_data["description"])
    st.caption(selected_profile_data["disclaimer"])

    if st.button("Save Project Knowledge Profile"):
        knowledge_service.set_profile(
            int(project["id"]),
            selected_profile,
        )
        st.success("Knowledge profile saved.")

    c1, c2, c3 = st.columns([2, 1, 1])
    query = c1.text_input(
        "Search local Knowledge Objects",
        placeholder="Kitchen, North-East, VK-...",
    )
    category = c2.selectbox(
        "Category",
        ["All"] + repository.categories(),
    )
    include_inactive = c3.checkbox("Show inactive", value=False)

    rules = repository.filter_rules(
        category=None if category == "All" else category,
        query=query or None,
        include_inactive=include_inactive,
    )

    frame = pd.DataFrame(
        [
            {
                "Rule ID": rule["rule_id"],
                "Category": rule["category"],
                "Title": rule["title"],
                "Direction": rule["direction"],
                "Polarity": rule["polarity"],
                "Severity": rule["severity"],
                "Score delta": rule["score_delta"],
                "Confidence": rule["knowledge_confidence"],
                "Version": rule["version"],
                "Active": rule["active"],
            }
            for rule in rules
        ]
    )
    st.dataframe(frame, use_container_width=True, hide_index=True)

    if not rules:
        st.info("No Knowledge Objects match the current filters.")
        return

    labels = {
        f'{rule["rule_id"]} · {rule["title"]}': rule
        for rule in rules
    }
    rule = labels[st.selectbox("Open Knowledge Object", list(labels))]

    st.subheader(f'{rule["rule_id"]} — {rule["title"]}')
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Severity", rule["severity"])
    c2.metric("Polarity", rule["polarity"].title())
    c3.metric("Confidence", f'{rule["knowledge_confidence"]:.0%}')
    c4.metric("Version", rule["version"])

    st.write(rule["explanation"])
    st.write(f'**Practical impact:** {rule["practical_impact"]}')
    if rule.get("architectural_note"):
        st.write(f'**Architectural note:** {rule["architectural_note"]}')
    if rule.get("existing_home_note"):
        st.write(f'**Existing-home note:** {rule["existing_home_note"]}')
    if rule.get("builder_note"):
        st.write(f'**Builder note:** {rule["builder_note"]}')
    st.caption(rule["source_note"])

    recommendations = repository.recommendations(
        include_inactive=include_inactive
    )
    for rec_id in rule.get("recommendation_ids", []):
        recommendation = recommendations.get(rec_id)
        if not recommendation:
            continue
        with st.expander(f'{rec_id} · {recommendation["title"]}'):
            st.write(
                f'**Stage:** {recommendation["stage"]} · '
                f'**Effort:** {recommendation["effort"]}'
            )
            for action in recommendation.get("actions", []):
                st.write(f"• {action}")
            for limitation in recommendation.get("limitations", []):
                st.caption(f"Limitation: {limitation}")

    related = repository.related_rules(rule["rule_id"])
    if related:
        st.markdown("#### Related Knowledge Objects")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Rule ID": item["rule_id"],
                        "Relationship": item["relationship"],
                        "Title": item["title"],
                        "Direction": item["direction"],
                        "Note": item["relationship_note"],
                    }
                    for item in related
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
