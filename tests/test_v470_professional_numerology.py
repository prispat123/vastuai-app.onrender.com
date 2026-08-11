from datetime import date
from pathlib import Path

from numerology_engine.calculations import (
    birth_number,
    life_path_number,
    property_number,
    reduce_number,
)

ROOT = Path(__file__).parents[1]


def test_number_reduction_preserves_master_numbers():
    assert reduce_number(29) == 11
    assert reduce_number(38) == 11
    assert reduce_number(22) == 22
    assert reduce_number(33) == 33
    assert reduce_number(19) == 1


def test_core_numbers_are_deterministic():
    dob = date(1984, 7, 29)
    assert birth_number(dob) == 11
    assert isinstance(life_path_number(dob), int)
    assert property_number("Tower 6 / Flat 1205") == 5


def test_numerology_schema_is_individual_project_scoped():
    source = (
        ROOT / "platform_core" / "database.py"
    ).read_text(encoding="utf-8")
    assert "professional_numerology_profiles" in source
    assert "professional_numerology_assessments" in source
    assert "project_id INTEGER PRIMARY KEY" in source


def test_numerology_ui_is_professional_only():
    source = (
        ROOT / "ui_pages" / "project_detail.py"
    ).read_text(encoding="utf-8")
    assert 'workspace == "Professional" and section == "Numerology"' in source
    assert "professional_numerology.render(project)" in source


def test_ui_states_scope_and_independence():
    source = (
        ROOT / "ui_pages" / "professional_numerology.py"
    ).read_text(encoding="utf-8")
    assert "Individual-property assessment" in source
    assert "does not assess a tower, building or project" in source
    assert "Do not average or directly compare" in source


def test_local_knowledge_objects_exist():
    data = __import__("json").loads(
        (
            ROOT / "numerology_knowledge" / "objects.json"
        ).read_text(encoding="utf-8")
    )
    assert len(data["objects"]) >= 31
    ids = {row["object_id"] for row in data["objects"]}
    assert "NUM-ALIGN-EXACT-BIRTH" in ids
    assert "NUM-ALIGN-EXACT-LIFE" in ids


def test_independent_pdf_report_exists():
    source = (
        ROOT / "professional_numerology" / "report_service.py"
    ).read_text(encoding="utf-8")
    assert "Professional Numerology Assessment" in source
    assert "independent of the Vastu" in source
    assert "SimpleDocTemplate" in source


def test_expansion_policy_preserves_boundaries():
    source = (
        ROOT / "architecture" / "KNOWLEDGE_ENGINE_EXPANSION.md"
    ).read_text(encoding="utf-8")
    assert "living, versioned expert systems" in source
    assert "does not independently assess towers" in source
    assert "must not be averaged" in source
