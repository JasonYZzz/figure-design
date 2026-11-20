"""Build a source-bound design worksheet; interpretation remains with Codex/reviewer."""
from figure_common import fingerprint
from figure_sources import evidence


def research_brief(content, sources, reference_images=()):
    checked = evidence(content, sources)
    if checked['errors']:
        raise ValueError('\n'.join(checked['errors']))
    labels = {label['id']: label for label in content['labels']}
    rows = []
    for task in content['tasks']:
        instances = [item for item in content['label_instances'] if item['owner_id'] == task['id']]
        rows.append({
            'task_id': task['id'], 'title': labels[task['title_label_id']]['text'],
            'status': task['status'], 'source_ids': task['source_ids'],
            'labels': [{'instance_id': item['id'], 'text': labels[item['label_id']]['text'],
                        'source_ids': labels[item['label_id']]['source_ids']} for item in instances],
            'incoming_relations': [r['id'] for r in content['relations'] if r['to_id'] == task['id']],
            'outgoing_relations': [r['id'] for r in content['relations'] if r['from_id'] == task['id']],
        })
    from figure_reference import reference_inputs
    from figure_plan import owner_slots
    return {
        'reference_source': 'upload' if reference_images else 'library',
        'uploaded_references': reference_inputs(reference_images),
        'composition_owners': owner_slots(content),
        'schema_version': '1.0', 'figure_id': content['figure_id'],
        'source_content_hash': fingerprint(content), 'status': 'semantic_design_pending',
        'purpose': content['purpose'], 'study_status': content['study_status'],
        'evidence_map': rows, 'relations': content['relations'], 'source_excerpts': content['sources'],
        'reference_requirements': {'query': content['purpose'], 'require': {}, 'task_count':len(content['tasks']),
            'relation_types':sorted({r['type'] for r in content['relations']}), 'count_policy':'capacity hint only; unknown reference counts never satisfy an exact constraint'},
        'design_decisions': {
            'main_question_or_supported_claim': None, 'hero_owner_id': None,
            'panel_questions_and_evidence_roles': [], 'reading_order': [],
            'main_paths': [], 'evidence_scope': [],
            'alternative_explanations_and_controls': [], 'color_meanings': [],
            'reference_choices_with_reasons': [], 'exclusions_with_reasons': [],
            'reference_design': None,
            'visual_concept': {'route': None, 'depictions': [], 'object_trace': [], 'evidence_displays': [], 'fallback_reason': None},
        },
        'review_required': [
            'Keep planned questions distinct from observed or validated conclusions.',
            'Trace the main paths without the local example. Identify the object passed and the action on each path.',
            'Read each evidence link as a claim. Match the target to the intervention, comparator, outcome and scope.',
            'Distinguish the main evidence from controls, methods and validation.',
            'Retain negation, units, uncertainty, experimental conditions and alternative explanations.',
            'Choose layout after the scientific argument; references provide design, never new facts.',
        ],
        'automation_scope': 'Exact source/label/relation mapping only; empty decisions require semantic design. No research conclusion or human approval is inferred.',
    }
