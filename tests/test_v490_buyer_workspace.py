import json
import uuid
from pathlib import Path
from platform_core.database import initialize_database, transaction
from professional_app.services import buyer_workspace_service

ROOT = Path(__file__).parents[1]


def test_schema_contains_buyer_objects():
    source = (ROOT/"platform_core"/"database.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS buyers" in source
    assert "CREATE TABLE IF NOT EXISTS buyer_shortlist_items" in source
    assert "ADD COLUMN buyer_id INTEGER" in source


def test_navigation_contains_buyer_workspace():
    detail = (ROOT/"ui_pages"/"project_detail.py").read_text(encoding="utf-8")
    ui = (ROOT/"professional_app"/"ui.py").read_text(encoding="utf-8")
    assert '"Buyer Workspace"' in detail
    assert 'requested_section == "Buyer Workspace"' in ui


def test_new_pdp_links_to_buyer():
    source = (
        ROOT/"professional_app"/"services"/"pdp_service.py"
    ).read_text(encoding="utf-8")
    assert "link_pdp_to_buyer(" in source


def test_normalized_buyer_identity():
    assert buyer_workspace_service.normalized_buyer_key(
        " Buyer   V490 ",
        "1990-01-01",
    ) == "buyer v490|1990-01-01"


def test_cross_project_shortlist_and_ordering():
    initialize_database()
    token = uuid.uuid4().hex[:8]
    name = f"Buyer V490 {token}"
    key = buyer_workspace_service.normalized_buyer_key(
        name, "1990-01-01"
    )

    with transaction() as c:
        buyer = c.execute(
            """INSERT INTO buyers(
               buyer_uuid,buyer_name,date_of_birth,normalized_key)
               VALUES(?,?,?,?)""",
            (f"buyer-{token}", name, "1990-01-01", key),
        )
        buyer_id = int(buyer.lastrowid)
        pdp_ids = []
        for i in (1,2):
            project = c.execute(
                """INSERT INTO projects(
                   project_uuid,name,workspace_type,client_or_builder,
                   city,description,status,project_folder)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    f"project-{token}-{i}",
                    f"V490 Project {token} {i}",
                    "Professional",
                    name,
                    "Chennai",
                    "",
                    "Active",
                    f"Project_{token}_{i}",
                ),
            )
            project_id = int(project.lastrowid)
            profile = {
                "buyer":{"owner_name":name,"date_of_birth":"1990-01-01"},
                "property":{"property_name":f"Home {i}","property_number":str(i)},
                "overall_professional":{"score":8+i/10,"rating":"Good"},
                "vastu":{"score":8.0,"critical_high_count":0},
                "numerology":{"score_100":82.0},
                "recommendation":{"decision":"Generally suitable"},
            }
            pdp = c.execute(
                """INSERT INTO property_decision_profiles(
                   decision_id,project_id,analysis_id,owner_name,
                   property_name,property_number,source_hash,
                   overall_score,overall_rating,profile_json,buyer_id)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    f"PDP-{token}-{i}",
                    project_id,
                    i,
                    name,
                    f"Home {i}",
                    str(i),
                    f"hash-{token}-{i}",
                    8+i/10,
                    "Good",
                    json.dumps(profile),
                    buyer_id,
                ),
            )
            pdp_ids.append(int(pdp.lastrowid))

    for pdp_id in pdp_ids:
        buyer_workspace_service.add_to_shortlist(buyer_id,pdp_id)

    rows = buyer_workspace_service.list_shortlist(buyer_id)
    assert len(rows)==2
    assert len({row["project_name"] for row in rows})==2

    buyer_workspace_service.move_shortlist_item(
        buyer_id,pdp_ids[1],"up"
    )
    rows = buyer_workspace_service.list_shortlist(buyer_id)
    assert int(rows[0]["id"])==pdp_ids[1]

    buyer_workspace_service.remove_from_shortlist(
        buyer_id,pdp_ids[1]
    )
    rows = buyer_workspace_service.list_shortlist(buyer_id)
    assert len(rows)==1
    assert int(rows[0]["id"])==pdp_ids[0]
