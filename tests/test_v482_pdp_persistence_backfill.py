import json
from pathlib import Path

from platform_core.database import connect, transaction
from professional_app.services.history_service import save_analysis, set_active_project, update_analysis
from professional_app.services import pdp_service

ROOT = Path(__file__).parents[1]


def _make_project(uuid: str = "pdp-auto") -> int:
    with transaction() as connection:
        cursor = connection.execute(
            """INSERT INTO projects(
                project_uuid,name,workspace_type,client_or_builder,
                city,description,status,project_folder
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (uuid, "PDP Auto", "Professional", "Buyer", "Chennai", "", "Active", uuid),
        )
        return int(cursor.lastrowid)


def _payload():
    return {
        "owner_name": "Buyer A",
        "dob": "1990-01-01",
        "property_name": "House A",
        "flat_number": "101",
        "assessment_year": 2026,
    }


def _result(score: float = 8.0):
    return {
        "vastu_result": {
            "score": score,
            "grade": "A",
            "coverage": 80,
            "details": [],
            "knowledge_findings": [{"rule_id": "VK-003"}],
        },
        "numerology_result": {
            "score": 8.0,
            "score_100": 80.0,
            "grade": "Very Good",
            "knowledge_ids": ["NUM-PROPERTY_NUMBER-01"],
        },
        "final_result": {
            "score": score,
            "score_100": score * 10,
            "rating": "Good",
            "basis": "Equal-weight Vastu and Numerology",
            "weights": {"vastu": 0.5, "numerology": 0.5},
        },
        "recommendation_result": {
            "decision": "Generally suitable",
            "confidence": "High",
            "actions": [],
        },
    }


def test_save_analysis_automatically_creates_pdp():
    project_id = _make_project("pdp-auto-save")
    set_active_project(project_id)
    analysis_id = save_analysis(_payload(), _result())
    pdp = pdp_service.latest_for_analysis(analysis_id)
    assert pdp is not None
    assert pdp["decision_id"].startswith("PDP-")
    assert pdp["profile"]["audit"]["creation_path"] == "automatic_persistence"


def test_update_analysis_creates_new_immutable_pdp_version():
    project_id = _make_project("pdp-auto-update")
    set_active_project(project_id)
    analysis_id = save_analysis(_payload(), _result(8.0))
    before = pdp_service.list_profiles(project_id)
    update_analysis(analysis_id, _payload(), _result(8.5))
    after = pdp_service.list_profiles(project_id)
    assert len(after) == len(before) + 1
    assert after[0]["analysis_id"] == analysis_id


def test_backfill_creates_pdp_for_historical_analysis():
    project_id = _make_project("pdp-backfill")
    payload = _payload()
    result = _result()
    with transaction() as connection:
        cursor = connection.execute(
            """INSERT INTO professional_analyses(
                project_id,property_label,owner_name,flat_number,
                overall_score,vastu_score,numerology_score,confidence,
                payload_json,result_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                project_id,"House A","Buyer A","101",8.0,8.0,8.0,"High",
                json.dumps(payload),json.dumps(result),
            ),
        )
        analysis_id = int(cursor.lastrowid)
    assert pdp_service.latest_for_analysis(analysis_id) is None
    backfill = pdp_service.backfill_missing_profiles(project_id)
    assert backfill["created_count"] == 1
    assert pdp_service.latest_for_analysis(analysis_id) is not None


def test_ui_no_longer_owns_pdp_creation():
    source = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert "pdp_service.create_profile(" not in source
    assert "backfill_missing_profiles" in source


def test_history_service_owns_pdp_persistence():
    source = (ROOT / "professional_app" / "services" / "history_service.py").read_text(encoding="utf-8")
    assert source.count("pdp_service.create_profile(") >= 2
