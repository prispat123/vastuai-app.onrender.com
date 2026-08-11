from __future__ import annotations
import uuid
from pathlib import Path
from PIL import Image
from platform_core.database import connect, transaction
from project_intelligence import document_intelligence, service
AUTO_SELECT_CLASSES={"Floor Plan","Master Layout"}
def _average_hash(path,size=16):
 image=Image.open(path).convert("L").resize((size,size)); pixels=list(image.getdata()); avg=sum(pixels)/len(pixels)
 bits="".join("1" if x>=avg else "0" for x in pixels); return f"{int(bits,2):0{size*size//4}x}"
def hamming_distance(a,b): return (int(a,16)^int(b,16)).bit_count()
def _new_run(project_id,document_id,run_type):
 with transaction() as c:
  cur=c.execute("INSERT INTO document_batch_runs(project_id,document_id,run_uuid,run_type,status) VALUES(?,?,?,?,?)",(project_id,document_id,str(uuid.uuid4()),run_type,"Queued")); return int(cur.lastrowid)
def _update(run_id,**fields):
 if not fields:return
 allowed={"status","total_pages","processed_pages","floor_plan_pages","layouts_created","needs_review","skipped_pages","error_message"}
 if set(fields)-allowed: raise ValueError("Unsupported batch field")
 with transaction() as c:c.execute(f"UPDATE document_batch_runs SET {', '.join(k+'=?' for k in fields)} WHERE id=?",list(fields.values())+[run_id])
def latest_batch_run(document_id):
 with connect() as c:return c.execute("SELECT * FROM document_batch_runs WHERE document_id=? ORDER BY id DESC LIMIT 1",(document_id,)).fetchone()
def scan_document(project_id,document_id,north_reference="Auto-detect"):
 pages=document_intelligence.list_pages(project_id,document_id)
 if not pages:
  document_intelligence.render_document(document_id); pages=document_intelligence.list_pages(project_id,document_id)
 run_id=_new_run(project_id,document_id,"FULL_DOCUMENT_SCAN"); _update(run_id,status="Processing",total_pages=len(pages))
 processed=floor_plans=needs_review=skipped=0; errors=[]
 for page in pages:
  try:
   result=document_intelligence.analyse_page(int(page["id"]),north_reference=north_reference)
   if result["classification"] in AUTO_SELECT_CLASSES:
    floor_plans+=1
    if result["overall_confidence"]<.70 or (result["classification"]=="Floor Plan" and not result["north_detected"]): needs_review+=1
   else: skipped+=1
  except Exception as exc:
   errors.append(f'Page {page["page_number"]}: {exc}'); needs_review+=1
   with transaction() as c:c.execute("UPDATE project_document_pages SET extraction_status='Failed',review_notes=? WHERE id=?",(str(exc),int(page["id"])))
  processed+=1; _update(run_id,processed_pages=processed,floor_plan_pages=floor_plans,needs_review=needs_review,skipped_pages=skipped)
 _update(run_id,status="Completed" if not errors else "Completed with Errors",error_message="\n".join(errors))
 with transaction() as c:c.execute("UPDATE document_batch_runs SET completed_at=CURRENT_TIMESTAMP WHERE id=?",(run_id,))
 service.add_timeline_event(project_id,"DOCUMENT_BATCH_SCAN_COMPLETED","Whole document analysed",f"{processed} pages; {floor_plans} layouts; {needs_review} review; {skipped} skipped")
 return {"run_id":run_id,"processed_pages":processed,"floor_plan_pages":floor_plans,"needs_review":needs_review,"skipped_pages":skipped,"errors":errors}
def shortlist_pages(project_id,document_id):
 rows=[]
 for page in document_intelligence.list_pages(project_id,document_id):
  extraction=document_intelligence.load_extraction(page); confidence=float((extraction or {}).get("overall_confidence",0))
  auto=page["classification"] in AUTO_SELECT_CLASSES or bool(page["is_floor_plan"])
  review=page["extraction_status"] in {"Needs Review","Failed"} or (page["classification"]=="Floor Plan" and not bool(page["north_detected"]))
  rows.append({"page":page,"extraction":extraction,"confidence":confidence,"auto_selected":auto,"needs_review":review})
 return rows
def _find_duplicate(project_id,image_path):
 fp=_average_hash(image_path)
 with connect() as c: rows=c.execute("SELECT * FROM layout_fingerprints WHERE project_id=?",(project_id,)).fetchall()
 best=None; dist=999
 for row in rows:
  d=hamming_distance(fp,row["perceptual_hash"])
  if d<dist:dist=d;best=int(row["layout_id"])
 return (best if dist<=10 else None,fp)
def create_layouts_from_selected_pages(project_id: int, page_ids: Iterable[int]) -> dict:
    created = needs_review = skipped = 0
    layout_ids = []
    for page_id in page_ids:
        with connect() as connection:
            page = connection.execute("SELECT * FROM project_document_pages WHERE id=?", (int(page_id),)).fetchone()
        if not page:
            skipped += 1
            continue
        extraction = document_intelligence.load_extraction(page)
        if not extraction:
            needs_review += 1
            continue
        layout_id = document_intelligence.create_layout_from_page(int(page_id))
        layout_ids.append(layout_id)
        created += 1
        if extraction.get("overall_confidence", 0) < .70 or not extraction.get("north_detected", False):
            needs_review += 1
    service.add_timeline_event(project_id, "BATCH_LAYOUT_CREATION_COMPLETED", "Selected layouts created", f"{created} created; {needs_review} need review; {skipped} skipped. No visual duplicate suppression applied.")
    return {"layouts_created": created, "duplicates": 0, "needs_review": needs_review, "skipped": skipped, "layout_ids": layout_ids}
