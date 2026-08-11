from __future__ import annotations
import hashlib,json
from collections import Counter
from typing import Any
from project_intelligence import report_export_service,knowledge_reasoning_service

def _stable_hash(value:dict[str,Any])->str:
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _compact(k:dict)->dict:
    return {
      'profile_name':k.get('profile_name',''),'reasoning_summary':k.get('reasoning_summary',''),
      'average_confidence':k.get('average_confidence',0),
      'findings':[{
        'rule_id':r.get('rule_id'),'category':r.get('category'),'field':r.get('field'),'title':r.get('title'),
        'observed_value':r.get('observed_value'),'polarity':r.get('polarity'),'severity':r.get('severity'),
        'combined_confidence':r.get('combined_confidence'),'explanation':r.get('explanation'),
        'practical_impact':r.get('practical_impact'),'source_note':r.get('source_note')
      } for r in k.get('findings',[])],
      'priority_actions':[{
        'recommendation_id':r.get('recommendation_id'),'title':r.get('title'),'severity':r.get('severity'),
        'triggered_by':r.get('triggered_by'),'finding':r.get('finding'),'actions':r.get('actions',[]),
        'limitations':r.get('limitations',[])
      } for r in k.get('priority_actions',[])]
    }

def project_qa_context(project_id:int)->dict:
    data=report_export_service.project_export_data(project_id)
    layouts=[]
    stored_counter=Counter(); applicable_counter=Counter()
    for row in data['layouts']:
        knowledge=knowledge_reasoning_service.ensure_layout_knowledge(
            project_id=project_id,layout_id=int(row['layout_id']),directions=row['directions'],status=row['status'])
        item={
          'layout_id':row['layout_id'],'tower':row['tower'],'flat_number':row['flat_number'],
          'layout_type':row['layout_type'],'floor':row['floor'],'status':row['status'],'score':row['score'],
          'confidence':row['confidence'],'grade':row['grade'],'north':row['north'],'directions':row['directions'],
          'strengths':row['strengths'],'cautions':row['cautions'],
          'stored_knowledge':_compact(knowledge['stored']),
          'applicable_knowledge':_compact(knowledge['applicable']),
          'knowledge_backfilled':knowledge['backfilled'],
        }
        layouts.append(item)
        for f in item['stored_knowledge']['findings']: stored_counter[f"{f.get('rule_id','')} · {f.get('title','')}"]+=1
        for f in item['applicable_knowledge']['findings']: applicable_counter[f"{f.get('rule_id','')} · {f.get('title','')}"]+=1
    context={
      'scope':'project_qa',
      'project':{
        'project_id':int(project_id),'name':data['project']['name'],'knowledge_profile':data['knowledge_profile'],
        'summary':data['summary'],'towers':data['towers'],'layouts':layouts,
        'common_professional_issues':data['common_issues'],
        'common_stored_knowledge_rules':[{'rule':r,'count':c} for r,c in stored_counter.most_common(20)],
        'common_applicable_knowledge_rules':[{'rule':r,'count':c} for r,c in applicable_counter.most_common(20)],
        'room_comparison_matrix':knowledge_reasoning_service.comparison_matrix(layouts),
      },
      'reasoning_contract':{
        'verified_observations':'Saved reviewed directions, scores, grades, confidence, status, tower and flat.',
        'stored_knowledge':'Rules persisted with the final analysis.',
        'applicable_knowledge':'Local deterministic rules matched from reviewed directions for this snapshot.',
        'comparison':'Room-by-room differences derived only from verified directions.',
        'no_score_changes':True,'no_rule_invention':True,
      },
      'constraints':{'belief_based':True,'answer_only_from_snapshot':True,
                     'structured_reports_location':'Analysis & Review and Dashboard & Reports'},
    }
    context['source_hash']=_stable_hash(context)
    return context
