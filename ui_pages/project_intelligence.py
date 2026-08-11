from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import streamlit as st
from ui_pages.knowledge_components import render_assessment, render_knowledge_base
from ui_pages import gpt_intelligence
from platform_core import projects as project_store
from project_intelligence import service,page_selection_service,professional_batch_service,review_workflow,recalculation_service,consolidation_service,report_export_service

PASTEL = {
 "green": "#DDF3E5", "sage": "#CFE8D7", "amber": "#FFF0D6",
 "coral": "#FCE2D9", "red": "#F8DADA", "lavender": "#EEE9F7",
}

def _score_fill(value):
 try: value=float(value)
 except (TypeError,ValueError): return ""
 if value >= 8: return f"background-color: {PASTEL['green']}; color:#315C43"
 if value >= 6: return f"background-color: {PASTEL['sage']}; color:#315C43"
 if value >= 4: return f"background-color: {PASTEL['amber']}; color:#745C23"
 return f"background-color: {PASTEL['coral']}; color:#844C3D"

def _status_fill(value):
 text=str(value).lower()
 if 'final' in text or 'ready' in text or 'complete' in text: return f"background-color: {PASTEL['green']}; color:#315C43"
 if 'review' in text or 'recalc' in text: return f"background-color: {PASTEL['amber']}; color:#745C23"
 if 'fail' in text or 'error' in text: return f"background-color: {PASTEL['red']}; color:#803C3C"
 return f"background-color: {PASTEL['lavender']}; color:#574B68"

def setup(project):
 st.header('Project Setup');d=service.get_project_details(int(project['id']))
 with st.form(f"setup_{project['id']}"):
  c1,c2=st.columns(2);ptype=c1.selectbox('Project type',service.PROJECT_TYPES,index=service.PROJECT_TYPES.index(d['project_type'] if d['project_type'] in service.PROJECT_TYPES else 'Apartment'));state=c2.text_input('State',d['state'] or '');country=c1.text_input('Country',d['country'] or 'India');towers=c2.number_input('Number of towers',min_value=0,step=1,value=int(d['number_of_towers'] or 0));remarks=st.text_area('Vastu-related remarks',d['remarks'] or '');save=st.form_submit_button('Save Project Setup',type='primary')
 if save:service.update_project_details(int(project['id']),project_type=ptype,state=state,country=country,north_reference='Manual per layout',number_of_towers=int(towers),remarks=remarks);st.rerun()
 st.divider();st.subheader('Delete Project');expected=str(project['name']).strip();confirm=st.text_input(f'Type the project name exactly: {expected}',key=f"del_{project['id']}")
 def delete():
  project_store.delete_project(int(project['id']),delete_files=True);st.session_state.active_project_id=None;st.session_state.page='Projects';st.session_state.project_section='Project Setup'
 st.button('Delete Current Project',disabled=confirm.strip()!=expected,on_click=delete,use_container_width=True)

def documents(project):
 st.header('Documents & Layout Selection');cat=st.selectbox('Document category',service.DOCUMENT_CATEGORIES);uploads=st.file_uploader('Upload brochure, PDF or image',type=['pdf','png','jpg','jpeg','webp'],accept_multiple_files=True,key=f"up_{project['id']}_{cat}")
 if st.button('Save Uploaded Documents',disabled=not uploads,type='primary',use_container_width=True):
  for u in uploads:service.save_document(int(project['id']),cat,u)
  st.rerun()
 docs=service.list_documents(int(project['id']))
 if not docs:st.info('Upload a document to continue.');return
 labels={f"{r['category']} · {r['display_name']}":r for r in docs};doc=labels[st.selectbox('Select document',list(labels))]
 if st.button('Extract Pages',type='primary',use_container_width=True):page_selection_service.ensure_pages(int(doc['id']));st.rerun()
 pages=page_selection_service.list_document_pages(int(project['id']),int(doc['id']))
 if not pages:st.info('Extract pages to display thumbnails.');return
 selected=[]
 for start in range(0,len(pages),3):
  cols=st.columns(3)
  for col,page in zip(cols,pages[start:start+3]):
   with col:
    p=Path(page['image_path']);
    if p.exists():st.image(str(p),caption=f"Page {page['page_number']}",use_container_width=True)
    if st.checkbox(f"Use page {page['page_number']} as layout",key=f"pick_{page['id']}"):selected.append(int(page['id']))
 if st.button('Create Selected Layouts',disabled=not selected,type='primary',use_container_width=True):page_selection_service.create_layouts_from_pages(int(project['id']),selected);st.session_state.pending_project_section='Layouts';st.rerun()

def layouts(project):
 st.header('Layouts');rows=service.list_layouts(int(project['id']))
 if not rows:st.info('No layouts created.');return
 st.dataframe(pd.DataFrame([dict(r) for r in rows])[["tower","flat_number","layout_type","floor","analysis_status","overall_score"]],use_container_width=True,hide_index=True)
 labels={f"{r['tower'] or 'No Tower'} · {r['flat_number'] or ('Layout '+str(r['id']))}":r for r in rows};sel=labels[st.selectbox('Select layout',list(labels))];c1,c2=st.columns(2)
 with c1:
  p=Path(sel['drawing_path'] or '');
  if p.exists() and p.is_file():st.image(str(p),use_container_width=True)
 with c2:
  with st.form(f"layout_{sel['id']}"):
   tower=st.text_input('Tower number / name',sel['tower'] or '');flat=st.text_input('Flat number',sel['flat_number'] or '');ltype=st.text_input('Layout type',sel['layout_type'] or '');floor=st.text_input('Floor',sel['floor'] or '');notes=st.text_area('Notes',sel['notes'] or '');save=st.form_submit_button('Save Layout Details',type='primary')
  if save:service.update_layout(int(sel['id']),tower=tower,flat_number=flat,layout_type=ltype,floor=floor,analysis_status=sel['analysis_status'],notes=notes);st.rerun()

def _latest_report_data(layout_id):
 from platform_core.database import connect
 with connect() as connection:
  row=connection.execute("""
   SELECT pa.*,pl.notes
   FROM project_layout_analyses pa
   JOIN project_layouts pl ON pl.id=pa.layout_id
   WHERE pa.layout_id=?
   ORDER BY CASE WHEN pa.analysis_version='PROFESSIONAL-REVIEWED-1.0'
    THEN 0 ELSE 1 END,pa.id DESC LIMIT 1
  """,(int(layout_id),)).fetchone()
 if not row:return None
 value=str(row['result_json_path'] or '').strip();path=Path(value) if value else None;stored={}
 if path and path.exists() and path.is_file():
  try:stored=json.loads(path.read_text(encoding='utf-8'))
  except (OSError,PermissionError,json.JSONDecodeError):stored={}
 report_path=None;notes=str(row['notes'] or '');marker='Professional report:'
 if marker in notes:
  candidate=Path(notes.split(marker)[-1].strip().splitlines()[0])
  if candidate.exists() and candidate.is_file():report_path=candidate
 return {'row':row,'stored':stored,'report_path':report_path}


def _render_flat_report(layout_id):
 latest=_latest_report_data(layout_id)
 if not latest:
  st.info('Finalise this layout to generate its individual Professional report.');return
 row=latest['row'];stored=latest['stored'];analysis=stored.get('analysis',{})
 final=analysis.get('final_result',{});vastu=analysis.get('vastu_result',{})
 recommendations=analysis.get('recommendation_result',{}).get('actions',[])
 st.divider();st.subheader('Individual Flat Report')
 c1,c2,c3,c4=st.columns(4)
 c1.metric('Overall Score',f"{float(row['overall_score'] or final.get('score',0) or 0):.1f}/10")
 c2.metric('Vastu Score',f"{float(row['vastu_score'] or vastu.get('score',0) or 0):.1f}/10")
 c3.metric('Confidence',f"{float(row['confidence_value'] or 0):.0%}")
 c4.metric('Grade',row['grade'] or vastu.get('grade','—'))
 confirmed=stored.get('confirmed_north_orientation',stored.get('confirmed_north_position',stored.get('payload',{}).get('north_orientation','Unknown')))
 st.write(f"**Confirmed North orientation:** {confirmed}")
 reviewed=stored.get('reviewed_directions',stored.get('payload',{}))
 room_rows=[]
 labels=dict(review_workflow.ROOM_FIELDS)
 for field,label in review_workflow.ROOM_FIELDS:
  if field in reviewed:room_rows.append({'Room':label,'Final direction':reviewed[field]})
 if room_rows:
  st.markdown('#### Final Reviewed Directions')
  st.dataframe(pd.DataFrame(room_rows),use_container_width=True,hide_index=True)
 left,right=st.columns(2)
 with left:
  st.markdown('#### Strengths')
  strengths=vastu.get('strengths',[])
  if strengths:
   for item in strengths:st.write(f"✓ {item}")
  else:st.caption('No strengths were listed.')
 with right:
  st.markdown('#### Needs Attention')
  cautions=vastu.get('cautions',[])
  if cautions:
   for item in cautions:st.write(f"• {item}")
  else:st.caption('No cautionary findings were listed.')
 if recommendations:
  st.markdown('#### Recommendations')
  for i,action in enumerate(recommendations,1):
   title=action.get('area') or action.get('title') or f'Recommendation {i}'
   priority=action.get('priority','Medium')
   with st.expander(f"{priority} · {title}",expanded=i==1):
    if action.get('finding'):st.write(f"**Finding:** {action['finding']}")
    if action.get('why_it_matters'):st.write(action['why_it_matters'])
    if action.get('practical_action'):st.write(f"**Practical action:** {action['practical_action']}")
    if action.get('structural_option'):st.write(f"**Structural option:** {action['structural_option']}")
 render_assessment(stored.get('knowledge_assessment',{}))
 report_path=latest['report_path']
 if report_path:
  st.download_button('Download Individual Professional Report (Original)',data=report_path.read_bytes(),file_name=report_path.name,mime='application/pdf',use_container_width=True,key=f'flat_report_{layout_id}')
 else:
  st.warning('The original Professional PDF was not found. The enhanced report below can still be generated from the saved final result.')
 enhanced_key=f'enhanced_flat_pdf_bytes_{layout_id}'
 if st.button(
  'Generate Enhanced Individual PDF',
  type='primary',
  use_container_width=True,
  key=f'generate_enhanced_flat_report_{layout_id}',
 ):
  try:
   with st.spinner('Generating enhanced individual PDF...'):
    st.session_state[enhanced_key]=report_export_service.individual_flat_pdf(
     int(st.session_state.active_project_id),
     layout_id,
    )
  except Exception as exc:
   st.error(f'Enhanced PDF generation failed: {exc}')
 if enhanced_key in st.session_state:
  st.download_button(
   'Download Enhanced Individual PDF',
   data=st.session_state[enhanced_key],
   file_name=f"individual_flat_{layout_id}.pdf",
   mime='application/pdf',
   type='primary',
   use_container_width=True,
   key=f'enhanced_flat_report_{layout_id}',
  )


def analysis_review(project):
 st.header('Analysis & Review');rows=service.list_layouts(int(project['id']))
 if not rows:st.info('Create layouts first.');return
 labels={f"{r['tower'] or 'No Tower'} · {r['flat_number'] or ('Layout '+str(r['id']))}":r for r in rows};sel=labels[st.selectbox('Select flat / layout',list(labels))];lid=int(sel['id']);img=Path(sel['drawing_path'] or '')
 left,right=st.columns([1,1])
 with left:
  if img.exists():st.image(str(img),use_container_width=True)
  st.write(f"**Tower:** {sel['tower'] or 'Not entered'}");st.write(f"**Flat:** {sel['flat_number'] or 'Not entered'}");st.write(f"**Score:** {sel['overall_score'] if sel['overall_score'] is not None else '—'}")
 with right:
  state=review_workflow.load(lid)
  if state['lifecycle_status']==review_workflow.NOT_ANALYSED:
   if st.button('Run Initial Professional Analysis',type='primary',use_container_width=True):
    result=professional_batch_service.analyse_selected_layouts(int(project['id']),[lid],north_reference='Auto-detect',generate_reports=True)
    if result['failed']:st.error('Initial analysis failed.')
    else:
     rp=Path(result['results'][0]['json_path']);stored=json.loads(rp.read_text(encoding='utf-8'));review_workflow.initialise(int(project['id']),lid,stored.get('extraction',{}));st.rerun()
   return
  st.write(f"**Lifecycle:** {state['lifecycle_status']}");st.subheader('1. Confirm North');st.write(f"Detected: **{state['detected_north_position']}**");st.write(f"Confidence: **{state['detected_north_confidence']:.0%}**")
  default=state['confirmed_north_orientation'] if state['confirmed_north_orientation'] in review_workflow.NORTH_OPTIONS else 'Unknown';north=st.selectbox('North orientation',review_workflow.NORTH_OPTIONS,index=review_workflow.NORTH_OPTIONS.index(default))
  if st.button('Confirm North and Derive Room Directions',disabled=north=='Unknown',type='primary',use_container_width=True):
   try:
    with st.spinner('Re-running Professional extraction with confirmed North...'):
     confirmation_result=review_workflow.confirm_north(
      int(project['id']),
      lid,
      img,
      north,
     )
   except Exception as exc:
    st.error(f'Room-direction derivation failed: {exc}')
   else:
    resolved=confirmation_result.get('resolved_room_count',0)
    st.session_state[f'north_derivation_notice_{lid}']=(
     f'North confirmed as {north}. '
     f'{resolved} room direction(s) were derived.'
    )
    st.rerun()

  notice_key=f'north_derivation_notice_{lid}'
  if notice_key in st.session_state:
   st.success(st.session_state.pop(notice_key))
 state=review_workflow.load(lid)
 if state['lifecycle_status'] in {review_workflow.ROOM_REVIEW,review_workflow.RECALC,review_workflow.FINALISED}:
  st.divider();st.subheader('2. Review Room Directions');vals=dict(state['derived']);vals.update(state['reviewed'])
  resolved_count=sum(1 for value in vals.values() if value not in {'','Unknown',None})
  if resolved_count==0:
   st.warning(
    'North was confirmed, but no room directions were confidently derived. '
    'Please correct the visible rooms manually below.'
   )
  else:
   st.caption(f'{resolved_count} room direction(s) derived from the confirmed North orientation.')
  edited={};cols=st.columns(2)
  for i,(field,label) in enumerate(review_workflow.ROOM_FIELDS):
   v=vals.get(field,'Unknown');v=v if v in review_workflow.DIRECTIONS else 'Unknown'
   with cols[i%2]:edited[field]=st.selectbox(label,review_workflow.DIRECTIONS,index=review_workflow.DIRECTIONS.index(v),key=f"room_{lid}_{field}")
  notes=st.text_area('Review notes',state['review_notes'])
  if st.button('Save Reviewed Directions',type='primary',use_container_width=True):review_workflow.save_review(int(project['id']),lid,edited,notes);st.rerun()
 state=review_workflow.load(lid)
 if state['lifecycle_status']==review_workflow.RECALC:
  st.divider();st.subheader('3. Recalculate and Finalise')
  if st.button('Recalculate Score and Regenerate Report',type='primary',use_container_width=True):
   with st.spinner('Recalculating...'):res=recalculation_service.recalculate(int(project['id']),lid)
   st.success(f"Finalised: {res['score']:.1f}/10");st.rerun()
 if state['lifecycle_status']==review_workflow.FINALISED:
  st.success('This layout is finalised. The individual report is shown below.')
  _render_flat_report(lid)

def dashboard(project):
 st.header('Dashboard & Reports')
 project_id=int(project['id'])
 d=consolidation_service.summary(project_id)
 c1,c2,c3,c4=st.columns(4)
 c1.metric('Total',d['total'])
 c2.metric('Finalised',d['finalised'])
 c3.metric('Coverage',f"{d['coverage']:.0%}")
 c4.metric('Building Score',f"{d['building_score']:.1f}/10" if d['building_score'] is not None else '—')

 st.subheader('Lifecycle Status')
 lifecycle_df=pd.DataFrame([{'Status':k,'Layouts':v} for k,v in d['statuses'].items()])
 st.dataframe(
  lifecycle_df.style.map(_status_fill,subset=['Status']),
  use_container_width=True,
  hide_index=True,
 )

 st.subheader('Tower Ranking')
 tf=pd.DataFrame(d['tower_ranking'])
 if not tf.empty:
  display_tf=tf.style.map(_score_fill,subset=['score']) if 'score' in tf.columns else tf
  st.dataframe(display_tf,use_container_width=True,hide_index=True)
  st.bar_chart(tf.set_index('tower')['score'],color='#A8D5BA')

 st.subheader('Flat Ranking')
 rf=pd.DataFrame(d['layout_ranking'])
 if not rf.empty:
  rf.insert(0,'rank',range(1,len(rf)+1))
  display_rf=rf.style.map(_score_fill,subset=['score']) if 'score' in rf.columns else rf
  st.dataframe(display_rf,use_container_width=True,hide_index=True)

 st.subheader('Common Issues')
 it=pd.DataFrame(d['common_issues'])
 if not it.empty:
  st.dataframe(it.style.set_properties(**{'background-color':'#FCE9DE'}),use_container_width=True,hide_index=True)

 st.divider()
 st.subheader('PDF Reports')
 if d['finalised']==0:
  st.info('Finalise at least one layout to enable PDF reports and exports.')
  return

 pdf1,pdf2=st.columns(2)
 if pdf1.button('Generate Building PDF',type='primary',use_container_width=True):
  try:
   st.session_state['building_pdf_bytes']=report_export_service.building_pdf(project_id)
  except Exception as exc:
   st.error(f'Building PDF generation failed: {exc}')
 if 'building_pdf_bytes' in st.session_state:
  pdf1.download_button(
   'Download Building PDF',
   data=st.session_state['building_pdf_bytes'],
   file_name=f"building_report_{project['name'].replace(' ','_')}.pdf",
   mime='application/pdf',
   use_container_width=True,
  )

 if pdf2.button('Generate Dashboard PDF',use_container_width=True):
  try:
   st.session_state['dashboard_pdf_bytes']=report_export_service.dashboard_pdf(project_id)
  except Exception as exc:
   st.error(f'Dashboard PDF generation failed: {exc}')
 if 'dashboard_pdf_bytes' in st.session_state:
  pdf2.download_button(
   'Download Dashboard PDF',
   data=st.session_state['dashboard_pdf_bytes'],
   file_name=f"dashboard_{project['name'].replace(' ','_')}.pdf",
   mime='application/pdf',
   use_container_width=True,
  )

 export_data=report_export_service.project_export_data(project_id)
 towers=[row['tower'] for row in export_data['towers']]
 if towers:
  tower=st.selectbox('Tower PDF',towers)
  tower_key=f'tower_pdf_bytes_{tower}'
  if st.button('Generate Selected Tower PDF',use_container_width=True):
   try:
    st.session_state[tower_key]=report_export_service.tower_pdf(project_id,tower)
   except Exception as exc:
    st.error(f'Tower PDF generation failed: {exc}')
  if tower_key in st.session_state:
   st.download_button(
    'Download Selected Tower PDF',
    data=st.session_state[tower_key],
    file_name=f"tower_{tower.replace(' ','_')}.pdf",
    mime='application/pdf',
    use_container_width=True,
   )

 st.subheader('Data Exports')
 e1,e2=st.columns(2)
 if e1.button('Generate Excel Workbook',use_container_width=True):
  try:
   st.session_state['project_excel_bytes']=report_export_service.excel_export(project_id)
  except Exception as exc:
   st.error(f'Excel generation failed: {exc}')
 if 'project_excel_bytes' in st.session_state:
  e1.download_button(
   'Download Excel Workbook',
   data=st.session_state['project_excel_bytes'],
   file_name=f"vastuai_export_{project['name'].replace(' ','_')}.xlsx",
   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
   use_container_width=True,
  )
 csv_files=report_export_service.csv_exports(project_id)
 csv_name=e2.selectbox('CSV dataset',list(csv_files))
 e2.download_button(
  'Download Selected CSV',
  data=csv_files[csv_name],
  file_name=csv_name,
  mime='text/csv',
  use_container_width=True,
 )

def render(project,section):
 routes={'Project Setup':setup,'Documents & Layout Selection':documents,'Layouts':layouts,'Analysis & Review':analysis_review,'Dashboard & Reports':dashboard,'Knowledge Base':render_knowledge_base,'AI Consultant':gpt_intelligence.render};routes.get(section,setup)(project)
