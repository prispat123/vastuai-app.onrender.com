from __future__ import annotations

import hashlib
import json
from pathlib import Path

from platform_core.database import connect, initialize_database, transaction


ROOT = Path(__file__).resolve().parents[1] / "numerology_knowledge"


class NumerologyRepository:
    def __init__(self):
        initialize_database()
        self.ensure_seeded()

    def _bundle(self) -> tuple[dict, list[dict], str]:
        manifest = json.loads(
            (ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        objects = json.loads(
            (ROOT / "objects.json").read_text(encoding="utf-8")
        )["objects"]
        digest = hashlib.sha256()
        for path in [ROOT / "manifest.json", ROOT / "objects.json"]:
            digest.update(path.read_bytes())
        return manifest, objects, digest.hexdigest()

    def ensure_seeded(self) -> None:
        manifest, objects, source_hash = self._bundle()
        with connect() as connection:
            row = connection.execute(
                "SELECT source_hash FROM numerology_knowledge_meta WHERE id=1"
            ).fetchone()
        if row and row["source_hash"] == source_hash:
            return
        self.import_master()

    def import_master(self) -> dict:
        manifest, objects, source_hash = self._bundle()
        with transaction() as connection:
            for item in objects:
                number_value = item.get("number")
                connection.execute(
                    """
                    INSERT INTO numerology_knowledge_objects(
                        object_id,domain,number_value,title,polarity,severity,
                        score_delta,confidence,summary,recommendation,
                        source_json,version,active
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(object_id) DO UPDATE SET
                        domain=excluded.domain,
                        number_value=excluded.number_value,
                        title=excluded.title,
                        polarity=excluded.polarity,
                        severity=excluded.severity,
                        score_delta=excluded.score_delta,
                        confidence=excluded.confidence,
                        summary=excluded.summary,
                        recommendation=excluded.recommendation,
                        source_json=excluded.source_json,
                        version=excluded.version,
                        active=excluded.active,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        item["object_id"],
                        item["domain"],
                        number_value,
                        item["title"],
                        item.get("polarity", "contextual"),
                        item.get("severity", "Informational"),
                        float(item.get("score_delta", 0)),
                        float(item.get("confidence", 0)),
                        item.get("summary", ""),
                        item.get("recommendation", ""),
                        json.dumps(item, ensure_ascii=False),
                        item.get("version", manifest["knowledge_version"]),
                        int(bool(item.get("active", True))),
                    ),
                )
            connection.execute(
                """
                INSERT INTO numerology_knowledge_meta(
                    id,knowledge_version,schema_version,source_hash
                ) VALUES(1,?,?,?)
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
        return {
            "knowledge_version": manifest["knowledge_version"],
            "objects_imported": len(objects),
            "source_hash": source_hash,
        }

    def meta(self) -> dict:
        with connect() as connection:
            row = connection.execute(
                "SELECT * FROM numerology_knowledge_meta WHERE id=1"
            ).fetchone()
        return dict(row)

    def object_for_number(self, domain: str, number: int) -> dict | None:
        with connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM numerology_knowledge_objects
                WHERE active=1 AND domain=? AND number_value=?
                LIMIT 1
                """,
                (domain, int(number)),
            ).fetchone()
        return dict(row) if row else None

    def alignment_object(self, object_id: str) -> dict | None:
        with connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM numerology_knowledge_objects
                WHERE active=1 AND object_id=?
                """,
                (object_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_objects(self, query: str = "") -> list[dict]:
        sql = """
            SELECT object_id,domain,number_value,title,polarity,severity,
                   confidence,version,active
            FROM numerology_knowledge_objects
            WHERE active=1
        """
        params = []
        if query.strip():
            sql += """
                AND LOWER(
                    object_id || ' ' || domain || ' ' || title || ' ' ||
                    summary
                ) LIKE ?
            """
            params.append(f"%{query.strip().lower()}%")
        sql += " ORDER BY domain,number_value,object_id"
        with connect() as connection:
            return [
                dict(row)
                for row in connection.execute(sql, tuple(params)).fetchall()
            ]
