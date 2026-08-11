from __future__ import annotations

import json
from typing import Any

from knowledge_engine.importer import ensure_seeded
from platform_core.database import connect


def _loads(value: str | None, default):
    try:
        return json.loads(value or "")
    except (TypeError, json.JSONDecodeError):
        return default


class KnowledgeRepository:
    """SQLite-backed runtime repository.

    JSON remains the editable/version-controlled master source. The importer
    seeds and refreshes these local runtime tables.
    """

    def __init__(self, *_args, **_kwargs):
        ensure_seeded()

    def rules(
        self,
        *,
        include_inactive: bool = False,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT * FROM knowledge_rules
        """
        if not include_inactive:
            query += " WHERE active=1"
        query += " ORDER BY rule_id"

        with connect() as connection:
            rows = connection.execute(query).fetchall()
            recommendation_rows = connection.execute(
                """
                SELECT rule_id,recommendation_id
                FROM knowledge_rule_recommendations
                ORDER BY rule_id,sequence_no
                """
            ).fetchall()

        rec_map: dict[str, list[str]] = {}
        for row in recommendation_rows:
            rec_map.setdefault(row["rule_id"], []).append(
                row["recommendation_id"]
            )

        result = []
        for row in rows:
            item = dict(row)
            item["tags"] = _loads(item.pop("tags_json"), [])
            item["profile_weights"] = _loads(
                item.pop("profile_weights_json"),
                {},
            )
            item["recommendation_ids"] = rec_map.get(
                item["rule_id"],
                [],
            )
            item["active"] = bool(item["active"])
            result.append(item)
        return result

    def recommendations(
        self,
        *,
        include_inactive: bool = False,
    ) -> dict[str, dict]:
        query = "SELECT * FROM knowledge_recommendations"
        if not include_inactive:
            query += " WHERE active=1"
        query += " ORDER BY recommendation_id"

        with connect() as connection:
            rows = connection.execute(query).fetchall()

        result = {}
        for row in rows:
            item = dict(row)
            item["actions"] = _loads(item.pop("actions_json"), [])
            item["limitations"] = _loads(
                item.pop("limitations_json"),
                [],
            )
            item["active"] = bool(item["active"])
            result[item["recommendation_id"]] = item
        return result

    def profiles(
        self,
        *,
        include_inactive: bool = False,
    ) -> dict[str, dict]:
        query = "SELECT * FROM knowledge_profiles"
        if not include_inactive:
            query += " WHERE active=1"
        query += " ORDER BY profile_key"

        with connect() as connection:
            rows = connection.execute(query).fetchall()

        return {
            row["profile_key"]: {
                "name": row["name"],
                "description": row["description"],
                "disclaimer": row["disclaimer"],
                "active": bool(row["active"]),
                "version": row["version"],
            }
            for row in rows
        }

    def categories(self) -> list[str]:
        with connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT category
                FROM knowledge_rules
                WHERE active=1
                ORDER BY category
                """
            ).fetchall()
        return [row["category"] for row in rows]

    def filter_rules(
        self,
        *,
        category: str | None = None,
        query: str | None = None,
        include_inactive: bool = False,
    ) -> list[dict]:
        clauses = []
        params: list[Any] = []

        if not include_inactive:
            clauses.append("active=1")
        if category:
            clauses.append("category=?")
            params.append(category)
        if query:
            q = f"%{query.strip().lower()}%"
            clauses.append(
                """
                LOWER(
                    rule_id || ' ' || title || ' ' || category || ' ' ||
                    field || ' ' || direction || ' ' || explanation || ' ' ||
                    practical_impact || ' ' || tags_json
                ) LIKE ?
                """
            )
            params.append(q)

        sql = "SELECT * FROM knowledge_rules"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY category,rule_id"

        with connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()

        all_rules = {
            item["rule_id"]: item
            for item in self.rules(include_inactive=include_inactive)
        }
        return [
            all_rules[row["rule_id"]]
            for row in rows
            if row["rule_id"] in all_rules
        ]

    def related_rules(self, rule_id: str) -> list[dict]:
        with connect() as connection:
            rows = connection.execute(
                """
                SELECT l.relationship,l.note,r.*
                FROM knowledge_rule_links l
                JOIN knowledge_rules r
                  ON r.rule_id=l.target_rule_id
                WHERE l.source_rule_id=? AND r.active=1
                ORDER BY l.relationship,r.rule_id
                """,
                (rule_id,),
            ).fetchall()

        rec_map = {
            item["rule_id"]: item
            for item in self.rules()
        }
        result = []
        for row in rows:
            item = rec_map.get(row["rule_id"])
            if item:
                item = dict(item)
                item["relationship"] = row["relationship"]
                item["relationship_note"] = row["note"]
                result.append(item)
        return result

    def status(self) -> dict:
        from knowledge_engine.importer import runtime_status
        return runtime_status()

    def validate(self) -> list[str]:
        status = self.status()
        errors = []
        if not status["seeded"]:
            errors.append("Knowledge runtime database is empty.")

        with connect() as connection:
            broken_recommendations = connection.execute(
                """
                SELECT krr.rule_id,krr.recommendation_id
                FROM knowledge_rule_recommendations krr
                LEFT JOIN knowledge_rules kr
                  ON kr.rule_id=krr.rule_id
                LEFT JOIN knowledge_recommendations rec
                  ON rec.recommendation_id=krr.recommendation_id
                WHERE kr.rule_id IS NULL OR rec.recommendation_id IS NULL
                """
            ).fetchall()
            broken_links = connection.execute(
                """
                SELECT l.source_rule_id,l.target_rule_id
                FROM knowledge_rule_links l
                LEFT JOIN knowledge_rules source
                  ON source.rule_id=l.source_rule_id
                LEFT JOIN knowledge_rules target
                  ON target.rule_id=l.target_rule_id
                WHERE source.rule_id IS NULL OR target.rule_id IS NULL
                """
            ).fetchall()

        for row in broken_recommendations:
            errors.append(
                f'Broken recommendation link: {row["rule_id"]} → '
                f'{row["recommendation_id"]}.'
            )
        for row in broken_links:
            errors.append(
                f'Broken rule relationship: {row["source_rule_id"]} → '
                f'{row["target_rule_id"]}.'
            )
        return errors
