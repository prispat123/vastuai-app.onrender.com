from __future__ import annotations
import json
from pathlib import Path
from platform_core.database import connect, transaction
from professional_app.engine_facade import extract_layout
from professional_app.services.floorplan_service import analyse_floor_plan

NORTH_OPTIONS=["Unknown","Auto-detect","Top edge","Right edge","Bottom edge","Left edge"]
DIRECTIONS=["Unknown","North","North-East","East","South-East","South","South-West","West","North-West","Centre"]
ROOM_FIELDS=[("entrance_direction","Main Entrance"),("kitchen_direction","Kitchen"),("master_bedroom_direction","Master Bedroom"),("children_bedroom_direction","Children's Bedroom"),("guest_bedroom_direction","Guest Bedroom"),("toilet_direction","Toilet"),("pooja_direction","Pooja / Meditation"),("living_room_direction","Living Room"),("dining_direction","Dining"),("balcony_direction","Balcony"),("staircase_direction","Staircase"),("brahmasthan_direction","Brahmasthan")]
NOT_ANALYSED="Not Analysed"; NORTH_REVIEW="Analysed — North Review Required"; ROOM_REVIEW="North Confirmed — Room Review Required"; RECALC="Reviewed — Recalculation Required"; FINALISED="Finalised"; FAILED="Analysis Failed"

def _row(layout_id):
 with connect() as c:return c.execute('SELECT * FROM layout_review_state WHERE layout_id=?',(layout_id,)).fetchone()
def load(layout_id):
 r=_row(layout_id)
 if not r:return {'lifecycle_status':NOT_ANALYSED,'detected_north_position':'Unknown','detected_north_confidence':0.0,'confirmed_north_orientation':'Unknown','derived':{},'reviewed':{},'review_notes':''}
 return {'lifecycle_status':r['lifecycle_status'],'detected_north_position':r['detected_north_position'] or 'Unknown','detected_north_confidence':float(r['detected_north_confidence'] or 0),'confirmed_north_orientation':r['confirmed_north_orientation'] or 'Unknown','derived':json.loads(r['derived_json'] or '{}'),'reviewed':json.loads(r['reviewed_json'] or '{}'),'review_notes':r['review_notes'] or ''}
def initialise(project_id,layout_id,extraction):
 rooms=extraction.get('rooms',{}) if isinstance(extraction.get('rooms'),dict) else {}
 derived={}
 for f,_ in ROOM_FIELDS:
  v=rooms.get(f,extraction.get(f,'Unknown'))
  if isinstance(v,dict):v=v.get('value','Unknown')
  derived[f]=v or 'Unknown'
 detected=extraction.get('north_orientation') or extraction.get('north_description') or ('Auto-detect' if extraction.get('north_detected') else 'Unknown')
 conf=float(extraction.get('north_confidence',0) or 0)
 with transaction() as c:c.execute("""INSERT INTO layout_review_state(layout_id,project_id,detected_north_position,detected_north_confidence,derived_json,lifecycle_status) VALUES(?,?,?,?,?,?) ON CONFLICT(layout_id) DO UPDATE SET detected_north_position=excluded.detected_north_position,detected_north_confidence=excluded.detected_north_confidence,derived_json=excluded.derived_json,lifecycle_status=CASE WHEN layout_review_state.lifecycle_status='Finalised' THEN layout_review_state.lifecycle_status ELSE excluded.lifecycle_status END,updated_at=CURRENT_TIMESTAMP""",(layout_id,project_id,str(detected),conf,json.dumps(derived),NORTH_REVIEW))
 return load(layout_id)
def confirm_north(project_id,layout_id,drawing_path,north_orientation):
 if north_orientation not in NORTH_OPTIONS or north_orientation=='Unknown':
  raise ValueError('Select North orientation.')

 image_path=Path(drawing_path)
 if not image_path.exists() or not image_path.is_file():
  raise FileNotFoundError('The selected layout image could not be opened.')

 extraction=dict(
  analyse_floor_plan(
   image_path.read_bytes(),
   mode="Detailed",
   north_orientation=north_orientation,
   force_refresh=True,
  ) or {}
 )

 if not extraction.get('is_floor_plan',False):
  raise ValueError(
   'The image was not recognised as a floor plan. '
   'Please verify the selected page.'
  )

 rooms=extraction.get('rooms',{}) if isinstance(extraction.get('rooms'),dict) else {}
 derived={}
 confidences={}
 for f,_ in ROOM_FIELDS:
  raw=rooms.get(f,extraction.get(f,'Unknown'))
  confidence=0.0
  if isinstance(raw,dict):
   confidence=float(raw.get('confidence',0) or 0)
   value=raw.get('value','Unknown')
  else:
   value=raw
  derived[f]=value or 'Unknown'
  confidences[f]=confidence

 resolved=sum(
  1 for value in derived.values()
  if value not in {'','Unknown',None}
 )

 with transaction() as c:
  cursor=c.execute(
   """UPDATE layout_review_state SET
       confirmed_north_orientation=?,
       detected_north_confidence=1.0,
       derived_json=?,
       reviewed_json='{}',
       lifecycle_status=?,
       updated_at=CURRENT_TIMESTAMP
      WHERE layout_id=? AND project_id=?""",
   (
    north_orientation,
    json.dumps(derived),
    ROOM_REVIEW,
    layout_id,
    project_id,
   ),
  )
  if cursor.rowcount != 1:
   raise ValueError(
    'The layout review state was not found. '
    'Run the initial Professional analysis again.'
   )

 state=load(layout_id)
 state['resolved_room_count']=resolved
 state['room_confidences']=confidences
 state['extraction_issues']=extraction.get('issues',[])
 state['extraction_notes']=extraction.get('notes','')
 return state
def save_review(project_id,layout_id,reviewed,notes=''):
 with transaction() as c:
  c.execute('UPDATE layout_review_state SET reviewed_json=?,review_notes=?,lifecycle_status=?,updated_at=CURRENT_TIMESTAMP WHERE layout_id=? AND project_id=?',(json.dumps(reviewed),notes.strip(),RECALC,layout_id,project_id))
  c.execute('UPDATE project_layouts SET analysis_status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(RECALC,layout_id))
def final_payload(layout_id):
 s=load(layout_id);p=dict(s['derived']);p.update(s['reviewed']);p['north_orientation']=s['confirmed_north_orientation'];return p
def mark_final(project_id,layout_id):
 with transaction() as c:
  c.execute('UPDATE layout_review_state SET lifecycle_status=?,updated_at=CURRENT_TIMESTAMP WHERE layout_id=? AND project_id=?',(FINALISED,layout_id,project_id))
  c.execute('UPDATE project_layouts SET analysis_status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(FINALISED,layout_id))
