from __future__ import annotations

from datetime import date, datetime
import json
import os
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st
from assessment_core.record_compatibility import normalize_professional_result
import pandas as pd
import matplotlib.pyplot as plt


# Streamlit Community Cloud exposes configured secrets through st.secrets.
# Copy only known keys into the environment so the service layer remains
# deployable outside Streamlit as well. Local .env values take precedence.
def load_streamlit_secrets() -> None:
    keys = ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_VISION_MODEL", "OPENAI_BASE_URL")
    try:
        for key in keys:
            if not os.getenv(key) and key in st.secrets:
                os.environ[key] = str(st.secrets[key])
    except Exception:
        # A missing secrets.toml is normal during local development.
        pass


load_streamlit_secrets()

from professional_app.version import __version__
from professional_app.services.floorplan_service import analyse_floor_plan
from professional_app.graph import analyze_property
from professional_app.utils.image_utils import assess_image_quality, image_to_png_bytes, uploaded_file_to_image
from professional_app.services.export_service import (
    build_export_bundle,
    to_csv_bytes,
    to_direction_balance_csv_bytes,
    to_json_bytes,
    to_room_scores_csv_bytes,
)
from professional_app.services.history_service import delete_analysis, get_analysis, list_analyses, save_analysis, update_analysis, update_metadata
from professional_app.services import ai_consultant_service, pdp_service
from professional_app.services import buyer_workspace_service
from professional_app.services import portfolio_consultant_service, portfolio_chat_service
from professional_app.services.pdf_service import build_comparison_pdf, build_pdf
from professional_app.services.comparison_service import rank_properties
from professional_app.services.logging_service import get_logger
from platform_core.openai_service import OPENAI

LOGGER = get_logger()


DIRECTIONS = [
    "Unknown", "North", "North-East", "East", "South-East", "South",
    "South-West", "West", "North-West", "Centre",
]
SUPPORTED_LAYOUT_TYPES = ["png", "jpg", "jpeg", "pdf"]
ROOM_FIELDS = [
    ("entrance_direction", "Main entrance"),
    ("kitchen_direction", "Kitchen"),
    ("master_bedroom_direction", "Master bedroom"),
    ("toilet_direction", "Toilet"),
    ("pooja_direction", "Pooja / meditation room"),
]

PASTEL = {
    "green": "#A8D5BA",
    "green_dark": "#5F8F72",
    "mint": "#DDF3E5",
    "amber": "#F6D6A8",
    "coral": "#F3B6A7",
    "red": "#E9A7A7",
    "lavender": "#CFC4E8",
    "peach": "#F8CFAF",
    "sage": "#C7D8C6",
    "cream": "#FFF9F0",
}

def _score_color(value: float) -> str:
    value = float(value or 0)
    if value >= 8: return PASTEL["green"]
    if value >= 6: return PASTEL["sage"]
    if value >= 4: return PASTEL["amber"]
    return PASTEL["coral"]

def _severity_color(value: str) -> str:
    return {"Low": PASTEL["green"], "None": PASTEL["green"], "Medium": PASTEL["amber"], "High": PASTEL["coral"], "Critical": PASTEL["red"]}.get(str(value), PASTEL["lavender"])

EXTRA_ROOM_FIELDS = [
    ("living_room_direction", "Living room"),
    ("balcony_direction", "Balcony / open space"),
    ("staircase_direction", "Staircase"),
    ("children_bedroom_direction", "Children's bedroom"),
    ("guest_bedroom_direction", "Guest bedroom"),
    ("dining_direction", "Dining area"),
    ("brahmasthan_direction", "Brahmasthan / central zone"),
    ("underground_tank_direction", "Underground tank / borewell"),
    ("overhead_tank_direction", "Overhead water tank"),
    ("parking_direction", "Parking"),
]


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root{--va-green:#A8D5BA;--va-green-dark:#5F8F72;--va-mint:#DDF3E5;--va-amber:#F6D6A8;--va-coral:#F3B6A7;--va-red:#E9A7A7;--va-cream:#FFF9F0;--va-ink:#26372E}
        .stApp{background:linear-gradient(180deg,#fbfefb 0%,#f6fbf7 50%,#fffaf4 100%);color:var(--va-ink)}
        [data-testid="stSidebar"]{background:linear-gradient(180deg,#edf8f0 0%,#f8fcf8 100%);border-right:1px solid #d7eadc}
        .block-container {max-width:100%;padding:.8rem 1.1rem 2.5rem 1.1rem}
        .hero {padding:1.15rem 1.3rem;border:1px solid #cfe5d5;border-radius:18px;background:linear-gradient(135deg,#DDF3E5,#FFF6E8);margin-bottom:1rem;box-shadow:0 5px 18px rgba(89,125,100,.08)}
        .hero h1 {margin:0;font-size:var(--vai-page-title,1.72rem);letter-spacing:-.025em;color:#315C43}.hero p{margin:.32rem 0 0;font-size:var(--vai-body,.94rem);opacity:.78}
        .section-kicker{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#5F8F72;margin-bottom:.15rem}
        .consult-card{padding:1rem 1.05rem;border:1px solid #d5e9da;border-radius:16px;background:#fbfefb;margin:.5rem 0 1rem;box-shadow:0 3px 12px rgba(89,125,100,.05)}
        .consult-card h3{margin:.05rem 0 .25rem;font-size:var(--vai-subtitle,1.04rem);color:#315C43}.consult-card p{margin:0;opacity:.75;font-size:var(--vai-label,.86rem)}
        .step-card{padding:.75rem .85rem;border:1px solid #d5e9da;background:#f8fcf9;border-radius:12px;min-height:88px}
        .step-number{font-size:.70rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#5F8F72}.step-title{font-size:var(--vai-label,.86rem);font-weight:700;margin-top:.2rem}
        .soft-note{padding:.7rem .8rem;border-left:4px solid #D6A45D;background:#FFF3DD;border-radius:8px}
        .status-pill{display:inline-block;padding:.26rem .58rem;border-radius:999px;background:#DDF3E5;border:1px solid #BFDCC8;color:#315C43;font-weight:700;font-size:.78rem;margin:.12rem .25rem .12rem 0}
        .result-banner{padding:.9rem 1rem;border-radius:15px;background:linear-gradient(135deg,#E4F5E9,#FFF4E2);border:1px solid #CEE4D4;margin-bottom:.75rem}.result-banner h2{margin:0 0 .35rem;color:#315C43}
        .semantic-good{background:#DDF3E5;color:#315C43}.semantic-medium{background:#FFF0D6;color:#7C5B27}.semantic-caution{background:#FCE2D9;color:#844C3D}.semantic-critical{background:#F8DADA;color:#803C3C}
        div[data-testid="stMetric"]{border:1px solid #d7eadc;border-radius:12px;padding:.55rem .7rem;background:#fbfefb;box-shadow:0 2px 8px rgba(89,125,100,.04)}
        div[data-testid="stMetricLabel"] p{font-size:.72rem!important;line-height:1.05!important;color:#55715f!important}
        div[data-testid="stMetricValue"]{font-size:1.22rem!important;line-height:1.15!important;color:#315C43!important}
        div[data-testid="stMetricDelta"]{font-size:.68rem!important}
        div[data-testid="stAlert"] p{font-size:.86rem!important}
        .stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"]{background:#78B88E!important;border-color:#78B88E!important;color:white!important}
        .stButton>button[kind="primary"]:hover,.stDownloadButton>button[kind="primary"]:hover{background:#5F9F75!important;border-color:#5F9F75!important}
        div[data-baseweb="tab-list"]{gap:.25rem} button[data-baseweb="tab"]{border-radius:9px 9px 0 0} button[data-baseweb="tab"][aria-selected="true"]{background:#E5F4E9;color:#315C43}
        @media (max-width:768px){
          .block-container{padding:.65rem .72rem 2rem!important}
          .hero{padding:.88rem .9rem!important;border-radius:14px!important;margin-bottom:.7rem!important}
          .consult-card{padding:.82rem .85rem!important;margin:.35rem 0 .7rem!important}
          .step-card{min-height:0!important;padding:.68rem .72rem!important}
          .result-banner{padding:.75rem .8rem!important}
          .soft-note{padding:.62rem .68rem!important}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialise_session_state() -> None:
    defaults = {
        "analysis_result": None,
        "analysis_complete": False,
        "input_mode": "Enter details manually",
        "layout_extraction": None,
        "layout_image_bytes": None,
        "last_payload": None,
        "last_saved_analysis_id": None,
        "editing_analysis_id": None,
        "edit_payload": None,
        "active_page": "New assessment",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_form_widgets() -> None:
    prefixes = ("manual_", "review_", "layout_")
    explicit = {"uploaded_floor_plan"}
    for key in list(st.session_state.keys()):
        if key.startswith(prefixes) or key in explicit:
            del st.session_state[key]


def reset_analysis(clear_forms: bool = False) -> None:
    st.session_state.analysis_result = None
    st.session_state.analysis_complete = False
    st.session_state.layout_extraction = None
    st.session_state.layout_image_bytes = None
    st.session_state.last_saved_analysis_id = None
    st.session_state.editing_analysis_id = None
    st.session_state.edit_payload = None
    if clear_forms:
        _clear_form_widgets()


def start_new_record() -> None:
    """Leave edit mode and initialise a completely blank assessment."""
    reset_analysis(clear_forms=True)
    # Clear navigation/widget values explicitly. This is important when the user
    # clicks Add another record while a saved record is open in Modify mode.
    st.session_state.input_mode = "Enter details manually"
    st.session_state.active_page = "New assessment"
    st.session_state.main_menu = "New assessment"
    st.session_state.assessment_notice = "A new blank assessment is ready."


def prepare_record_for_edit(analysis_id: int, payload: dict) -> None:
    _clear_form_widgets()
    st.session_state.editing_analysis_id = int(analysis_id)
    st.session_state.edit_payload = dict(payload)
    st.session_state.input_mode = "Enter details manually"
    st.session_state.analysis_result = None
    st.session_state.analysis_complete = False
    st.session_state.layout_extraction = None
    st.session_state.layout_image_bytes = None
    st.session_state.active_page = "New assessment"


def parse_optional_dob(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text


def render_workflow_steps() -> None:
    cols = st.columns(4)
    steps = [
        ("Step 1", "Provide details", "Manual entry or layout upload"),
        ("Step 2", "Validate layout", "North arrow and image quality"),
        ("Step 3", "Review extraction", "Confirm or correct AI results"),
        ("Step 4", "Run assessment", "Vastu, numerology and report"),
    ]
    for col, (number, title, text) in zip(cols, steps):
        with col:
            st.markdown(
                f'<div class="step-card"><div class="step-number">{number}</div>'
                f'<div class="step-title">{title}</div><div>{text}</div></div>',
                unsafe_allow_html=True,
            )


def render_vastu_details(details: list[dict]) -> None:
    if not details:
        st.info("Vastu was not assessed because the minimum Vastu information was not available.")
        return

    for item in details:
        score = float(item.get("score", 0))
        icon = "✅" if score >= 8 else "⚠️" if score >= 5 else "❗"
        with st.expander(
            f"{icon} {item.get('area', 'Area')} — {item.get('direction', 'Unknown')} "
            f"({score:g}/10, {item.get('status', 'Not rated')})"
        ):
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{score:g}/10")
            c2.metric("Issue severity", item.get("severity", "N/A"))
            c3.metric("Rule weight", item.get("weight", 1.0))
            st.write(item.get("rationale", ""))
            preferred = item.get("preferred", [])
            if preferred:
                st.write("**Traditionally preferred:** " + ", ".join(preferred))
            if score < 7:
                st.markdown("**Practical non-structural measure**")
                st.write(item.get("non_structural_remedy", "No remedy configured."))
                st.markdown("**Structural option — professional review required**")
                st.write(item.get("structural_remedy", "No structural option configured."))


def render_direction_wheel(details: list[dict]) -> None:
    direction_order = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
    aliases = {d.lower().replace(" ", "-"): d for d in direction_order}
    values = {d: [] for d in direction_order}
    for item in details:
        raw = str(item.get("direction", "")).strip()
        normal = raw.title().replace("Northeast", "North-East").replace("Southeast", "South-East").replace("Southwest", "South-West").replace("Northwest", "North-West")
        if normal in values:
            values[normal].append(float(item.get("score", 0) or 0))
    if not any(values.values()):
        st.info("The direction wheel will appear when directional room data is available.")
        return
    import numpy as np
    scores = [sum(values[d]) / len(values[d]) if values[d] else 0 for d in direction_order]
    angles = np.linspace(0, 2 * np.pi, len(direction_order), endpoint=False).tolist()
    angles += angles[:1]; plot_scores = scores + scores[:1]
    fig = plt.figure(figsize=(6.2, 6.2))
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    ax.plot(angles, plot_scores, marker="o", linewidth=2, color=PASTEL["green_dark"], label="Average room score")
    ax.fill(angles, plot_scores, alpha=.28, color=PASTEL["green"])
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(direction_order)
    ax.set_ylim(0, 10); ax.set_yticks([2, 4, 6, 8, 10]); ax.set_title("Directional balance wheel", pad=22)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, -0.18))
    fig.tight_layout(); st.pyplot(fig, clear_figure=True)


def render_results(result: dict, payload: dict) -> None:
    final = result.get("final_result", {})
    vastu = result.get("vastu_result", {})
    result = normalize_professional_result(result)
    numerology = result.get("numerology_result", {})
    recommendation = result.get("recommendation_result", {})

    st.divider()
    property_label = payload.get("property_name") or payload.get("flat_number") or "Property assessment"
    rating = final.get("rating", final.get("basis", "Assessment complete"))
    st.markdown(f'<div class="result-banner"><h2>{property_label}</h2><span class="status-pill">{rating}</span><span class="status-pill">Overall Professional Score {final.get("score", 0)}/10</span></div>', unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Assessment status", final.get("rating", "Complete"))
    cols[1].metric("Vastu score", f"{vastu.get('score', 'Not assessed')}/10" if vastu.get("score") is not None else "Not assessed")
    cols[2].metric("Numerology score", f"{numerology.get('score_100', 'Not assessed')}/100" if numerology.get("score_100") is not None else "Not assessed")
    cols[3].metric("Weighting", "50% / 50%" if final.get("basis") == "Equal-weight Vastu and Numerology" else final.get("basis", "N/A"))
    st.progress(min(max(float(final.get("score", 0)) / 10, 0.0), 1.0))
    st.caption(final.get("footnote", ""))

    dashboard_tab, overview_tab, vastu_tab, numerology_tab, recommendation_tab, consultant_tab, report_tab = st.tabs(
        ["Executive summary", "Overview", "Vastu", "Numerology", "Recommendations", "Consultant workspace", "Reports & export"]
    )
    with dashboard_tab:
        st.markdown("### Assessment dashboard")
        dcols = st.columns(4)
        dcols[0].metric("Overall Professional", f"{final.get('score', 0)}/10")
        dcols[1].metric("Vastu", f"{vastu.get('score', 'N/A')}/10")
        dcols[2].metric("Numerology", f"{numerology.get('score_100', 'N/A')}/100")
        dcols[3].metric("Confidence", recommendation.get("confidence", "N/A"))
        chart_left, chart_right = st.columns(2)
        with chart_left:
            labels, scores = [], []
            for item in vastu.get("details", []):
                labels.append(str(item.get("area", "Area")))
                scores.append(float(item.get("score", 0) or 0))
            if scores:
                fig, ax = plt.subplots(figsize=(7, max(3, len(scores) * .35)))
                ax.barh(labels, scores, color=[_score_color(v) for v in scores])
                ax.set_xlim(0, 10)
                ax.set_xlabel("Score out of 10")
                ax.set_title("Room-wise Vastu scores")
                fig.tight_layout()
                st.pyplot(fig, clear_figure=True)
            else:
                st.info("Room-wise chart will appear when Vastu details are available.")
        with chart_right:
            severity_counts = {}
            for item in vastu.get("details", []):
                severity = str(item.get("severity", "None"))
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            if severity_counts:
                fig, ax = plt.subplots(figsize=(5, 4))
                ax.pie(severity_counts.values(), labels=severity_counts.keys(), autopct="%1.0f%%", colors=[_severity_color(k) for k in severity_counts.keys()])
                ax.set_title("Issue severity distribution")
                fig.tight_layout()
                st.pyplot(fig, clear_figure=True)
            else:
                st.info("Severity chart will appear after Vastu assessment.")
        st.markdown("### Directional balance")
        render_direction_wheel(vastu.get("details", []))
    with overview_tab:
        st.markdown("### Deterministic executive explanation")
        st.write(result.get("explanation", "No explanation available."))
        if vastu.get("coverage") is not None:
            st.write(f"**Vastu coverage:** {vastu['coverage']}% ({vastu.get('evaluated_count', 0)} core factors evaluated)")

    with vastu_tab:
        st.markdown("### Professional Vastu assessment")
        summary_cols = st.columns(4)
        summary_cols[0].metric("Vastu grade", vastu.get("grade", "N/A"))
        summary_cols[1].metric("Coverage", f"{vastu.get('coverage', 0)}%")
        summary_cols[2].metric("Confidence", vastu.get("confidence", "N/A"))
        summary_cols[3].metric("Factors evaluated", vastu.get("evaluated_count", 0))

        critical = vastu.get("critical_issues", [])
        if critical:
            st.markdown("#### Priority issues")
            for item in critical:
                st.error(
                    f"{item.get('severity', 'High')} — {item.get('area')} in "
                    f"{item.get('direction')} ({item.get('score', 0):g}/10)"
                )

        st.markdown("#### Room-by-room rules, severity and remedies")
        render_vastu_details(vastu.get("details", []))

        if vastu.get("strengths"):
            st.markdown("#### Strengths")
            for item in vastu.get("strengths", []):
                st.write(f"✅ {item}")
        if vastu.get("cautions"):
            st.markdown("#### Points to review")
            for item in vastu.get("cautions", []):
                st.write(f"⚠️ {item}")

    with numerology_tab:
        if not numerology:
            st.info("Numerology was not assessed. Provide a property number and valid date of birth.")
        else:
            st.markdown("### Advanced Chaldean numerology")
            ncols = st.columns(4)
            ncols[0].metric("Numerology score", f"{numerology.get('score_100', 0)}/100")
            ncols[1].metric("Coverage", f"{numerology.get('coverage', 0)}%")
            ncols[2].metric("Confidence", numerology.get('confidence', 'N/A'))
            ncols[3].metric("Assessment year", numerology.get('assessment_year', 'N/A'))

            st.markdown("#### Core numbers")
            core = st.columns(5)
            core[0].metric("Birth", numerology.get('birth_number', 'N/A'))
            core[1].metric("Destiny", numerology.get('destiny_number', 'N/A'))
            core[2].metric("Attitude", numerology.get('attitude_number', 'N/A'))
            core[3].metric("Name root", numerology.get('name_root_number') or 'Not provided')
            core[4].metric("Personal year", numerology.get('personal_year_number', 'N/A'))

            st.markdown("#### Property number calculation")
            st.write(f"**Cleaned identifier:** {numerology.get('property_cleaned_number', '')}")
            st.write("**Breakdown:** " + " + ".join(numerology.get('property_breakdown', [])))
            st.write(f"**Compound → root:** {numerology.get('property_compound_number')} → {numerology.get('property_root_number')}")
            st.caption(numerology.get('property_compound_note', ''))

            st.markdown("#### Compatibility breakdown")
            for item in numerology.get('comparisons', []):
                label = item.get('reference', 'Reference')
                with st.expander(f"{label} {item.get('number')} — {item.get('status')} ({item.get('score_5')}/5)"):
                    st.write(item.get('explanation', ''))
                    st.write(f"Weight in numerology score: {float(item.get('weight', 0)):.0%}")

            st.markdown("#### Number profiles")
            profiles = numerology.get('profiles', {})
            for key, label in (("property", "Property root"), ("birth", "Birth number"), ("destiny", "Destiny number"), ("name", "Name number"), ("personal_year", "Personal year")):
                profile = profiles.get(key) or {}
                if not profile:
                    continue
                with st.expander(f"{label}: {profile.get('number')} — {profile.get('planet', '')}"):
                    st.write(profile.get('summary', ''))
                    if profile.get('keywords'):
                        st.write("**Traditional themes:** " + ", ".join(profile['keywords']))
                    if profile.get('supportive_directions'):
                        st.write("**Traditionally supportive directions:** " + ", ".join(profile['supportive_directions']))
                    if profile.get('supportive_colours'):
                        st.write("**Traditionally supportive colours:** " + ", ".join(profile['supportive_colours']))

            if numerology.get('strengths'):
                st.markdown("#### Strengths")
                for item in numerology['strengths']:
                    st.write(f"✅ {item}")
            if numerology.get('cautions'):
                st.markdown("#### Points to review")
                for item in numerology['cautions']:
                    st.write(f"⚠️ {item}")
            st.info(numerology.get('disclaimer', 'Numerology is belief-based guidance.'))

    with recommendation_tab:
        st.markdown("### Combined decision guidance")
        rcols = st.columns(4)
        rcols[0].metric("Decision", recommendation.get("decision", "N/A"))
        rcols[1].metric("Outlook", recommendation.get("sentiment", "N/A"))
        rcols[2].metric("Confidence", recommendation.get("confidence", "N/A"))
        rcols[3].metric("High-priority issues", recommendation.get("critical_issue_count", 0))

        for note in recommendation.get("synergy_notes", []):
            st.info(note)

        if recommendation.get("strengths"):
            st.markdown("#### Combined strengths")
            for item in recommendation["strengths"]:
                st.write(f"✅ {item}")

        if recommendation.get("actions"):
            st.markdown("#### Prioritised action plan")
            for index, item in enumerate(recommendation["actions"], start=1):
                with st.expander(f"{index}. {item.get('priority', 'Medium')} — {item.get('area', 'Property feature')}", expanded=index == 1):
                    st.write(f"**Finding:** {item.get('finding', '')}")
                    st.write(f"**Why it matters:** {item.get('why_it_matters', '')}")
                    st.write(f"**Practical action:** {item.get('practical_action', '')}")
                    st.warning(f"Structural option: {item.get('structural_option', '')}")

        st.markdown("#### Due-diligence next steps")
        for item in recommendation.get("next_steps", []):
            st.write(f"• {item}")
        st.caption(recommendation.get("disclaimer", ""))

    with consultant_tab:
        st.markdown("### Consultant workspace")
        analysis_id = st.session_state.get("last_saved_analysis_id")
        if not analysis_id:
            st.info("Save the assessment before adding workflow status, tags and consultant notes.")
        else:
            saved = get_analysis(int(analysis_id)) or {}
            statuses = ["Draft", "Needs review", "Client ready", "Client approved", "Archived"]
            current_status = saved.get("workflow_status") or "Draft"
            status_index = statuses.index(current_status) if current_status in statuses else 0
            c1, c2 = st.columns([1, 2])
            workflow_status = c1.selectbox("Workflow status", statuses, index=status_index, key=f"status_{analysis_id}")
            tags = c2.text_input("Tags", value=saved.get("tags") or "", placeholder="Example: premium, north-facing, follow-up", key=f"tags_{analysis_id}")
            consultant_notes = st.text_area("Consultant observations", value=saved.get("consultant_notes") or "", height=180,
                placeholder="Record client-specific observations, follow-up questions and professional judgement.", key=f"notes_{analysis_id}")
            if st.button("Save consultant workspace", type="primary", use_container_width=True):
                update_metadata(int(analysis_id), workflow_status, tags, consultant_notes)
                st.success("Status, tags and consultant notes saved.")
            st.caption("These notes are stored with the portfolio record and are not used to recalculate the Vastu score.")

    with report_tab:
        report_text = f"""VastuAI Property Compatibility Report

Owner: {payload.get('owner_name') or 'Not provided'}
Date of birth: {payload.get('dob') or 'Not provided'}
Apartment / property number: {payload.get('flat_number') or 'Not provided'}

Overall Professional Score: {final.get('score', 0)}/10
Rating: {final.get('rating', 'N/A')}
Assessment basis: {final.get('basis', 'N/A')}
Vastu score: {vastu.get('score', 'Not assessed')}
Vastu grade: {vastu.get('grade', 'N/A')}
Vastu coverage: {vastu.get('coverage', 0)}%
Vastu confidence: {vastu.get('confidence', 'N/A')}
Numerology score: {numerology.get('score_100', 'Not assessed')}/100
Numerology coverage: {numerology.get('coverage', 'Not assessed')}%
Birth / destiny / attitude: {numerology.get('birth_number', 'N/A')} / {numerology.get('destiny_number', 'N/A')} / {numerology.get('attitude_number', 'N/A')}
Name compound / root: {numerology.get('name_compound_number', 'N/A')} / {numerology.get('name_root_number', 'N/A')}
Property compound / root: {numerology.get('property_compound_number', 'N/A')} / {numerology.get('property_root_number', 'N/A')}
Personal year: {numerology.get('personal_year_number', 'N/A')}

Decision guidance: {recommendation.get('decision', 'N/A')}
Recommendation confidence: {recommendation.get('confidence', 'N/A')}
High-priority issues: {recommendation.get('critical_issue_count', 0)}

Weighting note:
{final.get('footnote', '')}

Explanation:
{result.get('explanation', '')}

Disclaimer:
This is belief-based guidance, not structural, legal, financial, scientific or investment advice.
"""
        st.markdown("### Professional reports and export package")
        st.caption("Sprint 3.2 reports include the directional balance wheel, room-wise score chart, direction summary table and detailed assessment findings.")
        property_slug = str(payload.get("property_name") or payload.get("flat_number") or "property").strip().replace(" ", "_")
        try:
            pdf_bytes = build_pdf(payload, result)
            bundle_bytes = build_export_bundle(payload, result, build_pdf, report_text)
            primary_left, primary_right = st.columns(2)
            primary_left.download_button(
                "Download visual professional PDF", pdf_bytes,
                f"VastuAI_{property_slug}.pdf", "application/pdf",
                type="primary", use_container_width=True,
            )
            primary_right.download_button(
                "Download complete export package", bundle_bytes,
                f"VastuAI_{property_slug}_Export_Package.zip", "application/zip",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Report generation failed: {exc}")
        st.markdown("#### Data exports")
        c1, c2, c3 = st.columns(3)
        c1.download_button("Assessment summary CSV", to_csv_bytes(payload, result), f"VastuAI_{property_slug}_Summary.csv", "text/csv", use_container_width=True)
        c2.download_button("Room scores CSV", to_room_scores_csv_bytes(result), f"VastuAI_{property_slug}_Room_Scores.csv", "text/csv", use_container_width=True)
        c3.download_button("Direction balance CSV", to_direction_balance_csv_bytes(result), f"VastuAI_{property_slug}_Direction_Balance.csv", "text/csv", use_container_width=True)
        d1, d2, d3 = st.columns(3)
        d1.download_button("Download enriched JSON", to_json_bytes(payload, result), f"VastuAI_{property_slug}.json", "application/json", use_container_width=True)
        d2.download_button("Download text report", report_text, f"VastuAI_{property_slug}.txt", "text/plain", use_container_width=True)
        d3.info("The ZIP package contains the PDF, both chart images, all CSV exports, JSON and text report.")


def direction_select(label: str, key: str, default: str = "Unknown") -> str:
    index = DIRECTIONS.index(default) if default in DIRECTIONS else 0
    return st.selectbox(label, DIRECTIONS, index=index, key=key)


def run_assessment(payload: dict) -> None:
    """Run the assessment, persist it, and move the user to Results.

    Any graph/runtime failure is shown in the UI instead of leaving the button
    looking unresponsive. Validation errors remain on the current form.
    """
    try:
        with st.spinner("Running the LangGraph assessment..."):
            result = analyze_property(payload)
    except Exception as exc:
        LOGGER.exception("Assessment failed")
        st.session_state.analysis_complete = False
        st.session_state.analysis_result = None
        st.error(f"Assessment could not be completed: {exc}")
        return

    errors = result.get("validation_errors", [])
    if errors:
        st.error("Please correct the following:")
        for error in errors:
            st.write(f"- {error}")
        return

    st.session_state.analysis_result = result
    st.session_state.analysis_complete = True
    st.session_state.last_payload = payload

    save_warning = None
    try:
        editing_id = st.session_state.get("editing_analysis_id")
        if editing_id:
            update_analysis(int(editing_id), payload, result)
            analysis_id = int(editing_id)
            st.session_state.editing_analysis_id = None
            st.session_state.edit_payload = None
            LOGGER.info(
                "Analysis %s updated for %s",
                analysis_id,
                payload.get("property_name") or payload.get("flat_number") or "Unnamed",
            )
        else:
            analysis_id = save_analysis(payload, result)
            LOGGER.info(
                "Analysis %s saved for %s",
                analysis_id,
                payload.get("property_name") or payload.get("flat_number") or "Unnamed",
            )
        st.session_state.last_saved_analysis_id = analysis_id
    except Exception as exc:
        LOGGER.exception("Could not save analysis")
        save_warning = f"Assessment completed, but history could not be saved: {exc}"

    st.session_state.assessment_notice = save_warning or "Assessment completed successfully."
    st.session_state.active_page = "Results"
    st.rerun()


def render_manual_form() -> None:
    edit_payload = st.session_state.get("edit_payload") or {}
    editing_id = st.session_state.get("editing_analysis_id")
    st.markdown("### Modify saved property" if editing_id else "### Manual property entry")
    if editing_id:
        st.info(f"Editing saved record P{editing_id}. Submitting will update the existing record rather than create a duplicate.")
    st.caption("Minimum required: entrance plus two other Vastu directions, OR property number plus date of birth. All extended Vastu fields are optional.")
    with st.form("manual_property_form"):
        left, right = st.columns(2, gap="large")
        with left:
            property_name = st.text_input("Property name / label (optional)", value=str(edit_payload.get("property_name", "")), key="manual_property_name")
            owner_name = st.text_input("Owner's full name (optional)", value=str(edit_payload.get("owner_name", "")), key="manual_owner_name")
            dob_text = st.text_input("Date of birth (optional, DD/MM/YYYY)", value=str(edit_payload.get("dob", "")), placeholder="26/07/1990", key="manual_dob")
            flat_number = st.text_input("Apartment / flat / house / villa number (optional)", value=str(edit_payload.get("flat_number", "")), key="manual_flat_number")
            assessment_year = st.number_input("Numerology assessment year (optional)", min_value=1900, max_value=2100, value=int(edit_payload.get("assessment_year") or date.today().year), step=1, key="manual_assessment_year")
        values = {}
        with right:
            for field, label in ROOM_FIELDS:
                values[field] = direction_select(label, f"manual_{field}", str(edit_payload.get(field, "Unknown")))
        with st.expander("Extended Vastu details (optional)", expanded=False):
            cols = st.columns(2)
            for index, (field, label) in enumerate(EXTRA_ROOM_FIELDS):
                with cols[index % 2]:
                    values[field] = direction_select(label, f"manual_{field}", str(edit_payload.get(field, "Unknown")))
        submitted = st.form_submit_button("Update assessment" if editing_id else "Analyse property", type="primary", use_container_width=True)

    if submitted:
        payload = {
            "property_name": property_name.strip(),
            "owner_name": owner_name.strip(),
            "dob": parse_optional_dob(dob_text),
            "flat_number": flat_number.strip(),
            "assessment_year": int(assessment_year),
            **values,
        }
        run_assessment(payload)


def extraction_default(extraction: dict, field: str) -> str:
    return extraction.get("rooms", {}).get(field, {}).get("value", "Unknown")


def render_extraction_review(extraction: dict) -> None:
    st.markdown("### Review detected rooms and directions")
    st.warning("AI and OCR results are advisory. Change any room direction before assessment.")

    room_labels = dict(ROOM_FIELDS + EXTRA_ROOM_FIELDS)
    extracted_rooms = extraction.get("rooms", {})

    # Individual controls are deliberately used instead of a wide data editor.
    # This keeps the direction selector visible on smaller displays and avoids
    # dependence on a horizontal scrollbar.
    reviewed_rows = []
    st.caption("Every detected feature has its own editable direction dropdown.")
    for index, (field, label) in enumerate(room_labels.items()):
        item = extracted_rooms.get(field, {})
        detected_direction = str(item.get("value", "Unknown"))
        if detected_direction not in DIRECTIONS:
            detected_direction = "Unknown"
        confidence = float(item.get("confidence", 0.0) or 0.0)

        with st.container(border=True):
            c1, c2, c3 = st.columns([1.2, 2.4, 1.2], gap="medium")
            include = c1.checkbox(
                "Include",
                value=detected_direction != "Unknown",
                key=f"review_include_{field}",
            )
            direction = c2.selectbox(
                f"{label} — change direction",
                DIRECTIONS,
                index=DIRECTIONS.index(detected_direction),
                key=f"review_direction_{field}",
                help=f"AI detected: {detected_direction}. Select the correct direction here.",
            )
            c3.metric("AI confidence", f"{confidence:.0%}")
            reviewed_rows.append({
                "field": field,
                "label": label,
                "include": include,
                "direction": direction,
                "confidence": confidence,
            })

    ocr = extraction.get("ocr", {})
    with st.expander("OCR text and performance details", expanded=False):
        if ocr.get("available"):
            st.caption("Locally extracted labels")
            st.code(ocr.get("text") or "No readable labels found.")
        else:
            st.info("Local OCR was skipped or unavailable. Vision analysis still completed. Install Tesseract OCR for local text extraction.")
            if ocr.get("error"):
                st.caption(ocr["error"])
        st.json(extraction.get("timings", {}))

    with st.form("layout_review_form"):
        left, right = st.columns(2, gap="large")
        with left:
            property_name = st.text_input("Property name / label (optional)", key="review_property_name")
            owner_name = st.text_input("Owner's full name (optional)", key="review_owner_name")
            dob_text = st.text_input("Date of birth (optional, DD/MM/YYYY)", placeholder="26/07/1990", key="review_dob")
        with right:
            flat_number = st.text_input("Apartment / flat / house / villa number (optional)", key="review_flat_number")
            assessment_year = st.number_input("Numerology assessment year", min_value=1900, max_value=2100, value=date.today().year, step=1, key="review_assessment_year")
            confirmed = st.checkbox("I reviewed the detected rooms and directions.", key="review_confirmed")
        submitted = st.form_submit_button("Apply directions and analyse property", type="primary", use_container_width=True)

    if submitted:
        if not confirmed:
            st.error("Please confirm that you reviewed the detected layout.")
            return
        values = {field: "Unknown" for field in room_labels}
        for row in reviewed_rows:
            if row["include"]:
                values[row["field"]] = row["direction"]
        payload = {
            "property_name": property_name.strip(),
            "owner_name": owner_name.strip(),
            "dob": parse_optional_dob(dob_text),
            "flat_number": flat_number.strip(),
            "assessment_year": int(assessment_year),
            "floorplan_analysis": {
                "mode": extraction.get("analysis_mode"),
                "north_orientation": extraction.get("north_orientation"),
                "timings": extraction.get("timings", {}),
                "ocr_labels": extraction.get("ocr", {}).get("labels", []),
            },
            **values,
        }
        run_assessment(payload)


def render_layout_upload() -> None:
    st.markdown("### Upload and analyse a floor plan")
    st.caption("Fast Mode is recommended. Results are cached, so the same plan opens almost instantly after its first analysis.")

    controls = st.columns([1, 1, 2])
    analysis_mode = controls[0].selectbox("Analysis mode", ["Fast", "Detailed"], index=0, key="layout_analysis_mode")
    north_orientation = controls[1].selectbox(
        "North orientation",
        ["Auto-detect", "Top edge", "Right edge", "Bottom edge", "Left edge"],
        key="layout_north_orientation",
    )
    controls[2].info("Fast: smaller image and low-detail vision. Detailed: higher resolution and high-detail vision.")

    uploaded_file = st.file_uploader("Choose a floor-plan file", type=SUPPORTED_LAYOUT_TYPES, key="uploaded_floor_plan")
    if uploaded_file is None:
        st.info("Upload a floor plan to begin analysis.")
        return

    file_bytes = uploaded_file.getvalue()
    try:
        image = uploaded_file_to_image(file_bytes, uploaded_file.name)
    except Exception as exc:
        st.error(f"Could not open this layout: {exc}")
        return

    png_bytes = image_to_png_bytes(image)
    quality = assess_image_quality(image)
    st.image(image, caption="Uploaded floor plan / first PDF page", use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Format", Path(uploaded_file.name).suffix.replace(".", "").upper())
    c2.metric("Dimensions", f"{quality.width} × {quality.height}")
    c3.metric("Local quality", f"{quality.quality_score}/100")
    c4.metric("Mode", analysis_mode)

    for issue in quality.issues:
        st.warning(issue)
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Configure OPENAI_API_KEY in the server environment or local .env before using automated layout analysis.")
        return

    action_cols = st.columns([3, 1])
    analyse_clicked = action_cols[0].button("Analyse floor plan", type="primary", use_container_width=True)
    refresh_clicked = action_cols[1].button("Force refresh", use_container_width=True)
    if analyse_clicked or refresh_clicked:
        with st.spinner("Preprocessing and running OCR + vision analysis..."):
            try:
                extraction = analyse_floor_plan(
                    png_bytes,
                    mode=analysis_mode,
                    north_orientation=north_orientation,
                    force_refresh=refresh_clicked,
                )
                extraction["local_quality"] = quality.__dict__
                st.session_state.layout_extraction = extraction
                st.session_state.layout_image_bytes = png_bytes
            except Exception as exc:
                LOGGER.exception("Floor-plan analysis failed")
                st.error(f"Floor-plan analysis failed: {exc}")
                return

    extraction = st.session_state.layout_extraction
    if not extraction:
        return

    st.divider()
    timings = extraction.get("timings", {})
    a, b, c, d = st.columns(4)
    a.metric("Floor plan", "Detected" if extraction.get("is_floor_plan") else "Unconfirmed")
    b.metric("North", "Detected" if extraction.get("north_detected") else north_orientation)
    c.metric("Confidence", f"{extraction.get('north_confidence', 0):.0%}")
    d.metric("Total time", f"{timings.get('total_seconds', 0):.1f}s", "Cache hit" if timings.get("cache_hit") else None)

    for issue in extraction.get("issues", []):
        st.warning(issue)
    if not extraction.get("is_floor_plan"):
        st.error("The uploaded image could not be confirmed as a floor plan.")
        return
    if north_orientation == "Auto-detect" and (not extraction.get("north_detected") or extraction.get("north_confidence", 0) < 0.65):
        st.error("North could not be detected reliably. Select the correct page edge as North or upload a clearer plan.")
        return
    if quality.quality_score < 35:
        st.error("Image quality is too low for dependable extraction.")
        return

    if timings.get("cache_hit"):
        st.success("Loaded the previous analysis from cache.")
    else:
        st.success("Analysis completed. Review and correct the detections below.")
    render_extraction_review(extraction)


def _portfolio_frame(rows: list[dict]) -> pd.DataFrame:
    ranked = rank_properties(rows)
    return pd.DataFrame([{
        "Rank": row["rank"], "Key": f"P{row['id']}", "ID": row["id"],
        "Property": row["property_label"],
        "Apartment number": row.get("flat_number") or "Not provided",
        "Display name": (f"{row['property_label']} ({row.get('flat_number')})"
                         if row.get("flat_number") and str(row.get("flat_number")) not in str(row["property_label"])
                         else str(row["property_label"])),
        "Owner": row.get("owner_name") or "", "Overall": row.get("overall_score"),
        "Vastu": row.get("vastu_score"), "Numerology": row.get("numerology_score"),
        "Confidence": row.get("confidence"),
        "Status": row.get("workflow_status") or "Draft",
        "Tags": row.get("tags") or "",
        "Created": str(row.get("created_at", ""))[:19].replace("T", " "),
    } for row in ranked])


def render_portfolio() -> None:
    st.subheader("Saved portfolio")
    rows = list_analyses(500)
    if not rows:
        st.info("No saved assessments yet. Create an assessment first.")
        return
    frame = _portfolio_frame(rows)
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    search = c1.text_input("Search", placeholder="Property, owner, status or tags")
    sort_by = c2.selectbox("Sort by", ["Newest", "Highest score", "Property name"])
    min_score = c3.number_input("Minimum score", min_value=0.0, max_value=10.0, value=0.0, step=0.5)
    status_filter = c4.selectbox("Status", ["All"] + sorted(frame["Status"].astype(str).unique().tolist()))
    view = frame.copy()
    if search.strip():
        q = search.strip().lower()
        view = view[view.apply(lambda r: q in " ".join(map(str, r.values)).lower(), axis=1)]
    view = view[pd.to_numeric(view["Overall"], errors="coerce").fillna(0) >= min_score]
    if status_filter != "All": view = view[view["Status"] == status_filter]
    if sort_by == "Highest score": view = view.sort_values("Overall", ascending=False)
    elif sort_by == "Property name": view = view.sort_values("Property")
    else: view = view.sort_values("ID", ascending=False)
    st.dataframe(view[["Key","Property","Apartment number","Owner","Overall","Vastu","Numerology","Status","Tags","Created"]], use_container_width=True, hide_index=True)
    if view.empty:
        st.warning("No records match the current filters.")
        return
    selected_id = st.selectbox("Selected record", view["ID"].tolist(),
        format_func=lambda value: f"P{value} — {frame.loc[frame['ID']==value,'Display name'].iloc[0]}")
    a,b,c,d = st.columns(4)
    if a.button("📂 Load", use_container_width=True):
        saved=get_analysis(int(selected_id))
        if saved:
            st.session_state.analysis_result=saved["result"]; st.session_state.last_payload=saved["payload"]
            st.session_state.last_saved_analysis_id=int(selected_id); st.session_state.analysis_complete=True
            st.session_state.editing_analysis_id=None; st.session_state.edit_payload=None
            st.session_state.active_page="Results"; st.rerun()
    if b.button("✏️ Edit", use_container_width=True):
        saved=get_analysis(int(selected_id))
        if saved: prepare_record_for_edit(int(selected_id), saved["payload"]); st.rerun()
    if c.button("📄 Duplicate", use_container_width=True):
        saved=get_analysis(int(selected_id))
        if saved:
            new_payload=dict(saved["payload"]); new_payload["property_name"] = f"{new_payload.get('property_name') or new_payload.get('flat_number') or 'Property'} copy"
            new_id=save_analysis(new_payload, saved["result"])
            st.success(f"Duplicated as P{new_id}."); st.rerun()
    if d.button("🗑️ Delete", use_container_width=True):
        st.session_state.pending_delete_id=int(selected_id)
    if st.session_state.get("pending_delete_id") == int(selected_id):
        st.warning(f"Delete P{selected_id}? This cannot be undone.")
        y,n=st.columns(2)
        if y.button("Yes, delete", type="primary", use_container_width=True):
            delete_analysis(int(selected_id)); st.session_state.pending_delete_id=None; st.rerun()
        if n.button("Cancel", use_container_width=True): st.session_state.pending_delete_id=None; st.rerun()


def render_comparison() -> None:
    st.subheader("Compare properties")
    rows=list_analyses(500)
    if len(rows)<2:
        st.info("Save at least two assessments to create a comparison.")
        return
    frame=_portfolio_frame(rows)
    selected_ids=st.multiselect("Select two or more records", frame["ID"].tolist(),
        format_func=lambda value: f"P{value} — {frame.loc[frame['ID']==value,'Display name'].iloc[0]}")
    if len(selected_ids)<2:
        st.info("Choose at least two records.")
        return
    selected=frame[frame["ID"].isin(selected_ids)].copy().sort_values("Overall",ascending=False)
    selected.insert(0,"Selected rank",range(1,len(selected)+1))
    st.dataframe(selected[["Selected rank","Key","Property","Apartment number","Overall","Vastu","Numerology","Confidence"]],use_container_width=True,hide_index=True)
    st.caption("Overall Professional Score gives equal importance to Vastu and Numerology when both are available: 50% each.")
    fig,ax=plt.subplots(figsize=(9,max(3.5,len(selected)*.6)))
    plot=selected.sort_values("Overall")
    _vals=pd.to_numeric(plot["Overall"],errors="coerce").fillna(0); ax.barh(plot["Key"],_vals,color=[_score_color(v) for v in _vals]); ax.set_xlim(0,10)
    ax.set_xlabel("Overall score"); ax.set_title("Selected property comparison"); fig.tight_layout(); st.pyplot(fig,clear_figure=True)
    st.dataframe(selected[["Key","Display name"]].rename(columns={"Display name":"Property legend"}),use_container_width=True,hide_index=True)
    chosen={int(x) for x in selected_ids}; selected_rows=[r for r in rows if int(r["id"]) in chosen]
    try:
        pdf=build_comparison_pdf(selected_rows)
        st.download_button("Download comparison PDF",pdf,"VastuAI_Selected_Comparison.pdf","application/pdf",type="primary",use_container_width=True)
    except Exception as exc: st.error(f"Comparison PDF generation failed: {exc}")


def render_dashboard() -> None:
    st.subheader("Portfolio dashboard")
    rows = list_analyses(500)
    if not rows:
        st.info("Dashboard metrics will appear after assessments are saved.")
        return

    frame = _portfolio_frame(rows)
    frame["Overall numeric"] = pd.to_numeric(frame["Overall"], errors="coerce").fillna(0.0)
    scores = frame["Overall numeric"]
    best = frame.loc[scores.idxmax()]
    lowest = frame.loc[scores.idxmin()]

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Saved properties", len(frame))
    k2.metric("Average score", f"{scores.mean():.1f}/10")
    k3.metric("Highest score", f"{scores.max():.1f}/10")
    k4.metric("Lowest score", f"{scores.min():.1f}/10")
    k5.metric("Top property", best["Key"])
    st.caption(f"Top property: {best['Display name']} · Lowest: {lowest['Display name']}")
    st.caption("Dashboard Overall Scores are equal-weight composites: 50% Professional Vastu and 50% Professional Numerology when both are available.")

    def score_band(value: float) -> str:
        if value >= 8:
            return "Excellent (8–10)"
        if value >= 6:
            return "Good (6–7.9)"
        if value >= 4:
            return "Needs review (4–5.9)"
        return "High concern (0–3.9)"

    frame["Score band"] = frame["Overall numeric"].map(score_band)
    band_order = ["Excellent (8–10)", "Good (6–7.9)", "Needs review (4–5.9)", "High concern (0–3.9)"]

    left, right = st.columns(2)
    with left:
        st.markdown("#### Property rankings")
        ranking = frame.sort_values("Overall numeric", ascending=True)
        fig, ax = plt.subplots(figsize=(9, max(4.5, len(ranking) * 0.42)))
        bars = ax.barh(ranking["Key"], ranking["Overall numeric"], color=[_score_color(v) for v in ranking["Overall numeric"]])
        ax.set_xlim(0, 10)
        ax.set_xlabel("Overall score")
        ax.set_title("All saved properties")
        for bar, value in zip(bars, ranking["Overall numeric"]):
            ax.text(min(value + 0.12, 9.7), bar.get_y() + bar.get_height()/2, f"{value:.1f}", va="center", fontsize=8)
        # The chart legend explains the record keys without requiring horizontal scrolling.
        legend_text = " · ".join(f"{r['Key']} = {r['Display name']}" for _, r in ranking.iterrows())
        ax.plot([], [], label="Property key legend below")
        ax.legend(loc="lower right", frameon=True)
        fig.tight_layout()
        st.pyplot(fig, clear_figure=True)
        with st.expander("Property legend", expanded=True):
            st.dataframe(
                ranking[["Key", "Display name", "Overall numeric"]].rename(columns={"Overall numeric": "Score"}),
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.markdown("#### Score distribution")
        counts = frame["Score band"].value_counts().reindex(band_order, fill_value=0)
        fig, ax = plt.subplots(figsize=(8, 4.8))
        bars = ax.bar(counts.index, counts.values, color=[PASTEL["green"], PASTEL["sage"], PASTEL["amber"], PASTEL["coral"]], label="Saved properties")
        ax.set_ylabel("Number of properties")
        ax.set_title("Portfolio score bands")
        ax.tick_params(axis="x", rotation=25)
        ax.legend(title="Legend", loc="upper right")
        for bar, value in zip(bars, counts.values):
            ax.text(bar.get_x() + bar.get_width()/2, value + 0.05, str(int(value)), ha="center", va="bottom")
        fig.tight_layout()
        st.pyplot(fig, clear_figure=True)

        st.markdown("#### Score trend")
        trend = frame.copy()
        trend["Created datetime"] = pd.to_datetime(trend["Created"], errors="coerce")
        trend = trend.sort_values(["Created datetime", "ID"])
        fig, ax = plt.subplots(figsize=(8, 4.2))
        ax.plot(range(1, len(trend) + 1), trend["Overall numeric"], marker="o", color=PASTEL["green_dark"], label="Overall score")
        ax.axhline(scores.mean(), linestyle="--", color="#D6A45D", label=f"Portfolio average ({scores.mean():.1f})")
        ax.set_ylim(0, 10)
        ax.set_xlabel("Assessment sequence")
        ax.set_ylabel("Score")
        ax.set_title("Saved assessment trend")
        ax.legend(title="Legend", loc="best")
        fig.tight_layout()
        st.pyplot(fig, clear_figure=True)

    st.divider()
    st.markdown("### All saved properties")
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    query = f1.text_input("Search dashboard properties", placeholder="Property, owner, tags or record key")
    selected_band = f2.selectbox("Score band", ["All"] + band_order)
    status_options = ["All"] + sorted(frame["Status"].fillna("Draft").astype(str).unique().tolist())
    selected_status = f3.selectbox("Status", status_options)
    dashboard_sort = f4.selectbox("Sort dashboard", ["Newest", "Highest score", "Lowest score", "Property name"])

    view = frame.copy()
    if query.strip():
        q = query.strip().lower()
        view = view[view.apply(lambda row: q in " ".join(map(str, row.values)).lower(), axis=1)]
    if selected_band != "All":
        view = view[view["Score band"] == selected_band]
    if selected_status != "All":
        view = view[view["Status"] == selected_status]
    if dashboard_sort == "Highest score":
        view = view.sort_values("Overall numeric", ascending=False)
    elif dashboard_sort == "Lowest score":
        view = view.sort_values("Overall numeric", ascending=True)
    elif dashboard_sort == "Property name":
        view = view.sort_values("Property")
    else:
        view = view.sort_values("ID", ascending=False)

    st.dataframe(
        view[["Key", "Property", "Apartment number", "Owner", "Overall", "Vastu", "Numerology", "Confidence", "Status", "Tags", "Score band", "Created"]],
        use_container_width=True,
        hide_index=True,
        height=min(650, 92 + max(1, len(view)) * 35),
    )
    st.caption(f"Showing {len(view)} of {len(frame)} saved properties.")

    if not view.empty:
        open_id = st.selectbox(
            "Open a saved property",
            view["ID"].tolist(),
            format_func=lambda value: f"P{value} — {frame.loc[frame['ID'] == value, 'Display name'].iloc[0]}",
            key="dashboard_open_id",
        )
        c1, c2 = st.columns(2)
        if c1.button("Open results", type="primary", use_container_width=True):
            saved = get_analysis(int(open_id))
            if saved:
                st.session_state.analysis_result = saved["result"]
                st.session_state.last_payload = saved["payload"]
                st.session_state.last_saved_analysis_id = int(open_id)
                st.session_state.analysis_complete = True
                st.session_state.editing_analysis_id = None
                st.session_state.edit_payload = None
                st.session_state.active_page = "Results"
                st.rerun()
        if c2.button("Edit property", use_container_width=True):
            saved = get_analysis(int(open_id))
            if saved:
                prepare_record_for_edit(int(open_id), saved["payload"])
                st.rerun()


def _navigate() -> None:
    st.session_state.active_page = st.session_state.main_menu




def render_saved_report_page() -> None:
    """Open a direct report/export screen for the left navigation Report item."""
    st.subheader("Professional report")
    rows = list_analyses(500)
    if not rows:
        st.info(
            "No saved assessment is available. Complete and save an "
            "individual Professional assessment first."
        )
        return

    options = [int(row["id"]) for row in rows]
    default_id = st.session_state.get("last_saved_analysis_id")
    default_index = options.index(default_id) if default_id in options else 0

    selected_id = st.selectbox(
        "Select saved assessment",
        options,
        index=default_index,
        format_func=lambda value: next(
            (
                f'P{value} — '
                f'{row.get("property_label") or row.get("property_name") or row.get("flat_number") or "Property"}'
                for row in rows
                if int(row["id"]) == int(value)
            ),
            f"P{value}",
        ),
        key="direct_report_record",
    )

    saved = get_analysis(int(selected_id))
    if not saved:
        st.error("The selected assessment could not be loaded.")
        return

    payload = saved.get("payload", {})
    result = normalize_professional_result(saved.get("result", {}))
    st.session_state.last_saved_analysis_id = int(selected_id)

    final = result.get("final_result", {})
    vastu = result.get("vastu_result", {})
    numerology = result.get("numerology_result", {})

    c1, c2, c3 = st.columns(3)
    c1.metric("Overall Professional", f'{final.get("score", 0)}/10')
    c2.metric(
        "Vastu",
        f'{vastu.get("score")}/10'
        if vastu.get("score") is not None else "Not assessed",
    )
    c3.metric(
        "Numerology",
        f'{numerology.get("score_100")}/100'
        if numerology.get("score_100") is not None else "Not assessed",
    )
    st.caption(final.get("footnote", ""))

    property_slug = str(
        payload.get("property_name")
        or payload.get("flat_number")
        or f"property_{selected_id}"
    ).strip().replace(" ", "_")

    report_text = (
        f"VastuAI Professional Property Report\\n\\n"
        f"Property: {payload.get('property_name') or 'Not provided'}\\n"
        f"Apartment / property number: "
        f"{payload.get('flat_number') or 'Not provided'}\\n"
        f"Owner: {payload.get('owner_name') or 'Not provided'}\\n\\n"
        f"Overall Professional Score: {final.get('score', 0)}/10\\n"
        f"Vastu score: {vastu.get('score', 'Not assessed')}\\n"
        f"Numerology score: "
        f"{numerology.get('score_100', 'Not assessed')}/100\\n\\n"
        f"{result.get('explanation', '')}\\n\\n"
        f"{final.get('footnote', '')}"
    )

    try:
        with st.spinner("Preparing report files..."):
            pdf_bytes = build_pdf(payload, result)
            bundle_bytes = build_export_bundle(
                payload,
                result,
                build_pdf,
                report_text,
            )
    except Exception as exc:
        st.error(f"Report generation failed: {exc}")
        return

    left, right = st.columns(2)
    left.download_button(
        "Download visual professional PDF",
        pdf_bytes,
        f"VastuAI_{property_slug}.pdf",
        "application/pdf",
        type="primary",
        use_container_width=True,
        key=f"direct_pdf_{selected_id}",
    )
    right.download_button(
        "Download complete export package",
        bundle_bytes,
        f"VastuAI_{property_slug}_Export_Package.zip",
        "application/zip",
        use_container_width=True,
        key=f"direct_bundle_{selected_id}",
    )

    with st.expander("Additional exports", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.download_button(
            "Assessment summary CSV",
            to_csv_bytes(payload, result),
            f"VastuAI_{property_slug}_Summary.csv",
            "text/csv",
            use_container_width=True,
            key=f"direct_summary_{selected_id}",
        )
        c2.download_button(
            "Room scores CSV",
            to_room_scores_csv_bytes(result),
            f"VastuAI_{property_slug}_Room_Scores.csv",
            "text/csv",
            use_container_width=True,
            key=f"direct_rooms_{selected_id}",
        )
        c3.download_button(
            "Enriched JSON",
            to_json_bytes(payload, result),
            f"VastuAI_{property_slug}.json",
            "application/json",
            use_container_width=True,
            key=f"direct_json_{selected_id}",
        )


def render_decision_profiles_page(project_id: int) -> None:
    st.subheader("Property Decision Profiles")
    st.caption("Canonical buyer decision profiles built from the same normalized assessment snapshot used by Professional reports.")

    backfill = pdp_service.backfill_missing_profiles(int(project_id))
    enrichment = pdp_service.enrich_existing_profiles(int(project_id))
    if backfill["created_count"]:
        st.success(f'Created {backfill["created_count"]} missing PDP(s) from saved assessments.')
    if enrichment["updated_count"]:
        st.success(f'Enriched {enrichment["updated_count"]} existing PDP(s) with Knowledge IDs and canonical metadata.')
    failures = list(backfill.get("failures", [])) + list(enrichment.get("failures", []))
    if failures:
        st.warning(f"{len(failures)} PDP migration item(s) need review.")
        with st.expander("PDP migration details"):
            st.json(failures)

    rows = pdp_service.list_profiles(int(project_id))
    if not rows:
        st.info("No PDP is available yet. Run a Professional assessment; the saved assessment and PDP are created automatically.")
        return

    selected = st.selectbox(
        "Select Property Decision Profile",
        [row["decision_id"] for row in rows],
        format_func=lambda value: next((f'{row["decision_id"]} — {row["property_name"] or "Property"} {row["property_number"] or ""}' for row in rows if row["decision_id"] == value), value),
        key="pdp_profile_select",
    )
    item = pdp_service.get_profile(selected)
    if not item:
        st.error("The selected PDP could not be loaded.")
        return
    profile=item["profile"]
    overall=profile.get("overall_professional",{})
    vastu=profile.get("vastu",{})
    numerology=profile.get("numerology",{})
    recommendation=profile.get("recommendation",{})
    versions=profile.get("versions",{})

    st.markdown(f'<div class="result-banner"><h2>{selected}</h2><span class="status-pill">{overall.get("rating") or "Not rated"}</span><span class="status-pill">Overall Professional {overall.get("score",0)}/10</span></div>', unsafe_allow_html=True)
    st.markdown("### Property Decision Profile")
    a,b=st.columns(2)
    a.write(f'**Buyer:** {profile.get("buyer",{}).get("owner_name") or "Not provided"}')
    a.write(f'**Date of birth:** {profile.get("buyer",{}).get("date_of_birth") or "Not provided"}')
    b.write(f'**Property:** {profile.get("property",{}).get("property_name") or "Not provided"}')
    b.write(f'**Property number:** {profile.get("property",{}).get("property_number") or "Not provided"}')

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Overall Professional",f'{overall.get("score",0)}/10')
    c2.metric("Professional Vastu",f'{vastu.get("score")}/10' if vastu.get("score") is not None else "Not assessed")
    c3.metric("Professional Numerology",f'{numerology.get("score_100")}/100' if numerology.get("score_100") is not None else "Not assessed")
    c4.metric("Critical / High",vastu.get("critical_high_count",0))
    st.caption(overall.get("footnote", ""))

    left,right=st.columns(2)
    with left:
        st.markdown("### Professional Vastu")
        x,y=st.columns(2)
        x.metric("Grade",vastu.get("grade") or "—")
        y.metric("Knowledge Objects",vastu.get("knowledge_count",len(vastu.get("knowledge_ids",[]))))
        st.write(f'**Coverage:** {vastu.get("coverage") if vastu.get("coverage") is not None else "—"}%')
        st.write(f'**Confidence:** {vastu.get("confidence") or "—"}')
        ids=vastu.get("knowledge_ids",[])
        st.write("**VK IDs:** "+(", ".join(ids) if ids else "None"))
        if vastu.get("strengths"):
            st.markdown("**Key strengths**")
            for value in vastu["strengths"][:4]: st.write(f"• {value}")
        if vastu.get("cautions"):
            st.markdown("**Review items**")
            for value in vastu["cautions"][:4]: st.write(f"• {value}")

    with right:
        st.markdown("### Professional Numerology")
        x,y=st.columns(2)
        x.metric("Grade",numerology.get("grade") or "—")
        y.metric("Knowledge Objects",numerology.get("knowledge_count",len(numerology.get("knowledge_ids",[]))))
        st.write(f'**Confidence:** {numerology.get("confidence") or "—"}')
        ids=numerology.get("knowledge_ids",[])
        st.write("**NUM IDs:** "+(", ".join(ids) if ids else "None"))
        nums=numerology.get("calculated_numbers",{})
        if nums:
            st.write(f'**Calculated numbers:** Birth {nums.get("birth_number","—")} · Life Path {nums.get("life_path_number","—")} · Property {nums.get("property_number","—")}')

    st.markdown("### Decision")
    x,y=st.columns(2)
    x.write(f'**Recommendation:** {recommendation.get("decision") or "Not stated"}')
    y.write(f'**Decision confidence:** {recommendation.get("confidence") or "Not stated"}')
    if recommendation.get("actions"):
        with st.expander("Priority actions"):
            for i,action in enumerate(recommendation["actions"][:6],1):
                st.write(f'**{i}. {action.get("priority") or "Priority"} — {action.get("area") or "Assessment finding"}**')
                if action.get("finding"): st.write(action["finding"])
                if action.get("practical_action"): st.write(f'Practical action: {action["practical_action"]}')

    st.markdown("### Buyer shortlist")
    buyer_workspace_service.sync_buyers_from_pdps()
    pdp_buyer = buyer_workspace_service.buyer_for_pdp(int(item["id"]))
    if pdp_buyer:
        if buyer_workspace_service.is_shortlisted(
            int(pdp_buyer["id"]),
            int(item["id"]),
        ):
            st.success(
                f'This property is already in '
                f'{pdp_buyer["buyer_name"]}\'s shortlist.'
            )
        elif st.button(
            "Add this property to Buyer Shortlist",
            type="primary",
            use_container_width=True,
            key=f'pdp_shortlist_{item["id"]}',
        ):
            buyer_workspace_service.add_to_shortlist(
                int(pdp_buyer["id"]),
                int(item["id"]),
            )
            st.rerun()
    else:
        st.warning(
            "Buyer identity is unavailable for this PDP. "
            "Check buyer name and date of birth."
        )

    st.markdown("### Assessment provenance")
    st.caption(f'Platform {versions.get("platform") or "—"} · Vastu Knowledge {versions.get("vastu_knowledge") or "—"} · Numerology Knowledge {versions.get("numerology_knowledge") or "—"} · Source analysis P{profile.get("analysis_id","—")}')
    with st.expander("PDP audit data"):
        st.json(profile)
    st.download_button("Download PDP JSON",json.dumps(profile,ensure_ascii=False,indent=2,default=str).encode("utf-8"),f"{selected}.json","application/json",type="primary",use_container_width=True,key=f"pdp_json_{selected}")

def render_buyer_workspace_page(project_id: int) -> None:
    st.subheader("Buyer Workspace")
    st.caption(
        "Shortlist assessed properties for one buyer across all Professional "
        "projects. The shortlist references immutable PDPs and never "
        "recalculates assessment scores."
    )

    sync = buyer_workspace_service.sync_buyers_from_pdps()
    if sync["failure_count"]:
        st.warning(
            f'{sync["failure_count"]} PDP(s) could not be linked to a Buyer.'
        )

    buyers = buyer_workspace_service.list_buyers()
    if not buyers:
        st.info("Run a Professional assessment with buyer details first.")
        return

    buyer_id = st.selectbox(
        "Buyer",
        [int(row["id"]) for row in buyers],
        format_func=lambda value: next(
            (
                f'{row["buyer_name"]}'
                + (
                    f' · DOB {row["date_of_birth"]}'
                    if row.get("date_of_birth") else ""
                )
                + f' · {row["shortlist_count"]} shortlisted'
                for row in buyers
                if int(row["id"]) == int(value)
            ),
            f"Buyer {value}",
        ),
        key="buyer_workspace_buyer",
    )
    buyer = buyer_workspace_service.get_buyer(int(buyer_id))
    pdps = buyer_workspace_service.list_buyer_pdps(int(buyer_id))
    shortlist = buyer_workspace_service.list_shortlist(int(buyer_id))

    st.markdown("### Buyer profile")
    a, b = st.columns(2)
    a.write(f'**Buyer:** {buyer["buyer_name"]}')
    a.write(
        f'**Date of birth:** '
        f'{buyer.get("date_of_birth") or "Not provided"}'
    )
    with b:
        with st.form(f"buyer_contact_{buyer_id}"):
            email = st.text_input("Email", value=buyer.get("email") or "")
            phone = st.text_input("Phone", value=buyer.get("phone") or "")
            if st.form_submit_button("Update contact"):
                buyer_workspace_service.update_buyer_contact(
                    int(buyer_id), email=email, phone=phone
                )
                st.rerun()

    best = max(
        [float(row.get("overall_score") or 0) for row in shortlist],
        default=0.0,
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Assessed PDPs", len(pdps))
    m2.metric("Shortlisted", len(shortlist))
    m3.metric(
        "Best shortlist score",
        f"{best:.1f}/10" if shortlist else "—",
    )

    st.markdown("### Assessed properties")
    table = []
    for row in pdps:
        table.append(
            {
                "PDP": row["decision_id"],
                "Project": row["project_name"],
                "Property": (
                    f'{row.get("property_name") or "Property"} '
                    f'{row.get("property_number") or ""}'
                ).strip(),
                "Overall": row.get("overall_score"),
                "Vastu": row.get("vastu_score"),
                "Numerology": row.get("numerology_score_100"),
                "Critical / High": row.get("critical_high_count", 0),
                "Decision": row.get("recommendation"),
                "Shortlisted": "Yes" if row.get("shortlisted") else "No",
            }
        )
    if table:
        st.dataframe(
            pd.DataFrame(table),
            use_container_width=True,
            hide_index=True,
        )

    available = [row for row in pdps if not row.get("shortlisted")]
    if available:
        selected_pdp = st.selectbox(
            "Add assessed property",
            [int(row["id"]) for row in available],
            format_func=lambda value: next(
                (
                    f'{row["decision_id"]} — {row["project_name"]} — '
                    f'{row.get("property_name") or "Property"} '
                    f'{row.get("property_number") or ""}'
                    for row in available
                    if int(row["id"]) == int(value)
                ),
                f"PDP {value}",
            ),
            key="buyer_workspace_add",
        )
        if st.button(
            "Add selected property to shortlist",
            type="primary",
            use_container_width=True,
        ):
            buyer_workspace_service.add_to_shortlist(
                int(buyer_id), int(selected_pdp)
            )
            st.rerun()

    st.divider()
    st.markdown("### My Shortlist")
    shortlist = buyer_workspace_service.list_shortlist(int(buyer_id))
    if not shortlist:
        st.info("No shortlisted properties yet.")
        return

    summary = []
    for rank, row in enumerate(shortlist, 1):
        summary.append(
            {
                "Order": rank,
                "PDP": row["decision_id"],
                "Project": row["project_name"],
                "Property": (
                    f'{row.get("property_name") or "Property"} '
                    f'{row.get("property_number") or ""}'
                ).strip(),
                "Overall": row.get("overall_score"),
                "Vastu": row.get("vastu_score"),
                "Numerology": row.get("numerology_score_100"),
                "Critical / High": row.get("critical_high_count", 0),
                "Decision": row.get("recommendation"),
            }
        )
    st.dataframe(
        pd.DataFrame(summary),
        use_container_width=True,
        hide_index=True,
    )

    for rank, row in enumerate(shortlist, 1):
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 2, 3])
            c1.markdown(
                f'**{rank}. {row["decision_id"]} — '
                f'{row["project_name"]}**'
            )
            c1.write(
                f'{row.get("property_name") or "Property"} · '
                f'{row.get("property_number") or "No number"}'
            )
            c1.caption(
                f'Overall {row.get("overall_score")}/10 · '
                f'Vastu {row.get("vastu_score")}/10 · '
                f'Numerology {row.get("numerology_score_100")}/100'
            )
            c2.metric("Critical / High", row.get("critical_high_count", 0))
            with c3:
                x, y, z = st.columns(3)
                if x.button(
                    "↑",
                    disabled=rank == 1,
                    key=f'up_{buyer_id}_{row["id"]}',
                ):
                    buyer_workspace_service.move_shortlist_item(
                        int(buyer_id), int(row["id"]), "up"
                    )
                    st.rerun()
                if y.button(
                    "↓",
                    disabled=rank == len(shortlist),
                    key=f'down_{buyer_id}_{row["id"]}',
                ):
                    buyer_workspace_service.move_shortlist_item(
                        int(buyer_id), int(row["id"]), "down"
                    )
                    st.rerun()
                if z.button(
                    "Remove",
                    key=f'remove_{buyer_id}_{row["id"]}',
                ):
                    buyer_workspace_service.remove_from_shortlist(
                        int(buyer_id), int(row["id"])
                    )
                    st.rerun()

    st.info(
        "Next, Portfolio Consultant and Buying Advisor will consume these "
        "shortlisted PDPs without changing the deterministic assessments."
    )


def render_portfolio_consultant_page(project_id: int) -> None:
    st.subheader("AI Portfolio Consultant")
    st.caption(
        "Select a buyer, choose whether to review the full shortlist or compare two properties, "
        "then ask the AI Consultant. Comparison and reasoning are shown only in the consultant response."
    )

    sync = buyer_workspace_service.sync_buyers_from_pdps()
    if sync["failure_count"]:
        st.warning(f'{sync["failure_count"]} PDP(s) could not be linked to a Buyer.')

    buyers = buyer_workspace_service.list_buyers()
    buyers = [row for row in buyers if int(row.get("shortlist_count") or 0) > 0]
    if not buyers:
        st.info("Add at least one assessed property to a Buyer Workspace shortlist first.")
        return

    buyer_id = st.selectbox(
        "Select buyer",
        [int(row["id"]) for row in buyers],
        format_func=lambda value: next(
            (
                f'{row["buyer_name"]}'
                + (f' · DOB {row["date_of_birth"]}' if row.get("date_of_birth") else "")
                + f' · {row["shortlist_count"]} shortlisted'
                for row in buyers if int(row["id"]) == int(value)
            ),
            f"Buyer {value}",
        ),
        key="portfolio_consultant_buyer",
    )

    portfolio = portfolio_consultant_service.analyse_shortlist(int(buyer_id))
    ranked = portfolio["ranked"]
    if not ranked:
        st.info("The selected buyer has no shortlisted properties.")
        return

    st.markdown("### Consultation scope")
    scope = st.radio(
        "What would you like the consultant to use?",
        ["Full shortlist", "Compare two properties"],
        horizontal=True,
        key="portfolio_consultation_scope",
    )

    selected_decision_ids = None
    if scope == "Compare two properties":
        if len(ranked) < 2:
            st.info("Add one more property to this buyer's shortlist to use two-property comparison.")
            return

        labels = {
            str(row["decision_id"]): (
                f'{row["decision_id"]} · {row["project_name"]} · {row["property_label"]}'
            )
            for row in ranked
        }
        ids = list(labels)
        left, right = st.columns(2)
        first = left.selectbox(
            "Property 1", ids, format_func=lambda value: labels[value],
            key="portfolio_compare_first",
        )
        second_options = [value for value in ids if value != first]
        second = right.selectbox(
            "Property 2", second_options, format_func=lambda value: labels[value],
            key="portfolio_compare_second",
        )
        selected_decision_ids = [first, second]
        st.caption("Only these two saved PDPs will be supplied to the AI for this comparison.")
    else:
        st.caption(f'AI will use all {len(ranked)} shortlisted saved PDPs for this buyer.')

    starter_cols = st.columns(3)
    starter_questions = (
        [
            "Which shortlisted property is best overall, and why?",
            "Rank my shortlist and explain the main trade-offs.",
            "Which property gives the best balance of Vastu and Numerology?",
        ]
        if scope == "Full shortlist"
        else [
            "Which of these two properties is better overall, and why?",
            "Compare these two properties on Vastu, Numerology and recorded concerns.",
            "What do I gain and compromise with each of these two properties?",
        ]
    )
    for idx, starter in enumerate(starter_questions):
        if starter_cols[idx].button(
            starter, key=f"portfolio_prompt_{scope}_{idx}", use_container_width=True
        ):
            st.session_state.portfolio_chat_question = starter

    question = st.text_area(
        "Ask AI Consultant",
        key="portfolio_chat_question",
        placeholder=(
            "Example: Which property should I investigate first and what are the main trade-offs?"
            if scope == "Full shortlist"
            else "Example: Between these two, which is the stronger choice and why?"
        ),
        height=120,
    )
    if st.button(
        "Ask AI Consultant",
        type="primary",
        disabled=not str(question or "").strip(),
        use_container_width=True,
        key="ask_portfolio_consultant",
    ):
        try:
            with st.spinner("Preparing the verified shortlist context..."):
                st.session_state.portfolio_chat_answer = portfolio_chat_service.ask(
                    int(project_id),
                    int(buyer_id),
                    question,
                    decision_ids=selected_decision_ids,
                )
        except Exception as exc:
            st.error(str(exc))

    current_context = portfolio_chat_service.portfolio_context(
        int(buyer_id), decision_ids=selected_decision_ids
    )
    answer = st.session_state.get("portfolio_chat_answer")
    if answer and answer.get("source_hash") == current_context["source_hash"]:
        st.markdown("### AI Consultant response")
        st.write(answer["answer"])
        st.caption(
            f'Generation {answer["history_id"]} · {answer["model_name"]} · '
            f'{answer["source_hash"][:12]}…'
        )
        property_name = str(payload.get("property_name") or payload.get("flat_number") or "Property")
        ai_pdf = ai_consultant_service.build_response_pdf(
            property_name=property_name,
            question=str(st.session_state.get("ai_consultant_question") or ""),
            answer=str(answer["answer"]),
            model_name=str(answer.get("model_name") or ""),
        )
        st.download_button(
            "Download AI Response PDF",
            data=ai_pdf,
            file_name=f"VastuAI_{_safe_filename(property_name)}_AI_Consultant.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"ai_response_pdf_{analysis_id}_{answer['history_id']}",
        )

    with st.expander("Conversation history"):
        chat_history = portfolio_chat_service.history(int(buyer_id))
        if chat_history:
            display_history = [
                {
                    "When": row.get("created_at"),
                    "Question": row.get("question_text"),
                    "Answer": row.get("answer_text"),
                    "Status": row.get("status"),
                }
                for row in chat_history
            ]
            st.dataframe(pd.DataFrame(display_history), use_container_width=True, hide_index=True)
        else:
            st.info("No AI portfolio conversation history yet.")

    st.info(
        "AI Portfolio Consultant uses only saved PDPs and does not recalculate assessment scores. "
        "Vastu and Numerology are belief-based guidance and are not financial, legal, structural, "
        "safety, valuation or investment advice."
    )

def render_ai_consultant_page(project_id: int) -> None:
    st.markdown('<div class="section-kicker">Property intelligence</div>', unsafe_allow_html=True)
    st.subheader("AI Consultant")
    st.markdown(
        '<div class="consult-card"><h3>Ask about this property</h3>'
        '<p>The consultant explains the verified saved assessment, including score reasoning, '
        'Vastu strengths, concerns, numerology and buyer checks. Saved scores are never changed.</p></div>',
        unsafe_allow_html=True,
    )
    rows = list_analyses(500)
    if not rows:
        st.info("Complete and save an assessment first.")
        return
    ids = [int(row["id"]) for row in rows]
    analysis_id = st.selectbox(
        "Select saved assessment",
        ids,
        format_func=lambda value: next(
            f'P{value} — {row.get("property_label") or row.get("property_name") or row.get("flat_number") or "Property"}'
            for row in rows if int(row["id"]) == value
        ),
    )
    saved = get_analysis(int(analysis_id))
    payload = saved.get("payload", {})
    result = normalize_professional_result(saved.get("result", {}))
    st.markdown("#### Suggested questions")
    starter_questions = [
        "Why did this property receive its overall score?",
        "What are the strongest Vastu features of this property?",
        "What are the main concerns or compromises I should know about?",
        "How does Numerology affect the recommendation for this property?",
        "What should I verify before making a buying decision?",
        "Explain the final recommendation in simple buyer-friendly language.",
    ]
    prompt_rows = [starter_questions[:3], starter_questions[3:]]
    for row_index, prompt_row in enumerate(prompt_rows):
        cols = st.columns(3)
        for col_index, starter in enumerate(prompt_row):
            if cols[col_index].button(
                starter,
                key=f"property_ai_prompt_{analysis_id}_{row_index}_{col_index}",
                use_container_width=True,
            ):
                st.session_state.ai_consultant_question = starter

    question = st.text_area(
        "Ask the AI Consultant",
        key="ai_consultant_question",
        placeholder="Why did this property receive its score?",
        height=140,
    )
    if st.button(
        "Ask AI Consultant",
        type="primary",
        disabled=not question.strip(),
        use_container_width=True,
    ):
        try:
            with st.spinner("Preparing verified assessment context..."):
                st.session_state.ai_consultant_answer = ai_consultant_service.ask(
                    int(project_id), int(analysis_id), payload, result, question
                )
        except Exception as exc:
            st.error(str(exc))
    answer = st.session_state.get("ai_consultant_answer")
    if answer:
        st.markdown("#### Consultant response")
        st.write(answer["answer"])
        st.caption(
            f'Generation {answer["history_id"]} · {answer["model_name"]} · '
            f'{answer["source_hash"][:12]}…'
        )
    with st.expander("Consultation history"):
        history = ai_consultant_service.history(int(project_id), int(analysis_id))
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
        else:
            st.info("No consultation history.")

def render_section(project_id: int, requested_section: str | None = None) -> None:
    from professional_app.services.history_service import set_active_project
    set_active_project(project_id)

    apply_theme()
    initialise_session_state()

    if requested_section == "Decision Profiles":
        st.markdown('<div class="hero"><h1>🧭 VastuAI Professional</h1><p>Buyer decision profiles.</p></div>', unsafe_allow_html=True)
        render_decision_profiles_page(project_id)
        return

    if requested_section == "Buyer Workspace":
        st.markdown(
            '<div class="hero"><h1>🧭 VastuAI Professional</h1>'
            '<p>Buyer-centric property shortlist and decision workspace.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        render_buyer_workspace_page(project_id)
        return

    if requested_section == "AI Portfolio Consultant":
        st.markdown(
            '<div class="hero"><h1>🧭 VastuAI Professional</h1>'
            '<p>Portfolio-level comparison of shortlisted buyer properties.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        render_portfolio_consultant_page(project_id)
        return

    if requested_section == "AI Consultant":
        st.markdown('<div class="hero"><h1>AI Consultant</h1><p>Ask questions grounded in the selected property assessment.</p></div>', unsafe_allow_html=True)
        render_ai_consultant_page(project_id)
        return

    if requested_section == "Report":
        st.markdown(
            '<div class="hero"><h1>🧭 VastuAI Professional</h1>'
            '<p>Individual buyer report and export centre.</p></div>',
            unsafe_allow_html=True,
        )
        render_saved_report_page()
        st.divider()
        st.caption(
            f"VastuAI Professional v{__version__} · "
            "Belief-based guidance only."
        )
        return

    menu_options = [
        "New assessment",
        "Results",
        "Saved portfolio",
        "Compare properties",
        "Dashboard",
    ]
    if st.session_state.get("active_page") not in menu_options:
        st.session_state.active_page = "New assessment"
    if st.session_state.get("professional_menu") != st.session_state.active_page:
        st.session_state.professional_menu = st.session_state.active_page

    st.markdown(
        '<div class="hero"><h1>🧭 VastuAI Professional</h1>'
        '<p>Assess, manage and compare properties in the active platform project.</p></div>',
        unsafe_allow_html=True,
    )

    def change_professional_page() -> None:
        st.session_state.active_page = st.session_state.professional_menu

    menu_col, action_col = st.columns([4, 1])
    with menu_col:
        st.radio(
            "Professional workflow",
            menu_options,
            horizontal=True,
            key="professional_menu",
            on_change=change_professional_page,
        )
    with action_col:
        if st.button(
            "➕ New record",
            type="primary",
            use_container_width=True,
            key="professional_new_record",
        ):
            start_new_record()
            st.rerun()

    notice = st.session_state.pop("assessment_notice", None)
    if notice:
        if notice.startswith("Assessment completed, but"):
            st.warning(notice)
        else:
            st.success(notice)

    with st.expander("Important notice"):
        st.info(
            "This application provides belief-based Vastu and numerology guidance. "
            "It is not a substitute for structural inspection, legal due diligence, "
            "financial advice or property valuation."
        )

    page = st.session_state.active_page
    if page == "New assessment":
        if st.session_state.get("editing_analysis_id"):
            st.warning(
                f"Edit mode: P{st.session_state.editing_analysis_id}. "
                "Submitting updates this record."
            )
        render_workflow_steps()
        st.divider()
        mode = st.radio(
            "Property input method",
            ["Enter details manually", "Upload floor plan"],
            horizontal=True,
            key="input_mode",
            on_change=reset_analysis,
        )
        render_manual_form() if mode == "Enter details manually" else render_layout_upload()
    elif page == "Results":
        if st.session_state.analysis_complete and st.session_state.analysis_result:
            render_results(
                st.session_state.analysis_result,
                st.session_state.last_payload or {},
            )
        else:
            st.info("No assessment loaded. Create one or load a saved record.")
    elif page == "Saved portfolio":
        render_portfolio()
    elif page == "Compare properties":
        render_comparison()
    elif page == "Dashboard":
        render_dashboard()

    if OPENAI.configured:
        st.success(
            f"OpenAI vision enabled · {OPENAI.models.vision_model}",
            icon="✅",
        )
    else:
        health = OPENAI.health()
        st.warning(
            "OPENAI_API_KEY is not available to the running deployment. "
            "Check the Render service Environment variable named exactly OPENAI_API_KEY."
        )
        st.caption(
            f"Runtime environment detected: {'Yes' if health.get('runtime_env_present') else 'No'} · "
            f"Streamlit secret detected: {'Yes' if health.get('streamlit_secret_present') else 'No'}"
        )

    st.divider()
    st.caption(
        f"VastuAI Professional v{__version__} · Belief-based guidance only · "
        "Always complete structural, legal, safety and financial due diligence."
    )



def render(project_id: int) -> None:
    """Backward-compatible entry point for the complete Professional workspace."""
    render_section(project_id, requested_section=None)
