import json
import uuid
from pathlib import Path

from platform_core.database import initialize_database, transaction
from professional_app.services import buyer_workspace_service, portfolio_chat_service

ROOT = Path(__file__).parents[1]


def _make_portfolio():
    initialize_database()
    token = uuid.uuid4().hex[:8]
    name = f"Buyer V510 {token}"
    key = buyer_workspace_service.normalized_buyer_key(name, "1984-07-11")
    analysis_base = 910_000_000 + int(token, 16) % 10_000_000
    pdp_ids = []
    with transaction() as c:
        buyer = c.execute(
            "INSERT INTO buyers(buyer_uuid,buyer_name,date_of_birth,normalized_key) VALUES(?,?,?,?)",
            (f"buyer-v510-{token}", name, "1984-07-11", key),
        )
        buyer_id = int(buyer.lastrowid)
        project_id = None
        for i, (label, overall, vastu, num) in enumerate([
            ("A", 8.8, 8.3, 92.0),
            ("B", 8.6, 9.0, 78.0),
        ], 1):
            project = c.execute(
                """INSERT INTO projects(project_uuid,name,workspace_type,client_or_builder,
                   city,description,status,project_folder) VALUES(?,?,?,?,?,?,?,?)""",
                (f"project-v510-{token}-{i}", f"Project {label} {token}", "Professional",
                 name, "Chennai", "", "Active", f"Project_v510_{token}_{i}"),
            )
            if project_id is None:
                project_id = int(project.lastrowid)
            profile = {
                "buyer": {"owner_name": name, "date_of_birth": "1984-07-11"},
                "property": {"property_name": f"Home {label}", "property_number": str(i)},
                "overall_professional": {"score": overall, "rating": "Excellent"},
                "vastu": {"score": vastu, "critical_high_count": 0,
                          "strengths": [f"Strength {label}"], "cautions": [f"Concern {label}"]},
                "numerology": {"score_100": num},
                "recommendation": {"decision": "Generally suitable"},
            }
            pdp = c.execute(
                """INSERT INTO property_decision_profiles(decision_id,project_id,analysis_id,
                   owner_name,property_name,property_number,source_hash,overall_score,
                   overall_rating,profile_json,buyer_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (f"PDP-V510-{token}-{label}", int(project.lastrowid), analysis_base + i,
                 name, f"Home {label}", str(i), f"hash-v510-{token}-{label}", overall,
                 "Excellent", json.dumps(profile), buyer_id),
            )
            pdp_ids.append(int(pdp.lastrowid))
    for pdp_id in pdp_ids:
        buyer_workspace_service.add_to_shortlist(buyer_id, pdp_id)
    return int(project_id), buyer_id


def test_version_is_v520_and_ui_contains_chat():
    assert '6.0.2' in (ROOT / 'professional_app' / 'version.py').read_text(encoding='utf-8')
    ui = (ROOT / 'professional_app' / 'ui.py').read_text(encoding='utf-8')
    assert 'AI Portfolio Consultant' in ui
    assert 'Compare two properties' in ui
    assert 'portfolio_chat_service.ask' in ui


def test_portfolio_context_is_ranked_and_hashed():
    _, buyer_id = _make_portfolio()
    context = portfolio_chat_service.portfolio_context(buyer_id)
    assert context['portfolio_shortlist_count'] == 2
    assert context['properties'][0]['overall_score'] == 8.8
    assert context['best_vastu_decision_id'].endswith('-B')
    assert len(context['source_hash']) == 64


def test_chat_is_audited_and_reuses_prior_turn(monkeypatch):
    project_id, buyer_id = _make_portfolio()
    prompts = []

    def fake_response(*, instructions, input_text, model=None):
        prompts.append(json.loads(input_text))
        assert 'Never recalculate' in instructions
        return 'Grounded portfolio answer.'

    monkeypatch.setattr(portfolio_chat_service.OPENAI, 'text_response', fake_response)
    monkeypatch.setattr(
        type(portfolio_chat_service.OPENAI),
        'models',
        property(lambda self: type('Models', (), {'default_model': 'test-model'})()),
    )

    first = portfolio_chat_service.ask(project_id, buyer_id, 'Which property ranks first?')
    second = portfolio_chat_service.ask(project_id, buyer_id, 'Why is that better than the other one?')
    assert first['answer'] == 'Grounded portfolio answer.'
    assert second['answer'] == 'Grounded portfolio answer.'
    assert prompts[1]['recent_conversation']
    assert prompts[1]['recent_conversation'][-1]['question'] == 'Which property ranks first?'

    rows = portfolio_chat_service.history(buyer_id)
    assert len(rows) >= 2
    assert rows[0]['status'] == 'Completed'
    assert rows[0]['source_hash'] == second['source_hash']


def test_two_property_scope_is_hashed_separately():
    _, buyer_id = _make_portfolio()
    full = portfolio_chat_service.portfolio_context(buyer_id)
    ids = [row['decision_id'] for row in full['properties']]
    scoped = portfolio_chat_service.portfolio_context(buyer_id, decision_ids=ids)
    assert scoped['scope'] == 'selected_properties'
    assert scoped['selected_property_count'] == 2
    assert {row['decision_id'] for row in scoped['properties']} == set(ids)
    assert scoped['strongest_selected_decision_id'] == full['properties'][0]['decision_id']
    assert scoped['source_hash'] != full['source_hash']
