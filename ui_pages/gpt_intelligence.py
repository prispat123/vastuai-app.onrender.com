from __future__ import annotations

import pandas as pd
import streamlit as st

from project_intelligence import gpt_service

SUGGESTED_QUESTIONS = [
    "Which finalised flats have the highest scores, and why?",
    "Compare the strongest flats in each tower.",
    "Which tower has the strongest average result among finalised flats?",
    "What are the most common Vastu concerns in this project?",
    "Which layouts have favourable entrance directions?",
    "Which flats have South-West master bedrooms?",
    "Explain the most frequently triggered Knowledge rules.",
    "Which flats should a buyer shortlist based on the stored results?",
    "What design improvements should the builder prioritise?",
    "Summarise this project for a first-time home buyer.",
]


def _render_answer(result: dict | None) -> None:
    if not result:
        return
    st.divider()
    st.subheader("Answer")
    if result.get("question"):
        st.caption(f'Question: {result["question"]}')
    st.write(result["output_text"])
    st.caption(
        f'Generation {result["generation_id"]} · '
        f'Model {result["model_name"]} · '
        f'Source snapshot {result["source_hash"][:12]}…'
    )
    st.download_button(
        "Download Answer",
        data=result["output_text"].encode("utf-8"),
        file_name="vastuai_ai_consultant_answer.txt",
        mime="text/plain",
        use_container_width=True,
        key=f'gpt_answer_download_{result["generation_id"]}',
    )


def _settings() -> None:
    settings = gpt_service.get_settings()
    with st.expander("AI Consultant Settings", expanded=False):
        with st.form("gpt_settings_form"):
            enabled = st.checkbox("Enable AI Consultant", value=bool(settings["enabled"]))
            model_name = st.text_input("OpenAI model", value=settings["model_name"])
            effort_options = gpt_service.VALID_EFFORTS
            current_effort = settings["reasoning_effort"] if settings["reasoning_effort"] in effort_options else "low"
            reasoning_effort = st.selectbox(
                "Reasoning effort", effort_options, index=effort_options.index(current_effort),
                help="Low is faster. Increase only for difficult project-wide comparisons.",
            )
            style_options = gpt_service.VALID_STYLES
            current_style = settings["narrative_style"] if settings["narrative_style"] in style_options else "Professional"
            narrative_style = st.selectbox("Answer style", style_options, index=style_options.index(current_style))
            save = st.form_submit_button("Save AI Consultant Settings", type="primary")
        if save:
            gpt_service.save_settings(
                enabled=enabled,
                model_name=model_name,
                reasoning_effort=reasoning_effort,
                narrative_style=narrative_style,
                include_in_reports=False,
            )
            st.success("AI Consultant settings saved.")
            st.rerun()
        if gpt_service.api_key_configured():
            st.success("OPENAI_API_KEY is configured.")
        else:
            st.warning("OPENAI_API_KEY is not configured. Analysis, Knowledge, dashboards, PDF reports and exports remain available.")


def _qa(project) -> None:
    st.info(
        "For structured and in-depth details, use the Individual Flat, Tower, Building and Dashboard reports in Analysis & Review or Dashboard & Reports. Use the AI Consultant to compare, explain, shortlist and explore those verified results."
    )
    st.markdown("#### Evidence used in answers")
    st.caption("Verified = saved project facts · Stored Knowledge = rules saved with analysis · Applicable Knowledge = local rules matched from reviewed directions for this question.")
    selected = st.selectbox("Suggested question", ["Write my own question"] + SUGGESTED_QUESTIONS)
    question_key = "focused_gpt_question"
    if selected != "Write my own question" and st.button("Use Selected Question", use_container_width=True):
        st.session_state[question_key] = selected
        st.rerun()
    question = st.text_area(
        "Ask VastuAI",
        key=question_key,
        height=150,
        placeholder="Ask about a flat, compare flats or towers, explain Knowledge findings, shortlist properties, or request a buyer/builder summary.",
    )
    left, right = st.columns([3,1])
    ask = left.button("Ask AI Consultant", type="primary", use_container_width=True, disabled=not question.strip())
    clear = right.button("Clear", use_container_width=True)
    if clear:
        st.session_state.pop(question_key, None)
        st.session_state.pop("focused_gpt_result", None)
        st.rerun()
    if ask:
        try:
            with st.spinner("Building verified comparisons and applicable local Knowledge matches, then asking the AI Consultant to explain them..."):
                st.session_state["focused_gpt_result"] = gpt_service.generate_project_answer(
                    project_id=int(project["id"]), question=question
                )
        except Exception as exc:
            st.error(str(exc))
    _render_answer(st.session_state.get("focused_gpt_result"))


def _history(project) -> None:
    rows = gpt_service.history(int(project["id"]))
    if not rows:
        st.info("No AI Consultant history is available.")
        return
    st.dataframe(pd.DataFrame([dict(row) for row in rows]), use_container_width=True, hide_index=True)
    st.caption("History is retained for auditability. Failed requests are also recorded with error details.")


def render(project) -> None:
    st.header("AI Consultant")
    st.caption(
        "Ask questions about verified Professional analysis, reviewed room directions, stored Knowledge and deterministically applicable local Knowledge Objects. The AI Consultant explains and compares; it does not determine directions, rules or scores."
    )
    _settings()
    qa_tab, history_tab = st.tabs(["Q&A", "History"])
    with qa_tab:
        _qa(project)
    with history_tab:
        _history(project)
