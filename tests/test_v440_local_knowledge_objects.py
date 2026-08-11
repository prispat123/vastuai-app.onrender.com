import json
from pathlib import Path

from knowledge_engine.importer import (
    export_runtime_bundle,
    import_json_master,
    runtime_status,
)
from knowledge_engine.repository import KnowledgeRepository
from platform_core.database import initialize_database

ROOT = Path(__file__).parents[1]


def test_json_master_imports_to_sqlite():
    initialize_database()
    result = import_json_master()
    assert result["rules_imported"] >= 81
    assert result["recommendations_imported"] >= 10
    assert result["profiles_imported"] == 4
    assert result["links_imported"] > 0

    status = runtime_status()
    assert status["seeded"] is True
    assert status["counts"]["rules"] >= 81


def test_repository_reads_runtime_database():
    initialize_database()
    import_json_master()
    repository = KnowledgeRepository()
    rules = repository.filter_rules(category="Kitchen")
    assert len(rules) == 9
    assert all(rule["category"] == "Kitchen" for rule in rules)
    assert repository.validate() == []


def test_relationships_are_queryable():
    initialize_database()
    import_json_master()
    repository = KnowledgeRepository()
    concern = next(
        rule
        for rule in repository.rules()
        if rule["category"] == "Kitchen"
        and rule["polarity"] == "negative"
    )
    related = repository.related_rules(concern["rule_id"])
    assert related
    assert any(
        item["relationship"] == "preferred_alternative"
        for item in related
    )


def test_runtime_backup_contains_knowledge_objects():
    initialize_database()
    import_json_master()
    bundle = export_runtime_bundle()
    assert bundle["rules"]
    assert bundle["recommendations"]
    assert bundle["profiles"]
    assert bundle["links"]


def test_ui_exposes_local_management():
    source = (
        ROOT / "ui_pages" / "knowledge_components.py"
    ).read_text(encoding="utf-8")
    assert "Validate and Refresh from JSON Master" in source
    assert "Export Local Knowledge Backup" in source
    assert "Storage: local SQLite" in source
    assert "Related Knowledge Objects" in source


def test_evaluator_no_longer_reads_json_runtime():
    source = (
        ROOT / "knowledge_engine" / "repository.py"
    ).read_text(encoding="utf-8")
    assert "FROM knowledge_rules" in source
    assert "glob(" not in source
