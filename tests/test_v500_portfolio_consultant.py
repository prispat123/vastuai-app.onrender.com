import json
import uuid
from pathlib import Path

from platform_core.database import initialize_database, transaction
from professional_app.services import buyer_workspace_service, portfolio_consultant_service

ROOT = Path(__file__).parents[1]


def test_navigation_contains_portfolio_consultant():
    detail = (ROOT / "ui_pages" / "project_detail.py").read_text(encoding="utf-8")
    ui = (ROOT / "professional_app" / "ui.py").read_text(encoding="utf-8")
    assert '"AI Portfolio Consultant"' in detail
    assert 'requested_section == "AI Portfolio Consultant"' in ui
    assert "render_portfolio_consultant_page" in ui


def test_version_is_v5_series():
    version = (ROOT / "professional_app" / "version.py").read_text(encoding="utf-8")
    assert '5.' in version


def test_portfolio_ranking_preserves_overall_score_and_tiebreakers():
    initialize_database()
    token = uuid.uuid4().hex[:8]
    name = f"Buyer V500 {token}"
    key = buyer_workspace_service.normalized_buyer_key(name, "1985-02-03")

    analysis_base = 900_000_000 + int(token, 16) % 10_000_000

    with transaction() as c:
        buyer = c.execute(
            """INSERT INTO buyers(buyer_uuid,buyer_name,date_of_birth,normalized_key)
               VALUES(?,?,?,?)""",
            (f"buyer-{token}", name, "1985-02-03", key),
        )
        buyer_id = int(buyer.lastrowid)
        specs = [
            ("A", 8.7, 8.4, 90.0, 1),
            ("B", 8.7, 8.6, 88.0, 0),
            ("C", 8.5, 9.1, 79.0, 0),
        ]
        pdp_ids = []
        for i, (label, overall, vastu, num, critical) in enumerate(specs, 1):
            project = c.execute(
                """INSERT INTO projects(project_uuid,name,workspace_type,client_or_builder,
                   city,description,status,project_folder) VALUES(?,?,?,?,?,?,?,?)""",
                (f"project-{token}-{i}", f"Project {label} {token}", "Professional", name,
                 "Chennai", "", "Active", f"Project_{token}_{i}"),
            )
            profile = {
                "buyer": {"owner_name": name, "date_of_birth": "1985-02-03"},
                "property": {"property_name": f"Home {label}", "property_number": str(i)},
                "overall_professional": {"score": overall, "rating": "Excellent"},
                "vastu": {"score": vastu, "critical_high_count": critical,
                          "strengths": [f"Strength {label}"], "cautions": [f"Concern {label}"]},
                "numerology": {"score_100": num},
                "recommendation": {"decision": "Generally suitable"},
            }
            pdp = c.execute(
                """INSERT INTO property_decision_profiles(decision_id,project_id,analysis_id,
                   owner_name,property_name,property_number,source_hash,overall_score,
                   overall_rating,profile_json,buyer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (f"PDP-{token}-{label}", int(project.lastrowid), analysis_base + i, name, f"Home {label}", str(i),
                 f"hash-{token}-{label}", overall, "Excellent", json.dumps(profile), buyer_id),
            )
            pdp_ids.append(int(pdp.lastrowid))

    for pdp_id in pdp_ids:
        buyer_workspace_service.add_to_shortlist(buyer_id, pdp_id)

    result = portfolio_consultant_service.analyse_shortlist(buyer_id)
    assert result["shortlist_count"] == 3
    # A and B share the same immutable overall score; B wins because it has fewer critical/high issues.
    assert result["ranked"][0]["property_name"] == "Home B"
    assert result["best_overall"]["property_name"] == "Home B"
    assert result["best_vastu"]["property_name"] == "Home C"
    assert result["best_numerology"]["property_name"] == "Home A"
    assert result["ranked"][0]["strengths"] == ["Strength B"]
    assert "does not" not in result["ranking_basis"].lower() or "recalculated" in result["ranking_basis"].lower()


def test_empty_portfolio_is_safe():
    initialize_database()
    token = uuid.uuid4().hex[:8]
    name = f"Buyer Empty V500 {token}"
    key = buyer_workspace_service.normalized_buyer_key(name, "")
    with transaction() as c:
        row = c.execute(
            "INSERT INTO buyers(buyer_uuid,buyer_name,date_of_birth,normalized_key) VALUES(?,?,?,?)",
            (f"buyer-empty-{token}", name, "", key),
        )
        buyer_id = int(row.lastrowid)
    result = portfolio_consultant_service.analyse_shortlist(buyer_id)
    assert result["shortlist_count"] == 0
    assert result["ranked"] == []
