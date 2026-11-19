#!/usr/bin/env python3
"""Validate JSON schema and a small set of referential-science invariants.
This is offline fixture validation, not a substitute for verifying the original document.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from jsonschema import Draft202012Validator

def unique(records:list[dict],category:str, errors:list[str])->set[str]:
    vals=[item['id'] for item in records]
    if len(vals)!=len(set(vals)):errors.append(f'duplicate IDs in {category}')
    return set(vals)

def check_content(data:dict)->list[str]:
    errors=[]
    source_ids=unique(data['sources'],'sources',errors)
    entity_ids=unique(data['entities'],'entities',errors)
    task_ids=unique(data['tasks'],'tasks',errors)
    label_ids=unique(data['labels'],'labels',errors)
    inst_ids=unique(data['label_instances'],'label_instances',errors)
    relation_ids=unique(data['relations'],'relations',errors)
    owners=[data['figure_id']]+[x['id'] for x in data['entities']+data['tasks']+data['relations']]
    if len(owners)!=len(set(owners)):errors.append('ambiguous owner IDs across content categories')
    for obj in data['entities']+data['tasks']+data['relations']+data['labels']:
        for sid in obj['source_ids']:
            if sid not in source_ids:errors.append(f'{obj["id"]} missing source {sid}')
    for obj in data['tasks']:
        if obj['title_label_id'] not in label_ids:errors.append(f'{obj["id"]}: title label missing')
        for ent in obj.get('entity_ids',[]):
            if ent not in entity_ids:errors.append(f'{obj["id"]}: entity missing {ent}')
    allowed_owner={data['figure_id']}|task_ids|entity_ids|{x['id'] for x in data['relations']}
    operation_owners=set()
    sourced_labels={label['id'] for label in data['labels'] if label['source_ids']}
    for item in data['label_instances']:
        if item['role']=='operation':
            owner=item['owner_id']
            if owner not in relation_ids or owner in operation_owners or item['label_id'] not in sourced_labels:
                errors.append(f"{item['id']}: an operation requires a unique relation owner and a source-bound label")
            operation_owners.add(owner)
        if item['label_id'] not in label_ids:errors.append(f'{item["id"]}: label missing')
        if item['owner_id'] not in allowed_owner:errors.append(f'{item["id"]}: unknown owner')
    for item in data['relations']:
        if item['from_id'] not in task_ids|entity_ids or item['to_id'] not in task_ids|entity_ids:
            errors.append(f'{item["id"]}: unknown edge endpoint')
        if item.get('condition_label_id') and item['condition_label_id'] not in label_ids:
            errors.append(f'{item["id"]}: unknown condition label')
        if item['critical'] and not item['source_ids']:
            errors.append(f'{item["id"]}: critical relation lacks source')
    for label in data['labels']:
        if not label['approved']:errors.append(f'{label["id"]}: unapproved label')
        if label['kind']!='editorial' and not label['source_ids']:
            errors.append(f'{label["id"]}: evidence-bound label lacks source')
    if not inst_ids:errors.append('no label instances')
    return errors

def check_plan(data:dict)->list[str]:
    errors=[]
    region_ids=unique(data['regions'],'regions',errors)
    relation_ids=[e['relation_id'] for e in data['edges']]
    if len(relation_ids)!=len(set(relation_ids)):errors.append('duplicate relation IDs in plan edges')
    for r in data['regions']:
        x,y,w,h=r['bounds']
        if x+w>1+1e-8 or y+h>1+1e-8 or w<=0 or h<=0:
            errors.append(f'{r["id"]}: invalid normalized bounds')
    for e in data['edges']:
        if e['source_region_id'] not in region_ids or e['target_region_id'] not in region_ids:
            errors.append(f'{e["relation_id"]}: dangling region endpoint')
    return errors

def validate(schema:dict,data:dict)->list[str]:
    # The offline validator must never fetch a user-supplied remote schema.
    def external_ref(value):
        if isinstance(value,dict):
            return any((key in ('$ref','$dynamicRef') and isinstance(child,str) and not child.startswith('#'))
                       or external_ref(child) for key,child in value.items())
        if isinstance(value,list):return any(external_ref(child) for child in value)
        return False
    if external_ref(schema):return ['external schema references are unsupported offline']
    Draft202012Validator.check_schema(schema)
    errors=[f'{"/".join(map(str,e.path)) or "/"}: {e.message}' for e in sorted(Draft202012Validator(schema).iter_errors(data),key=lambda e:str(e.path))]
    if errors:return errors
    if schema.get('title')=='FigureContent v1':errors.extend(check_content(data))
    if schema.get('title')=='CompositionPlan v1':errors.extend(check_plan(data))
    return errors

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schema',required=True,type=Path);p.add_argument('--input',required=True,type=Path)
    a=p.parse_args()
    s=json.loads(a.schema.read_text(encoding='utf-8'))
    d=json.loads(a.input.read_text(encoding='utf-8'))
    errors=validate(s,d)
    if errors:
        for e in errors:print('INVALID:',e)
        return 2
    print(f'VALID: {a.input.name} ({s.get("title", "unknown")})');return 0
if __name__=='__main__':raise SystemExit(main())
