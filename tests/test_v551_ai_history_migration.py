from __future__ import annotations

import sqlite3

from platform_core import database


def test_ai_history_mode_runtime_migration(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.sqlite3"
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript("""
    CREATE TABLE property_decision_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE professional_ai_consultant_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        analysis_id INTEGER NOT NULL,
        model_name TEXT NOT NULL,
        source_hash TEXT NOT NULL,
        question_text TEXT NOT NULL,
        answer_text TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL,
        error_text TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    database._ensure_runtime_migrations(con)
    columns = {row[1] for row in con.execute("PRAGMA table_info(professional_ai_consultant_history)")}
    assert "mode" in columns
    con.close()

def test_builder_is_user_facing_label():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert 'Open Builder' in (root / 'ui_pages' / 'home.py').read_text(encoding='utf-8')
    assert 'else "Builder"' in (root / 'ui_pages' / 'projects.py').read_text(encoding='utf-8')
