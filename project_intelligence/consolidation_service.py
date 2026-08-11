from __future__ import annotations
import json
from collections import Counter,defaultdict
from pathlib import Path
from platform_core.database import connect
from platform_core.projects import get_project
from platform_core.storage import STORAGE
from project_intelligence import review_workflow

def summary(project_id):
 with connect() as c:rows=c.execute("""SELECT pl.*,rs.lifecycle_status,pa.overall_score score,pa.confidence_value confidence,pa.grade,pa.findings_json FROM project_layouts pl LEFT JOIN layout_review_state rs ON rs.layout_id=pl.id LEFT JOIN project_layout_analyses pa ON pa.id=(SELECT id FROM project_layout_analyses p2 WHERE p2.layout_id=pl.id ORDER BY CASE WHEN p2.analysis_version='PROFESSIONAL-REVIEWED-1.0' THEN 0 ELSE 1 END,id DESC LIMIT 1) WHERE pl.project_id=?""",(project_id,)).fetchall()
 statuses=Counter((r['lifecycle_status'] or review_workflow.NOT_ANALYSED) for r in rows);final=[r for r in rows if r['lifecycle_status']==review_workflow.FINALISED and r['score'] is not None]
 towers=defaultdict(list);ranking=[];issues=Counter()
 for r in final:
  tower=r['tower'] or 'Unassigned Tower';score=float(r['score']);towers[tower].append(score);ranking.append({'tower':tower,'flat_number':r['flat_number'] or f"Layout {r['id']}",'layout_type':r['layout_type'] or '—','floor':r['floor'] or '—','score':score,'confidence':float(r['confidence'] or 0),'grade':r['grade'] or ''})
  try:findings=json.loads(r['findings_json'] or '[]')
  except:findings=[]
  for f in findings:
   if float(f.get('score',0) or 0)<7:issues[f"{f.get('area',f.get('field','Finding'))} · {f.get('direction','Unknown')}"]+=1
 ranking.sort(key=lambda x:x['score'],reverse=True);tr=[{'tower':k,'score':round(sum(v)/len(v),2),'finalised_layouts':len(v)} for k,v in towers.items()];tr.sort(key=lambda x:x['score'],reverse=True)
 scores=[x['score'] for x in ranking];return {'total':len(rows),'finalised':len(final),'coverage':len(final)/len(rows) if rows else 0,'building_score':round(sum(scores)/len(scores),2) if scores else None,'statuses':dict(statuses),'tower_ranking':tr,'layout_ranking':ranking,'common_issues':[{'issue':k,'count':v} for k,v in issues.most_common(12)]}
def generate_html(project_id,tower=None):
 p=get_project(project_id);d=summary(project_id);items=[x for x in d['layout_ranking'] if tower is None or x['tower']==tower];title=f"Tower Report — {tower}" if tower else f"Building Report — {p['name']}";rows=''.join(f"<tr><td>{i+1}</td><td>{x['tower']}</td><td>{x['flat_number']}</td><td>{x['score']}</td><td>{x['grade']}</td></tr>" for i,x in enumerate(items));html=f"<html><body><h1>{title}</h1><p>Coverage: {d['coverage']:.0%}</p><p>Score: {d['building_score'] if not tower else (round(sum(x['score'] for x in items)/len(items),2) if items else '—')}</p><table border='1' cellpadding='6'><tr><th>Rank</th><th>Tower</th><th>Flat</th><th>Score</th><th>Grade</th></tr>{rows}</table></body></html>".encode();folder=Path(p['project_folder'])/'reports'/'consolidated';folder.mkdir(parents=True,exist_ok=True);name='building_report.html' if tower is None else f"tower_{''.join(c if c.isalnum() else '_' for c in tower)}.html";path=folder/name;STORAGE.save_bytes(path,html,overwrite=True);return path
