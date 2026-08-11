from __future__ import annotations
import json
from pathlib import Path
from platform_core.database import connect,transaction
from platform_core.projects import get_project
from platform_core.storage import STORAGE
from professional_app.graph import analyze_property
from professional_app.services.pdf_service import build_pdf
from project_intelligence import review_workflow, knowledge_service

def recalculate(project_id,layout_id):
 with connect() as c:l=c.execute('SELECT * FROM project_layouts WHERE id=? AND project_id=?',(layout_id,project_id)).fetchone()
 if not l:raise ValueError('Layout not found')
 reviewed=review_workflow.final_payload(layout_id); north=reviewed.pop('north_orientation','Unknown')
 if north=='Unknown':raise ValueError('Confirm North first')
 payload={'property_name':' · '.join(x for x in [l['tower'] or '',l['flat_number'] or '',l['layout_type'] or ''] if x) or f'Layout {layout_id}','flat_number':l['flat_number'] or '','owner_name':'','north_orientation':north};payload.update(reviewed)
 analysis=analyze_property(payload);vastu=analysis.get('vastu_result',{});final=analysis.get('final_result',{});rec=analysis.get('recommendation_result',{})
 score=float(final.get('score',vastu.get('score',0)) or 0);cov=float(vastu.get('coverage',0) or 0);cov=cov/100 if cov>1 else cov
 project=get_project(project_id);adir=Path(project['project_folder'])/'analysis'/'finalised';rdir=Path(project['project_folder'])/'reports'/'individual_layouts';adir.mkdir(parents=True,exist_ok=True);rdir.mkdir(parents=True,exist_ok=True)
 knowledge=knowledge_service.evaluate_layout(project_id,layout_id,payload,detection_confidences={k:1.0 for k in payload if k.endswith('_direction')}); stored={'layout':dict(l),'payload':payload,'analysis':analysis,'confidence':cov,'status':review_workflow.FINALISED,'knowledge_assessment':knowledge};jp=adir/f'layout_{layout_id}_finalised.json';STORAGE.write_json(jp,stored,overwrite=True)
 try:pdf=build_pdf(payload,analysis)
 except TypeError:pdf=build_pdf(analysis,payload)
 pp=rdir/f'layout_{layout_id}_professional_report.pdf';STORAGE.save_bytes(pp,pdf,overwrite=True)
 with transaction() as c:
  c.execute("""INSERT INTO project_layout_analyses(project_id,layout_id,analysis_version,source_extraction_id,vastu_score,overall_score,confidence_label,confidence_value,grade,status,strengths_json,cautions_json,findings_json,recommendations_json,result_json_path) VALUES(?,?,?,NULL,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(layout_id,analysis_version) DO UPDATE SET vastu_score=excluded.vastu_score,overall_score=excluded.overall_score,confidence_value=excluded.confidence_value,grade=excluded.grade,status=excluded.status,strengths_json=excluded.strengths_json,cautions_json=excluded.cautions_json,findings_json=excluded.findings_json,recommendations_json=excluded.recommendations_json,result_json_path=excluded.result_json_path,updated_at=CURRENT_TIMESTAMP""",(project_id,layout_id,'PROFESSIONAL-REVIEWED-1.0',float(vastu.get('score',0) or 0),score,'Reviewed',cov,vastu.get('grade',final.get('grade','')),review_workflow.FINALISED,json.dumps(vastu.get('strengths',[])),json.dumps(vastu.get('cautions',[])),json.dumps(vastu.get('details',[])),json.dumps(rec.get('actions',[])),str(jp)))
  notes=str(l['notes'] or '').split('Professional report:')[0].rstrip();notes+=(('\n' if notes else '')+f'Professional report: {pp}')
  c.execute('UPDATE project_layouts SET analysis_status=?,overall_score=?,confidence=?,last_analysis_at=CURRENT_TIMESTAMP,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(review_workflow.FINALISED,score,cov,notes,layout_id))
 review_workflow.mark_final(project_id,layout_id);return {'score':score,'confidence':cov,'pdf_path':str(pp)}
