from __future__ import annotations
from typing import Any
from project_intelligence import knowledge_service, review_workflow
UNKNOWN_VALUES={"","Unknown","None","N/A",None}

def applicable_rules(directions:dict[str,Any],*,profile_name:str)->dict:
    """Deterministically match reviewed directions against local SQLite rules."""
    return knowledge_service.engine().evaluate(
        directions,profile=profile_name,
        detection_confidences={k:1.0 for k,v in directions.items() if k.endswith('_direction') and v not in UNKNOWN_VALUES},
    )

def stored_assessment(layout_id:int)->dict:
    latest=knowledge_service.latest_assessment(int(layout_id))
    return latest['result'] if latest else {}

def ensure_layout_knowledge(*,project_id:int,layout_id:int,directions:dict,status:str)->dict:
    stored=stored_assessment(layout_id)
    profile=knowledge_service.get_profile(project_id)
    applicable=applicable_rules(directions,profile_name=profile)
    backfilled=False
    if not stored and status==review_workflow.FINALISED:
        stored=knowledge_service.evaluate_layout(
            project_id,layout_id,directions,
            detection_confidences={k:1.0 for k,v in directions.items() if k.endswith('_direction') and v not in UNKNOWN_VALUES},
        )
        backfilled=True
    return {'stored':stored,'applicable':applicable,'backfilled':backfilled}

def comparison_matrix(layouts:list[dict])->list[dict]:
    fields=set()
    for layout in layouts: fields.update((layout.get('directions') or {}).keys())
    rows=[]
    for field in sorted(fields):
        values=[]
        for layout in layouts:
            value=(layout.get('directions') or {}).get(field,'Unknown')
            if value not in UNKNOWN_VALUES:
                values.append({'layout_id':layout['layout_id'],'tower':layout['tower'],'flat_number':layout['flat_number'],'value':value})
        if len(values)>=2:
            rows.append({'field':field,'values':values,'same_value':len({v['value'] for v in values})==1})
    return rows
