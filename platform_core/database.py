from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from platform_core.config import CONFIG

SCHEMA_VERSION = 3

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    schema_version INTEGER NOT NULL,
    upgraded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_uuid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    workspace_type TEXT NOT NULL CHECK(workspace_type IN ('Professional','Builder')),
    client_or_builder TEXT,
    city TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'Active',
    project_folder TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS project_intelligence_details (
    project_id INTEGER PRIMARY KEY,
    project_type TEXT NOT NULL DEFAULT 'Apartment',
    state TEXT DEFAULT '',
    country TEXT DEFAULT 'India',
    north_reference TEXT DEFAULT 'Auto-detect',
    number_of_towers INTEGER DEFAULT 0,
    remarks TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS project_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_uuid TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    display_name TEXT NOT NULL,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_documents_project
ON project_documents(project_id, category, uploaded_at DESC);

CREATE TABLE IF NOT EXISTS project_layouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    layout_uuid TEXT NOT NULL UNIQUE,
    tower TEXT DEFAULT '',
    flat_number TEXT DEFAULT '',
    layout_type TEXT DEFAULT '',
    floor TEXT DEFAULT '',
    drawing_path TEXT DEFAULT '',
    source_document_id INTEGER,
    analysis_status TEXT NOT NULL DEFAULT 'Not Started',
    overall_score REAL,
    confidence REAL,
    last_analysis_at TEXT,
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(source_document_id) REFERENCES project_documents(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_project_layouts_project
ON project_layouts(project_id, analysis_status, tower, floor, flat_number);


CREATE TABLE IF NOT EXISTS project_document_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_id INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    image_hash TEXT NOT NULL,
    classification TEXT NOT NULL DEFAULT 'Unreviewed',
    is_floor_plan INTEGER NOT NULL DEFAULT 0,
    north_detected INTEGER NOT NULL DEFAULT 0,
    north_confidence REAL NOT NULL DEFAULT 0,
    north_description TEXT DEFAULT '',
    extracted_json_path TEXT DEFAULT '',
    extraction_status TEXT NOT NULL DEFAULT 'Not Processed',
    review_notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, page_number),
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(document_id) REFERENCES project_documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_document_pages_project
ON project_document_pages(project_id, classification, extraction_status);

CREATE TABLE IF NOT EXISTS layout_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    layout_id INTEGER,
    page_id INTEGER,
    source_hash TEXT NOT NULL,
    north_direction TEXT DEFAULT 'Unknown',
    entrance_direction TEXT DEFAULT 'Unknown',
    rooms_json TEXT NOT NULL DEFAULT '{}',
    vision_confidence REAL NOT NULL DEFAULT 0,
    model_name TEXT DEFAULT '',
    raw_json_path TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(layout_id) REFERENCES project_layouts(id) ON DELETE SET NULL,
    FOREIGN KEY(page_id) REFERENCES project_document_pages(id) ON DELETE SET NULL
);



CREATE TABLE IF NOT EXISTS document_batch_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
 document_id INTEGER NOT NULL, run_uuid TEXT NOT NULL UNIQUE,
 run_type TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Queued',
 total_pages INTEGER NOT NULL DEFAULT 0, processed_pages INTEGER NOT NULL DEFAULT 0,
 floor_plan_pages INTEGER NOT NULL DEFAULT 0, layouts_created INTEGER NOT NULL DEFAULT 0,
 needs_review INTEGER NOT NULL DEFAULT 0, skipped_pages INTEGER NOT NULL DEFAULT 0,
 error_message TEXT DEFAULT '', started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 completed_at TEXT,
 FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
 FOREIGN KEY(document_id) REFERENCES project_documents(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS layout_fingerprints (
 id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
 layout_id INTEGER NOT NULL, perceptual_hash TEXT NOT NULL,
 source_hash TEXT NOT NULL, canonical_layout_id INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(project_id, perceptual_hash),
 FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
 FOREIGN KEY(layout_id) REFERENCES project_layouts(id) ON DELETE CASCADE,
 FOREIGN KEY(canonical_layout_id) REFERENCES project_layouts(id) ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS project_layout_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    layout_id INTEGER NOT NULL,
    analysis_version TEXT NOT NULL DEFAULT 'VSS-1.0',
    source_extraction_id INTEGER,
    vastu_score REAL NOT NULL DEFAULT 0,
    overall_score REAL NOT NULL DEFAULT 0,
    confidence_label TEXT DEFAULT 'Insufficient',
    confidence_value REAL NOT NULL DEFAULT 0,
    grade TEXT DEFAULT '',
    status TEXT DEFAULT '',
    strengths_json TEXT NOT NULL DEFAULT '[]',
    cautions_json TEXT NOT NULL DEFAULT '[]',
    findings_json TEXT NOT NULL DEFAULT '[]',
    recommendations_json TEXT NOT NULL DEFAULT '[]',
    result_json_path TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(layout_id, analysis_version),
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(layout_id) REFERENCES project_layouts(id) ON DELETE CASCADE,
    FOREIGN KEY(source_extraction_id) REFERENCES layout_extractions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_project_layout_analysis_project
ON project_layout_analyses(project_id, overall_score DESC);

CREATE TABLE IF NOT EXISTS project_analysis_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    analysis_version TEXT NOT NULL DEFAULT 'VSS-1.0',
    project_score REAL,
    layout_count INTEGER NOT NULL DEFAULT 0,
    analysed_count INTEGER NOT NULL DEFAULT 0,
    needs_review_count INTEGER NOT NULL DEFAULT 0,
    confidence_value REAL NOT NULL DEFAULT 0,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS layout_review_state (
 layout_id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL,
 detected_north_position TEXT DEFAULT 'Unknown', detected_north_confidence REAL DEFAULT 0,
 confirmed_north_orientation TEXT DEFAULT 'Unknown', derived_json TEXT DEFAULT '{}', reviewed_json TEXT DEFAULT '{}',
 lifecycle_status TEXT DEFAULT 'Not Analysed', review_notes TEXT DEFAULT '', updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(layout_id) REFERENCES project_layouts(id) ON DELETE CASCADE,
 FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS project_knowledge_settings (
    project_id INTEGER PRIMARY KEY,
    profile_name TEXT NOT NULL DEFAULT 'practical',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS layout_knowledge_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    layout_id INTEGER NOT NULL,
    profile_name TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(layout_id,profile_name),
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(layout_id) REFERENCES project_layouts(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS knowledge_meta (
    id INTEGER PRIMARY KEY CHECK(id=1),
    knowledge_version TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    source_hash TEXT NOT NULL DEFAULT '',
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_profiles (
    profile_key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    disclaimer TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    version TEXT NOT NULL DEFAULT '1.0.0',
    source_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_rules (
    rule_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    field TEXT NOT NULL,
    direction TEXT NOT NULL,
    polarity TEXT NOT NULL,
    severity TEXT NOT NULL,
    score_delta REAL NOT NULL DEFAULT 0,
    knowledge_confidence REAL NOT NULL DEFAULT 0,
    explanation TEXT NOT NULL DEFAULT '',
    practical_impact TEXT NOT NULL DEFAULT '',
    architectural_note TEXT NOT NULL DEFAULT '',
    existing_home_note TEXT NOT NULL DEFAULT '',
    builder_note TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT '',
    source_note TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    profile_weights_json TEXT NOT NULL DEFAULT '{}',
    version TEXT NOT NULL DEFAULT '1.0.0',
    active INTEGER NOT NULL DEFAULT 1,
    source_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_rules_search
ON knowledge_rules(active,category,field,direction,polarity,severity);

CREATE TABLE IF NOT EXISTS knowledge_recommendations (
    recommendation_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT '',
    effort TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    actions_json TEXT NOT NULL DEFAULT '[]',
    limitations_json TEXT NOT NULL DEFAULT '[]',
    version TEXT NOT NULL DEFAULT '1.0.0',
    active INTEGER NOT NULL DEFAULT 1,
    source_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_rule_recommendations (
    rule_id TEXT NOT NULL,
    recommendation_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(rule_id,recommendation_id),
    FOREIGN KEY(rule_id) REFERENCES knowledge_rules(rule_id)
        ON DELETE CASCADE,
    FOREIGN KEY(recommendation_id)
        REFERENCES knowledge_recommendations(recommendation_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_rule_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_rule_id TEXT NOT NULL,
    target_rule_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_rule_id,target_rule_id,relationship),
    FOREIGN KEY(source_rule_id) REFERENCES knowledge_rules(rule_id)
        ON DELETE CASCADE,
    FOREIGN KEY(target_rule_id) REFERENCES knowledge_rules(rule_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_rule_links_source
ON knowledge_rule_links(source_rule_id,relationship);

CREATE TABLE IF NOT EXISTS knowledge_import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_version TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    source_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    rules_imported INTEGER NOT NULL DEFAULT 0,
    recommendations_imported INTEGER NOT NULL DEFAULT 0,
    profiles_imported INTEGER NOT NULL DEFAULT 0,
    links_imported INTEGER NOT NULL DEFAULT 0,
    validation_json TEXT NOT NULL DEFAULT '[]',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);



CREATE TABLE IF NOT EXISTS gpt_settings (
    id INTEGER PRIMARY KEY CHECK(id=1),
    enabled INTEGER NOT NULL DEFAULT 1,
    model_name TEXT NOT NULL DEFAULT 'gpt-5',
    reasoning_effort TEXT NOT NULL DEFAULT 'low',
    narrative_style TEXT NOT NULL DEFAULT 'Professional',
    include_in_reports INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gpt_generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    layout_id INTEGER,
    tower_name TEXT NOT NULL DEFAULT '',
    generation_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    source_snapshot_json TEXT NOT NULL DEFAULT '{}',
    prompt_text TEXT NOT NULL DEFAULT '',
    output_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    error_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(layout_id) REFERENCES project_layouts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_gpt_generations_lookup
ON gpt_generations(project_id,generation_type,layout_id,tower_name,created_at);



CREATE TABLE IF NOT EXISTS numerology_knowledge_meta (
    id INTEGER PRIMARY KEY CHECK(id=1),
    knowledge_version TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    source_hash TEXT NOT NULL DEFAULT '',
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS numerology_knowledge_objects (
    object_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    number_value INTEGER,
    title TEXT NOT NULL,
    polarity TEXT NOT NULL DEFAULT 'contextual',
    severity TEXT NOT NULL DEFAULT 'Informational',
    score_delta REAL NOT NULL DEFAULT 0,
    confidence REAL NOT NULL DEFAULT 0,
    summary TEXT NOT NULL DEFAULT '',
    recommendation TEXT NOT NULL DEFAULT '',
    source_json TEXT NOT NULL DEFAULT '{}',
    version TEXT NOT NULL DEFAULT '1.0.0',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_numerology_objects_lookup
ON numerology_knowledge_objects(active,domain,number_value);

CREATE TABLE IF NOT EXISTS professional_numerology_profiles (
    project_id INTEGER PRIMARY KEY,
    intended_user_name TEXT NOT NULL DEFAULT '',
    date_of_birth TEXT NOT NULL DEFAULT '',
    property_identifier TEXT NOT NULL DEFAULT '',
    property_name TEXT NOT NULL DEFAULT '',
    method_profile TEXT NOT NULL DEFAULT 'foundational',
    notes TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS professional_numerology_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    analysis_id INTEGER,
    knowledge_version TEXT NOT NULL,
    method_profile TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    birth_number INTEGER,
    life_path_number INTEGER,
    property_number INTEGER,
    numerology_score REAL NOT NULL DEFAULT 0,
    grade TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0,
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(analysis_id) REFERENCES professional_analyses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_professional_numerology_project
ON professional_numerology_assessments(project_id,created_at DESC);



CREATE TABLE IF NOT EXISTS property_decision_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL UNIQUE,
    project_id INTEGER NOT NULL,
    analysis_id INTEGER NOT NULL,
    owner_name TEXT NOT NULL DEFAULT '',
    property_name TEXT NOT NULL DEFAULT '',
    property_number TEXT NOT NULL DEFAULT '',
    source_hash TEXT NOT NULL,
    overall_score REAL NOT NULL DEFAULT 0,
    overall_rating TEXT NOT NULL DEFAULT '',
    profile_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_pdp_project
ON property_decision_profiles(project_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pdp_owner
ON property_decision_profiles(owner_name,created_at DESC);

CREATE TABLE IF NOT EXISTS professional_ai_consultant_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    analysis_id INTEGER NOT NULL,
    mode TEXT NOT NULL DEFAULT 'property',
    model_name TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    error_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_uuid TEXT NOT NULL UNIQUE,
    buyer_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    normalized_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'Active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_buyers_name
ON buyers(buyer_name,date_of_birth);

CREATE TABLE IF NOT EXISTS buyer_shortlist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    pdp_id INTEGER NOT NULL,
    shortlist_order INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Shortlisted',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(buyer_id,pdp_id),
    FOREIGN KEY(buyer_id) REFERENCES buyers(id) ON DELETE CASCADE,
    FOREIGN KEY(pdp_id) REFERENCES property_decision_profiles(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_buyer_shortlist_order
ON buyer_shortlist_items(buyer_id,status,shortlist_order,id);

CREATE TABLE IF NOT EXISTS portfolio_ai_consultant_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    buyer_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    error_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY(buyer_id) REFERENCES buyers(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_portfolio_ai_history_buyer
ON portfolio_ai_consultant_history(buyer_id,id DESC);


CREATE TABLE IF NOT EXISTS project_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    details TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_timeline_project
ON project_timeline(project_id, id DESC);


CREATE TABLE IF NOT EXISTS project_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_projects_workspace
ON projects(workspace_type, updated_at DESC);

CREATE TABLE IF NOT EXISTS professional_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    property_label TEXT NOT NULL,
    owner_name TEXT,
    flat_number TEXT,
    overall_score REAL,
    vastu_score REAL,
    numerology_score REAL,
    confidence TEXT,
    payload_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    workflow_status TEXT DEFAULT 'Draft',
    tags TEXT DEFAULT '',
    consultant_notes TEXT DEFAULT '',
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_professional_analyses_project
ON professional_analyses(project_id, id DESC);
"""

def connect() -> sqlite3.Connection:
    CONFIG.db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        str(CONFIG.db_path),
        timeout=30,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection

@contextmanager
def transaction():
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def _table_columns(connection, table_name: str) -> set[str]:
    return {
        str(row["name"])
        for row in connection.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }


def _ensure_runtime_migrations(connection) -> None:
    # Backward-compatible AI Consultant audit migration. Earlier databases
    # have this table without the v5.x ``mode`` column. CREATE TABLE IF NOT
    # EXISTS cannot add columns, so repair it safely at startup.
    ai_history_columns = _table_columns(
        connection,
        "professional_ai_consultant_history",
    )
    if "mode" not in ai_history_columns:
        connection.execute(
            "ALTER TABLE professional_ai_consultant_history "
            "ADD COLUMN mode TEXT NOT NULL DEFAULT 'property'"
        )

    pdp_columns = _table_columns(
        connection,
        "property_decision_profiles",
    )
    if "buyer_id" not in pdp_columns:
        connection.execute(
            "ALTER TABLE property_decision_profiles "
            "ADD COLUMN buyer_id INTEGER"
        )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_pdp_buyer "
        "ON property_decision_profiles(buyer_id,created_at DESC)"
    )


def initialize_database() -> None:
    with transaction() as connection:
        connection.executescript(DDL)
        _ensure_runtime_migrations(connection)
        connection.execute(
            """
            INSERT INTO schema_meta(id, schema_version)
            VALUES(1, ?)
            ON CONFLICT(id) DO UPDATE SET
                schema_version=excluded.schema_version,
                upgraded_at=CURRENT_TIMESTAMP
            """,
            (SCHEMA_VERSION,),
        )
