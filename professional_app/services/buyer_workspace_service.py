from __future__ import annotations
import json
import re
import uuid
from typing import Any
from platform_core.database import connect, initialize_database, transaction


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalized_buyer_key(name: str, date_of_birth: str) -> str:
    clean_name = re.sub(
        r"[^a-z0-9]+", " ", _clean(name).lower()
    ).strip()
    return f"{clean_name}|{_clean(date_of_birth)}"


def ensure_buyer_for_identity(connection, *, buyer_name: str, date_of_birth: str) -> int:
    name, dob = _clean(buyer_name), _clean(date_of_birth)
    if not name:
        raise ValueError("Buyer name is required before shortlisting.")
    key = normalized_buyer_key(name, dob)
    row = connection.execute(
        "SELECT id FROM buyers WHERE normalized_key=?", (key,)
    ).fetchone()
    if row:
        return int(row["id"])
    cursor = connection.execute(
        """INSERT INTO buyers(
           buyer_uuid,buyer_name,date_of_birth,normalized_key)
           VALUES(?,?,?,?)""",
        (str(uuid.uuid4()), name, dob, key),
    )
    return int(cursor.lastrowid)


def link_pdp_to_buyer(connection, *, pdp_id: int, profile: dict[str, Any]) -> int:
    buyer = profile.get("buyer", {}) or {}
    buyer_id = ensure_buyer_for_identity(
        connection,
        buyer_name=str(buyer.get("owner_name") or ""),
        date_of_birth=str(buyer.get("date_of_birth") or ""),
    )
    connection.execute(
        "UPDATE property_decision_profiles SET buyer_id=? WHERE id=?",
        (buyer_id, int(pdp_id)),
    )
    return buyer_id


def sync_buyers_from_pdps() -> dict[str, Any]:
    initialize_database()
    linked, failures = 0, []
    with transaction() as connection:
        rows = connection.execute(
            """SELECT id,decision_id,profile_json
               FROM property_decision_profiles
               WHERE buyer_id IS NULL ORDER BY id"""
        ).fetchall()
        for row in rows:
            try:
                link_pdp_to_buyer(
                    connection,
                    pdp_id=int(row["id"]),
                    profile=json.loads(row["profile_json"] or "{}"),
                )
                linked += 1
            except Exception as exc:
                failures.append(
                    {"decision_id": str(row["decision_id"]), "error": str(exc)}
                )
    return {
        "linked_count": linked,
        "failure_count": len(failures),
        "failures": failures,
    }


def list_buyers() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as connection:
        rows = connection.execute(
            """SELECT b.id,b.buyer_uuid,b.buyer_name,b.date_of_birth,
                      b.email,b.phone,b.status,
                      COUNT(DISTINCT pdp.id) AS pdp_count,
                      COUNT(DISTINCT CASE
                        WHEN bs.status='Shortlisted' THEN bs.id
                      END) AS shortlist_count
               FROM buyers b
               LEFT JOIN property_decision_profiles pdp
                 ON pdp.buyer_id=b.id
               LEFT JOIN buyer_shortlist_items bs
                 ON bs.buyer_id=b.id AND bs.pdp_id=pdp.id
               WHERE b.status='Active'
               GROUP BY b.id
               ORDER BY LOWER(b.buyer_name),b.date_of_birth,b.id"""
        ).fetchall()
    return [dict(row) for row in rows]


def get_buyer(buyer_id: int) -> dict[str, Any] | None:
    initialize_database()
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM buyers WHERE id=?", (int(buyer_id),)
        ).fetchone()
    return dict(row) if row else None


def buyer_for_pdp(pdp_id: int) -> dict[str, Any] | None:
    initialize_database()
    with connect() as connection:
        row = connection.execute(
            """SELECT b.* FROM property_decision_profiles pdp
               JOIN buyers b ON b.id=pdp.buyer_id
               WHERE pdp.id=?""",
            (int(pdp_id),),
        ).fetchone()
    return dict(row) if row else None


def _enrich(row) -> dict[str, Any]:
    item = dict(row)
    profile = json.loads(item.pop("profile_json") or "{}")
    item["profile"] = profile
    overall = profile.get("overall_professional", {}) or {}
    vastu = profile.get("vastu", {}) or {}
    numerology = profile.get("numerology", {}) or {}
    rec = profile.get("recommendation", {}) or {}
    item["overall_score"] = overall.get("score", item.get("overall_score"))
    item["overall_rating"] = overall.get("rating", item.get("overall_rating"))
    item["vastu_score"] = vastu.get("score")
    item["vastu_grade"] = vastu.get("grade")
    item["numerology_score_100"] = numerology.get("score_100")
    item["numerology_grade"] = numerology.get("grade")
    item["critical_high_count"] = vastu.get("critical_high_count", 0)
    item["recommendation"] = rec.get("decision")
    item["decision_confidence"] = rec.get("confidence")
    return item


def list_buyer_pdps(buyer_id: int) -> list[dict[str, Any]]:
    initialize_database()
    with connect() as connection:
        rows = connection.execute(
            """SELECT pdp.*,p.name AS project_name,p.city AS project_city,
                      CASE WHEN bs.id IS NULL THEN 0 ELSE 1 END AS shortlisted
               FROM property_decision_profiles pdp
               JOIN projects p ON p.id=pdp.project_id
               LEFT JOIN buyer_shortlist_items bs
                 ON bs.buyer_id=pdp.buyer_id
                AND bs.pdp_id=pdp.id
                AND bs.status='Shortlisted'
               WHERE pdp.buyer_id=?
               ORDER BY pdp.created_at DESC,pdp.id DESC""",
            (int(buyer_id),),
        ).fetchall()
    return [_enrich(row) for row in rows]


def list_shortlist(buyer_id: int) -> list[dict[str, Any]]:
    initialize_database()
    with connect() as connection:
        rows = connection.execute(
            """SELECT pdp.*,p.name AS project_name,p.city AS project_city,
                      bs.id AS shortlist_item_id,bs.shortlist_order,
                      bs.notes AS shortlist_notes
               FROM buyer_shortlist_items bs
               JOIN property_decision_profiles pdp ON pdp.id=bs.pdp_id
               JOIN projects p ON p.id=pdp.project_id
               WHERE bs.buyer_id=? AND bs.status='Shortlisted'
               ORDER BY bs.shortlist_order,bs.id""",
            (int(buyer_id),),
        ).fetchall()
    return [_enrich(row) for row in rows]


def is_shortlisted(buyer_id: int, pdp_id: int) -> bool:
    initialize_database()
    with connect() as connection:
        row = connection.execute(
            """SELECT 1 FROM buyer_shortlist_items
               WHERE buyer_id=? AND pdp_id=? AND status='Shortlisted'""",
            (int(buyer_id), int(pdp_id)),
        ).fetchone()
    return bool(row)


def normalize_shortlist_order(buyer_id: int) -> None:
    initialize_database()
    with transaction() as connection:
        rows = connection.execute(
            """SELECT id FROM buyer_shortlist_items
               WHERE buyer_id=? AND status='Shortlisted'
               ORDER BY shortlist_order,id""",
            (int(buyer_id),),
        ).fetchall()
        for order, row in enumerate(rows, 1):
            connection.execute(
                """UPDATE buyer_shortlist_items
                   SET shortlist_order=?,updated_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (order, int(row["id"])),
            )


def add_to_shortlist(buyer_id: int, pdp_id: int) -> None:
    initialize_database()
    with transaction() as connection:
        pdp = connection.execute(
            "SELECT buyer_id FROM property_decision_profiles WHERE id=?",
            (int(pdp_id),),
        ).fetchone()
        if not pdp:
            raise ValueError("PDP not found.")
        if int(pdp["buyer_id"] or 0) != int(buyer_id):
            raise ValueError("This PDP belongs to a different buyer.")
        next_order = int(
            connection.execute(
                """SELECT COALESCE(MAX(shortlist_order),0)+1 AS n
                   FROM buyer_shortlist_items
                   WHERE buyer_id=? AND status='Shortlisted'""",
                (int(buyer_id),),
            ).fetchone()["n"]
        )
        existing = connection.execute(
            """SELECT id FROM buyer_shortlist_items
               WHERE buyer_id=? AND pdp_id=?""",
            (int(buyer_id), int(pdp_id)),
        ).fetchone()
        if existing:
            connection.execute(
                """UPDATE buyer_shortlist_items
                   SET status='Shortlisted',shortlist_order=?,
                       updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                (next_order, int(existing["id"])),
            )
        else:
            connection.execute(
                """INSERT INTO buyer_shortlist_items(
                   buyer_id,pdp_id,shortlist_order,status)
                   VALUES(?,?,?,'Shortlisted')""",
                (int(buyer_id), int(pdp_id), next_order),
            )
    normalize_shortlist_order(buyer_id)


def remove_from_shortlist(buyer_id: int, pdp_id: int) -> None:
    initialize_database()
    with transaction() as connection:
        connection.execute(
            """UPDATE buyer_shortlist_items
               SET status='Removed',updated_at=CURRENT_TIMESTAMP
               WHERE buyer_id=? AND pdp_id=?""",
            (int(buyer_id), int(pdp_id)),
        )
    normalize_shortlist_order(buyer_id)


def move_shortlist_item(buyer_id: int, pdp_id: int, direction: str) -> None:
    items = list_shortlist(buyer_id)
    ids = [int(item["id"]) for item in items]
    target = int(pdp_id)
    if target not in ids:
        return
    index = ids.index(target)
    new_index = index - 1 if direction == "up" else index + 1
    if new_index < 0 or new_index >= len(ids):
        return
    ids[index], ids[new_index] = ids[new_index], ids[index]
    initialize_database()
    with transaction() as connection:
        for order, current_id in enumerate(ids, 1):
            connection.execute(
                """UPDATE buyer_shortlist_items
                   SET shortlist_order=?,updated_at=CURRENT_TIMESTAMP
                   WHERE buyer_id=? AND pdp_id=? AND status='Shortlisted'""",
                (order, int(buyer_id), int(current_id)),
            )


def update_buyer_contact(buyer_id: int, *, email: str, phone: str) -> None:
    initialize_database()
    with transaction() as connection:
        connection.execute(
            """UPDATE buyers SET email=?,phone=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (_clean(email), _clean(phone), int(buyer_id)),
        )
