from __future__ import annotations
from typing import Iterable
from platform_core.database import connect
from project_intelligence import document_intelligence, service

def list_document_pages(project_id: int, document_id: int):
    return document_intelligence.list_pages(int(project_id), int(document_id))

def ensure_pages(document_id: int) -> int:
    return document_intelligence.render_document(int(document_id))

def create_layouts_from_pages(project_id: int, page_ids: Iterable[int]) -> dict:
    created = skipped = 0
    layout_ids = []
    for page_id in page_ids:
        with connect() as connection:
            page = connection.execute(
                """
                SELECT pg.*, d.display_name document_name
                FROM project_document_pages pg
                JOIN project_documents d ON d.id=pg.document_id
                WHERE pg.id=? AND pg.project_id=?
                """,
                (int(page_id), int(project_id)),
            ).fetchone()
        if not page:
            skipped += 1
            continue

        layout_id = service.add_layout(
            int(project_id),
            tower="",
            flat_number=f'Page-{page["page_number"]}',
            layout_type="",
            floor="",
            drawing_path=page["image_path"],
            notes=(
                f'Created from {page["document_name"]}, page '
                f'{page["page_number"]}. Awaiting Professional analysis.'
            ),
        )
        service.update_layout(
            int(layout_id),
            tower="",
            flat_number=f'Page-{page["page_number"]}',
            layout_type="",
            floor="",
            analysis_status="Not Started",
            notes=(
                f'Created from {page["document_name"]}, page '
                f'{page["page_number"]}. Awaiting Professional analysis.'
            ),
        )
        layout_ids.append(layout_id)
        created += 1

    service.add_timeline_event(
        int(project_id),
        "LAYOUT_PAGES_SELECTED",
        "Layout pages selected",
        f"{created} layout(s) created; {skipped} skipped.",
    )
    return {
        "layouts_created": created,
        "skipped": skipped,
        "layout_ids": layout_ids,
    }
