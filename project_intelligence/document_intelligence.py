from __future__ import annotations

import base64
import hashlib
import json
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from platform_core.database import connect, transaction
from platform_core.openai_service import OPENAI
from platform_core.projects import get_project
from platform_core.storage import STORAGE
from project_intelligence import service

PAGE_CLASSIFICATIONS = [
    "Unreviewed",
    "Floor Plan",
    "Master Layout",
    "Site Plan",
    "Text / Specification",
    "Marketing Image",
    "Other",
]

EXTRACTION_STATUSES = [
    "Not Processed",
    "Rendered",
    "Analysed",
    "Needs Review",
    "Approved",
    "Failed",
]

ROOM_KEYS = [
    "entrance_direction",
    "kitchen_direction",
    "master_bedroom_direction",
    "children_bedroom_direction",
    "guest_bedroom_direction",
    "toilet_direction",
    "pooja_direction",
    "living_room_direction",
    "dining_direction",
    "balcony_direction",
    "staircase_direction",
    "brahmasthan_direction",
]

ALLOWED_DIRECTIONS = [
    "Unknown", "North", "North-East", "East", "South-East",
    "South", "South-West", "West", "North-West", "Centre",
]

def _render_pdf_pages(pdf_path: Path, output_dir: Path, dpi: int = 150):
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise RuntimeError(
            "pypdfium2 is required for PDF processing. "
            "Run pip install -r requirements.txt."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    pdf = pdfium.PdfDocument(str(pdf_path))
    scale = dpi / 72
    rendered = []
    try:
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().convert("RGB")
            output = output_dir / f"page_{index + 1:04d}.jpg"
            image.save(output, "JPEG", quality=88, optimize=True)
            rendered.append(output)
            page.close()
    finally:
        pdf.close()
    return rendered

def render_document(document_id: int) -> int:
    with connect() as connection:
        document = connection.execute(
            "SELECT * FROM project_documents WHERE id=?",
            (int(document_id),),
        ).fetchone()
    if not document:
        raise ValueError("Document not found.")

    source = Path(document["stored_path"])
    if not source.exists():
        raise FileNotFoundError(source)

    project = get_project(int(document["project_id"]))
    page_dir = (
        Path(project["project_folder"])
        / "document_pages"
        / document["document_uuid"]
    )
    suffix = source.suffix.lower()

    if suffix == ".pdf":
        images = _render_pdf_pages(source, page_dir)
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        page_dir.mkdir(parents=True, exist_ok=True)
        image = Image.open(source).convert("RGB")
        output = page_dir / "page_0001.jpg"
        image.save(output, "JPEG", quality=90)
        images = [output]
    else:
        raise ValueError("Only PDF and image documents can be processed.")

    with transaction() as connection:
        for page_number, image_path in enumerate(images, start=1):
            image_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
            connection.execute(
                """
                INSERT INTO project_document_pages(
                    project_id,document_id,page_number,image_path,image_hash,
                    extraction_status
                ) VALUES(?,?,?,?,?,'Rendered')
                ON CONFLICT(document_id,page_number) DO UPDATE SET
                    image_path=excluded.image_path,
                    image_hash=excluded.image_hash,
                    extraction_status='Rendered',
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    int(document["project_id"]),
                    int(document_id),
                    page_number,
                    str(image_path),
                    image_hash,
                ),
            )

    service.add_timeline_event(
        int(document["project_id"]),
        "DOCUMENT_RENDERED",
        "Document pages prepared",
        f'{document["display_name"]}: {len(images)} page(s)',
    )
    return len(images)

def list_pages(project_id: int, document_id: int | None = None):
    query = """
        SELECT pg.*, d.display_name document_name, d.category document_category
        FROM project_document_pages pg
        JOIN project_documents d ON d.id=pg.document_id
        WHERE pg.project_id=?
    """
    params = [int(project_id)]
    if document_id is not None:
        query += " AND pg.document_id=?"
        params.append(int(document_id))
    query += " ORDER BY d.id,pg.page_number"
    with connect() as connection:
        return connection.execute(query, tuple(params)).fetchall()

def _normalise_direction(value: Any) -> str:
    text = str(value or "Unknown").strip().title()
    replacements = {
        "Northeast": "North-East",
        "Southeast": "South-East",
        "Southwest": "South-West",
        "Northwest": "North-West",
        "Center": "Centre",
    }
    text = replacements.get(text, text)
    return text if text in ALLOWED_DIRECTIONS else "Unknown"

def analyse_page(page_id: int, *, north_reference: str = "Auto-detect") -> dict:
    with connect() as connection:
        page = connection.execute(
            "SELECT * FROM project_document_pages WHERE id=?",
            (int(page_id),),
        ).fetchone()
    if not page:
        raise ValueError("Page not found.")

    image_path = Path(page["image_path"])
    image_bytes = image_path.read_bytes()
    data_url = (
        "data:image/jpeg;base64,"
        + base64.b64encode(image_bytes).decode("ascii")
    )

    prompt = f"""
You are extracting objective information from a residential project document page.
The configured North reference is: {north_reference}.

Return JSON only with this exact shape:
{{
  "classification": "Floor Plan",
  "is_floor_plan": true,
  "layout_identifiers": {{
    "tower": "",
    "flat_number": "",
    "layout_type": "",
    "floor": ""
  }},
  "north_direction": "Unknown",
  "north_detected": false,
  "north_confidence": 0.0,
  "north_description": "",
  "entrance_direction": "Unknown",
  "rooms": {{
    "entrance_direction": {{"value":"Unknown","confidence":0.0}},
    "kitchen_direction": {{"value":"Unknown","confidence":0.0}},
    "master_bedroom_direction": {{"value":"Unknown","confidence":0.0}},
    "children_bedroom_direction": {{"value":"Unknown","confidence":0.0}},
    "guest_bedroom_direction": {{"value":"Unknown","confidence":0.0}},
    "toilet_direction": {{"value":"Unknown","confidence":0.0}},
    "pooja_direction": {{"value":"Unknown","confidence":0.0}},
    "living_room_direction": {{"value":"Unknown","confidence":0.0}},
    "dining_direction": {{"value":"Unknown","confidence":0.0}},
    "balcony_direction": {{"value":"Unknown","confidence":0.0}},
    "staircase_direction": {{"value":"Unknown","confidence":0.0}},
    "brahmasthan_direction": {{"value":"Unknown","confidence":0.0}}
  }},
  "overall_confidence": 0.0,
  "issues": [],
  "notes": ""
}}

Rules:
1. Classify as one of: Unreviewed, Floor Plan, Master Layout, Site Plan,
   Text / Specification, Marketing Image, Other.
2. Do not infer North from page orientation unless the configured reference
   explicitly says Top, Right, Bottom or Left of page.
3. When Auto-detect is used, require a visible North arrow or compass.
4. Only assign room directions when North is known.
5. Use only these directions: {", ".join(ALLOWED_DIRECTIONS)}.
6. Do not invent tower, flat, room or direction information.
""".strip()

    started = time.perf_counter()
    response = OPENAI.client().chat.completions.create(
        model=OPENAI.models.vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    parsed = json.loads(response.choices[0].message.content or "{}")
    classification = str(parsed.get("classification", "Other"))
    if classification not in PAGE_CLASSIFICATIONS:
        classification = "Other"

    rooms_raw = parsed.get("rooms", {})
    rooms = {}
    for key in ROOM_KEYS:
        item = rooms_raw.get(key, {}) if isinstance(rooms_raw, dict) else {}
        rooms[key] = {
            "value": _normalise_direction(item.get("value")),
            "confidence": max(
                0.0,
                min(1.0, float(item.get("confidence", 0.0) or 0.0)),
            ),
        }

    result = {
        "classification": classification,
        "is_floor_plan": bool(parsed.get("is_floor_plan", False)),
        "layout_identifiers": parsed.get("layout_identifiers", {}),
        "north_direction": _normalise_direction(
            parsed.get("north_direction")
        ),
        "north_detected": bool(parsed.get("north_detected", False)),
        "north_confidence": max(
            0.0,
            min(1.0, float(parsed.get("north_confidence", 0.0) or 0.0)),
        ),
        "north_description": str(
            parsed.get("north_description", "")
        ).strip(),
        "entrance_direction": _normalise_direction(
            parsed.get("entrance_direction")
        ),
        "rooms": rooms,
        "overall_confidence": max(
            0.0,
            min(1.0, float(parsed.get("overall_confidence", 0.0) or 0.0)),
        ),
        "issues": [
            str(item) for item in parsed.get("issues", [])
            if str(item).strip()
        ],
        "notes": str(parsed.get("notes", "")).strip(),
        "model": OPENAI.models.vision_model,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }

    project = get_project(int(page["project_id"]))
    output_dir = Path(project["project_folder"]) / "analysis" / "page_extractions"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'page_{page["id"]}_{page["image_hash"][:10]}.json'
    STORAGE.write_json(output_path, result, overwrite=True)

    status = (
        "Needs Review"
        if result["overall_confidence"] < 0.70
        or (result["is_floor_plan"] and not result["north_detected"])
        else "Analysed"
    )

    with transaction() as connection:
        connection.execute(
            """
            UPDATE project_document_pages SET
                classification=?,is_floor_plan=?,north_detected=?,
                north_confidence=?,north_description=?,
                extracted_json_path=?,extraction_status=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                classification,
                int(result["is_floor_plan"]),
                int(result["north_detected"]),
                result["north_confidence"],
                result["north_description"],
                str(output_path),
                status,
                int(page_id),
            ),
        )
        connection.execute(
            """
            INSERT INTO layout_extractions(
                project_id,page_id,source_hash,north_direction,
                entrance_direction,rooms_json,vision_confidence,
                model_name,raw_json_path
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                int(page["project_id"]),
                int(page_id),
                page["image_hash"],
                result["north_direction"],
                result["entrance_direction"],
                json.dumps(result["rooms"]),
                result["overall_confidence"],
                result["model"],
                str(output_path),
            ),
        )

    service.add_timeline_event(
        int(page["project_id"]),
        "PAGE_ANALYSED",
        "Document page analysed",
        f'Page {page["page_number"]}: {classification}',
    )
    return result

def load_extraction(page) -> dict | None:
    path = str(page["extracted_json_path"] or "").strip()
    if not path or not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))

def update_page_review(
    page_id: int,
    *,
    classification: str,
    north_detected: bool,
    north_confidence: float,
    north_description: str,
    extraction_status: str,
    review_notes: str,
) -> None:
    if classification not in PAGE_CLASSIFICATIONS:
        raise ValueError("Invalid classification.")
    if extraction_status not in EXTRACTION_STATUSES:
        raise ValueError("Invalid extraction status.")
    with transaction() as connection:
        connection.execute(
            """
            UPDATE project_document_pages SET
                classification=?,is_floor_plan=?,north_detected=?,
                north_confidence=?,north_description=?,
                extraction_status=?,review_notes=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                classification,
                int(classification == "Floor Plan"),
                int(north_detected),
                max(0.0, min(1.0, float(north_confidence))),
                north_description.strip(),
                extraction_status,
                review_notes.strip(),
                int(page_id),
            ),
        )

def create_layout_from_page(page_id: int) -> int:
    with connect() as connection:
        page = connection.execute(
            "SELECT * FROM project_document_pages WHERE id=?",
            (int(page_id),),
        ).fetchone()
        extraction_row = connection.execute(
            """
            SELECT * FROM layout_extractions
            WHERE page_id=? ORDER BY id DESC LIMIT 1
            """,
            (int(page_id),),
        ).fetchone()
    if not page:
        raise ValueError("Page not found.")

    extraction = load_extraction(page) or {}
    identifiers = extraction.get("layout_identifiers", {})
    status = (
        "Ready"
        if extraction.get("is_floor_plan")
        and extraction.get("north_detected")
        else "Needs Review"
    )
    layout_id = service.add_layout(
        int(page["project_id"]),
        tower=str(identifiers.get("tower", "")),
        flat_number=str(
            identifiers.get("flat_number", "")
            or f'Page-{page["page_number"]}'
        ),
        layout_type=str(identifiers.get("layout_type", "")),
        floor=str(identifiers.get("floor", "")),
        drawing_path=page["image_path"],
        notes="Created from document page extraction.",
    )
    service.update_layout(
        layout_id,
        tower=str(identifiers.get("tower", "")),
        flat_number=str(
            identifiers.get("flat_number", "")
            or f'Page-{page["page_number"]}'
        ),
        layout_type=str(identifiers.get("layout_type", "")),
        floor=str(identifiers.get("floor", "")),
        analysis_status=status,
        notes="Created from document page extraction.",
    )
    if extraction_row:
        with transaction() as connection:
            connection.execute(
                "UPDATE layout_extractions SET layout_id=? WHERE id=?",
                (layout_id, int(extraction_row["id"])),
            )
    update_page_review(
        int(page_id),
        classification="Floor Plan",
        north_detected=bool(page["north_detected"]),
        north_confidence=float(page["north_confidence"]),
        north_description=page["north_description"] or "",
        extraction_status="Approved",
        review_notes=page["review_notes"] or "",
    )
    return layout_id
