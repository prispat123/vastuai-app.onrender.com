from pathlib import Path
import sqlite3

from platform_core.config import CONFIG
from platform_core.database import initialize_database
from knowledge_engine.importer import ensure_seeded, runtime_status

ROOT = Path(__file__).parents[1]


def test_knowledge_service_has_no_import_time_repository():
    source = (ROOT / "project_intelligence" / "knowledge_service.py").read_text(encoding="utf-8")
    assert "REPOSITORY = repository()" not in source
    assert "ENGINE = KnowledgeEngine(REPOSITORY)" not in source


def test_runtime_status_initializes_schema():
    # The test database starts without Knowledge rows. runtime_status must apply
    # additive DDL before querying knowledge_meta.
    status = runtime_status()
    assert "counts" in status
    assert set(status["counts"]) == {"rules", "recommendations", "profiles", "links"}


def test_ensure_seeded_imports_master_after_schema_creation():
    status = ensure_seeded()
    assert status["seeded"] is True
    assert status["counts"]["rules"] >= 81


def test_initialization_is_additive():
    initialize_database()
    # The projects table and Knowledge tables coexist in the same DB.
    connection = sqlite3.connect(CONFIG.db_path)
    names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    connection.close()
    assert "projects" in names
    assert "knowledge_meta" in names
    assert "knowledge_rules" in names
