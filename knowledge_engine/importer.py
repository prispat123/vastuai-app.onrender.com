from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from knowledge_engine.json_source import JsonKnowledgeSource
from knowledge_engine.validation import validate_bundle
from platform_core.database import connect, transaction, initialize_database


class KnowledgeImportError(RuntimeError):
    pass


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def import_json_master(
    source: JsonKnowledgeSource | None = None,
    *,
    deactivate_missing: bool = True,
) -> dict:
    initialize_database()
    source = source or JsonKnowledgeSource()
    bundle = source.bundle()
    errors = validate_bundle(bundle)
    manifest = bundle["manifest"]
    source_hash = source.source_hash()

    with transaction() as connection:
        cursor = connection.execute(
            """
            INSERT INTO knowledge_import_runs(
                knowledge_version,schema_version,source_hash,status,
                validation_json
            ) VALUES(?,?,?,?,?)
            """,
            (
                manifest["knowledge_version"],
                int(manifest["schema_version"]),
                source_hash,
                "Validation Failed" if errors else "Processing",
                _json(errors),
            ),
        )
        run_id = int(cursor.lastrowid)

    if errors:
        with transaction() as connection:
            connection.execute(
                """
                UPDATE knowledge_import_runs
                SET completed_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (run_id,),
            )
        raise KnowledgeImportError("\n".join(errors))

    rule_ids = {rule["rule_id"] for rule in bundle["rules"]}
    rec_ids = {
        recommendation["recommendation_id"]
        for recommendation in bundle["recommendations"]
    }
    profile_keys = set(bundle["profiles"])

    with transaction() as connection:
        for profile_key, profile in bundle["profiles"].items():
            connection.execute(
                """
                INSERT INTO knowledge_profiles(
                    profile_key,name,description,disclaimer,active,
                    version,source_json
                ) VALUES(?,?,?,?,1,?,?)
                ON CONFLICT(profile_key) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    disclaimer=excluded.disclaimer,
                    active=1,
                    version=excluded.version,
                    source_json=excluded.source_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    profile_key,
                    profile.get("name", profile_key),
                    profile.get("description", ""),
                    profile.get("disclaimer", ""),
                    manifest["knowledge_version"],
                    _json(profile),
                ),
            )

        for recommendation in bundle["recommendations"]:
            connection.execute(
                """
                INSERT INTO knowledge_recommendations(
                    recommendation_id,title,stage,effort,category,
                    actions_json,limitations_json,version,active,source_json
                ) VALUES(?,?,?,?,?,?,?,?,1,?)
                ON CONFLICT(recommendation_id) DO UPDATE SET
                    title=excluded.title,
                    stage=excluded.stage,
                    effort=excluded.effort,
                    category=excluded.category,
                    actions_json=excluded.actions_json,
                    limitations_json=excluded.limitations_json,
                    version=excluded.version,
                    active=1,
                    source_json=excluded.source_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    recommendation["recommendation_id"],
                    recommendation.get("title", ""),
                    recommendation.get("stage", ""),
                    recommendation.get("effort", ""),
                    recommendation.get("category", ""),
                    _json(recommendation.get("actions", [])),
                    _json(recommendation.get("limitations", [])),
                    manifest["knowledge_version"],
                    _json(recommendation),
                ),
            )

        for rule in bundle["rules"]:
            connection.execute(
                """
                INSERT INTO knowledge_rules(
                    rule_id,title,category,field,direction,polarity,
                    severity,score_delta,knowledge_confidence,
                    explanation,practical_impact,architectural_note,
                    existing_home_note,builder_note,source_type,source_note,
                    tags_json,profile_weights_json,version,active,source_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)
                ON CONFLICT(rule_id) DO UPDATE SET
                    title=excluded.title,
                    category=excluded.category,
                    field=excluded.field,
                    direction=excluded.direction,
                    polarity=excluded.polarity,
                    severity=excluded.severity,
                    score_delta=excluded.score_delta,
                    knowledge_confidence=excluded.knowledge_confidence,
                    explanation=excluded.explanation,
                    practical_impact=excluded.practical_impact,
                    architectural_note=excluded.architectural_note,
                    existing_home_note=excluded.existing_home_note,
                    builder_note=excluded.builder_note,
                    source_type=excluded.source_type,
                    source_note=excluded.source_note,
                    tags_json=excluded.tags_json,
                    profile_weights_json=excluded.profile_weights_json,
                    version=excluded.version,
                    active=1,
                    source_json=excluded.source_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    rule["rule_id"],
                    rule.get("title", ""),
                    rule.get("category", ""),
                    rule.get("field", ""),
                    rule.get("direction", ""),
                    rule.get("polarity", "neutral"),
                    rule.get("severity", "Low"),
                    float(rule.get("score_delta", 0)),
                    float(rule.get("knowledge_confidence", 0)),
                    rule.get("explanation", ""),
                    rule.get("practical_impact", ""),
                    rule.get("architectural_note", ""),
                    rule.get("existing_home_note", ""),
                    rule.get("builder_note", ""),
                    rule.get("source_type", ""),
                    rule.get("source_note", ""),
                    _json(rule.get("tags", [])),
                    _json(rule.get("profile_weights", {})),
                    manifest["knowledge_version"],
                    _json(rule),
                ),
            )

        connection.execute("DELETE FROM knowledge_rule_recommendations")
        for rule in bundle["rules"]:
            for sequence, rec_id in enumerate(
                rule.get("recommendation_ids", []),
                start=1,
            ):
                connection.execute(
                    """
                    INSERT INTO knowledge_rule_recommendations(
                        rule_id,recommendation_id,sequence_no
                    ) VALUES(?,?,?)
                    """,
                    (rule["rule_id"], rec_id, sequence),
                )

        connection.execute("DELETE FROM knowledge_rule_links")
        for link in bundle["links"]:
            connection.execute(
                """
                INSERT OR IGNORE INTO knowledge_rule_links(
                    source_rule_id,target_rule_id,relationship,note
                ) VALUES(?,?,?,?)
                """,
                (
                    link["source_rule_id"],
                    link["target_rule_id"],
                    link.get("relationship", "related"),
                    link.get("note", ""),
                ),
            )

        if deactivate_missing:
            if rule_ids:
                placeholders = ",".join("?" for _ in rule_ids)
                connection.execute(
                    f"""
                    UPDATE knowledge_rules SET active=0
                    WHERE rule_id NOT IN ({placeholders})
                    """,
                    tuple(sorted(rule_ids)),
                )
            if rec_ids:
                placeholders = ",".join("?" for _ in rec_ids)
                connection.execute(
                    f"""
                    UPDATE knowledge_recommendations SET active=0
                    WHERE recommendation_id NOT IN ({placeholders})
                    """,
                    tuple(sorted(rec_ids)),
                )
            if profile_keys:
                placeholders = ",".join("?" for _ in profile_keys)
                connection.execute(
                    f"""
                    UPDATE knowledge_profiles SET active=0
                    WHERE profile_key NOT IN ({placeholders})
                    """,
                    tuple(sorted(profile_keys)),
                )

        connection.execute(
            """
            INSERT INTO knowledge_meta(
                id,knowledge_version,schema_version,source_hash,imported_at
            ) VALUES(1,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                knowledge_version=excluded.knowledge_version,
                schema_version=excluded.schema_version,
                source_hash=excluded.source_hash,
                imported_at=CURRENT_TIMESTAMP
            """,
            (
                manifest["knowledge_version"],
                int(manifest["schema_version"]),
                source_hash,
            ),
        )

        connection.execute(
            """
            UPDATE knowledge_import_runs SET
                status='Completed',
                rules_imported=?,
                recommendations_imported=?,
                profiles_imported=?,
                links_imported=?,
                completed_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                len(bundle["rules"]),
                len(bundle["recommendations"]),
                len(bundle["profiles"]),
                len(bundle["links"]),
                run_id,
            ),
        )

    return {
        "run_id": run_id,
        "knowledge_version": manifest["knowledge_version"],
        "schema_version": manifest["schema_version"],
        "source_hash": source_hash,
        "rules_imported": len(bundle["rules"]),
        "recommendations_imported": len(bundle["recommendations"]),
        "profiles_imported": len(bundle["profiles"]),
        "links_imported": len(bundle["links"]),
        "validation_errors": [],
    }


def runtime_status() -> dict:
    # Existing user databases predate the Knowledge Object tables. Ensure the
    # current additive DDL is applied before querying status. CREATE TABLE IF
    # NOT EXISTS preserves all existing project and analysis records.
    initialize_database()
    with connect() as connection:
        meta = connection.execute(
            "SELECT * FROM knowledge_meta WHERE id=1"
        ).fetchone()
        counts = {
            "rules": connection.execute(
                "SELECT COUNT(*) value FROM knowledge_rules WHERE active=1"
            ).fetchone()["value"],
            "recommendations": connection.execute(
                """
                SELECT COUNT(*) value
                FROM knowledge_recommendations WHERE active=1
                """
            ).fetchone()["value"],
            "profiles": connection.execute(
                "SELECT COUNT(*) value FROM knowledge_profiles WHERE active=1"
            ).fetchone()["value"],
            "links": connection.execute(
                "SELECT COUNT(*) value FROM knowledge_rule_links"
            ).fetchone()["value"],
        }
        last_run = connection.execute(
            """
            SELECT * FROM knowledge_import_runs
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()

    return {
        "seeded": counts["rules"] > 0,
        "meta": dict(meta) if meta else None,
        "counts": counts,
        "last_run": dict(last_run) if last_run else None,
    }


def ensure_seeded() -> dict:
    """Keep the runtime Knowledge DB aligned with the bundled JSON master.

    Existing databases may already contain an older rule set. Merely checking
    that some rules exist is insufficient; compare source hash, version and
    active rule count so newly added VK objects are imported automatically.
    """
    source = JsonKnowledgeSource()
    bundle = source.bundle()
    expected_hash = source.source_hash()
    expected_version = bundle["manifest"]["knowledge_version"]
    expected_rules = len(bundle["rules"])

    status = runtime_status()
    meta = status.get("meta") or {}
    is_current = (
        status["seeded"]
        and meta.get("source_hash") == expected_hash
        and meta.get("knowledge_version") == expected_version
        and int(status["counts"].get("rules", 0)) == expected_rules
    )
    if is_current:
        return status

    import_json_master(source)
    refreshed = runtime_status()
    refreshed["refreshed"] = True
    return refreshed


def export_runtime_bundle() -> dict:
    ensure_seeded()
    with connect() as connection:
        meta = connection.execute(
            "SELECT * FROM knowledge_meta WHERE id=1"
        ).fetchone()
        profiles = connection.execute(
            """
            SELECT * FROM knowledge_profiles
            ORDER BY profile_key
            """
        ).fetchall()
        rules = connection.execute(
            "SELECT * FROM knowledge_rules ORDER BY rule_id"
        ).fetchall()
        recommendations = connection.execute(
            """
            SELECT * FROM knowledge_recommendations
            ORDER BY recommendation_id
            """
        ).fetchall()
        rule_recs = connection.execute(
            """
            SELECT * FROM knowledge_rule_recommendations
            ORDER BY rule_id,sequence_no
            """
        ).fetchall()
        links = connection.execute(
            """
            SELECT source_rule_id,target_rule_id,relationship,note
            FROM knowledge_rule_links
            ORDER BY source_rule_id,target_rule_id,relationship
            """
        ).fetchall()

    recommendation_ids: dict[str, list[str]] = {}
    for row in rule_recs:
        recommendation_ids.setdefault(row["rule_id"], []).append(
            row["recommendation_id"]
        )

    rule_rows = []
    for row in rules:
        item = json.loads(row["source_json"] or "{}")
        item["active"] = bool(row["active"])
        item["version"] = row["version"]
        item["recommendation_ids"] = recommendation_ids.get(
            row["rule_id"],
            [],
        )
        rule_rows.append(item)

    recommendation_rows = []
    for row in recommendations:
        item = json.loads(row["source_json"] or "{}")
        item["active"] = bool(row["active"])
        item["version"] = row["version"]
        recommendation_rows.append(item)

    profile_rows = {}
    for row in profiles:
        item = json.loads(row["source_json"] or "{}")
        item["active"] = bool(row["active"])
        item["version"] = row["version"]
        profile_rows[row["profile_key"]] = item

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "runtime_meta": dict(meta) if meta else {},
        "profiles": profile_rows,
        "rules": rule_rows,
        "recommendations": recommendation_rows,
        "links": [dict(row) for row in links],
    }


def export_runtime_json_bytes() -> bytes:
    return json.dumps(
        export_runtime_bundle(),
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")
