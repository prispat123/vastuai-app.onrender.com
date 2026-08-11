from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_context_has_evidence_layers():
 s=(ROOT/'project_intelligence'/'gpt_context_service.py').read_text(encoding='utf-8')
 for x in ['stored_knowledge','applicable_knowledge','room_comparison_matrix','knowledge_backfilled']: assert x in s
def test_local_applicable_rules_and_backfill():
 s=(ROOT/'project_intelligence'/'knowledge_reasoning_service.py').read_text(encoding='utf-8')
 assert 'knowledge_service.engine().evaluate(' in s
 assert 'knowledge_service.evaluate_layout(' in s
 assert 'review_workflow.FINALISED' in s
def test_prompt_distinguishes_layers_and_concrete_example():
 s=(ROOT/'project_intelligence'/'gpt_service.py').read_text(encoding='utf-8')
 for x in ['Verified observation','Stored Knowledge','Applicable Knowledge','East balcony','West balcony','VK-057','VK-061']: assert x in s
def test_ui_evidence_legend():
 s=(ROOT/'ui_pages'/'gpt_intelligence.py').read_text(encoding='utf-8')
 assert 'Evidence used in answers' in s and 'Applicable Knowledge' in s
