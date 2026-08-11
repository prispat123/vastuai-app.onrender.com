from pathlib import Path
ROOT=Path(__file__).parents[1]

def test_pdp_uses_canonical_snapshot():
    s=(ROOT/'professional_app/services/pdp_service.py').read_text(encoding='utf-8')
    assert 'from assessment_core import build_snapshot' in s
    assert 'snapshot = build_snapshot(' in s
    assert 'CURRENT_SCHEMA_VERSION = 3' in s
    assert 'enrich_existing_profiles' in s

def test_ui_fixed_and_executive():
    s=(ROOT/'professional_app/ui.py').read_text(encoding='utf-8')
    assert 'import json' in s
    for label in ('Property Decision Profile','Professional Vastu','Professional Numerology','Assessment provenance','VK IDs:','NUM IDs:'):
        assert label in s
