"""Carry the source-bound parts of the design brief through editable plans."""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import re

from figure_assets import register
from figure_common import read
from figure_data import comparison_svg
from figure_plan import figure_theme

CHARTS = ('paired-dot', 'horizontal-bar')
TRACE_FIELDS = ('before', 'basis', 'after', 'next_action')


def design_bindings(decisions):
    visual = decisions.get('visual_concept') or {}
    return {'hero': decisions.get('hero_owner_id'), 'paths': decisions.get('main_paths', []),
            'traces': visual.get('object_trace', []), 'displays': visual.get('evidence_displays', [])}


def owner_regions(plan, content):
    owners = {i['id']: i['owner_id'] for i in content['label_instances']}
    return {r['id']: {owners[i] for i in r['label_instance_ids']} for r in plan['regions']}


def bind_design(plan, content, decisions):
    design = design_bindings(decisions)
    if not any(design.values()):
        return
    plan['design_bindings'] = design
    owners = owner_regions(plan, content)
    for d in design['displays']:
        if not isinstance(d, dict) or d.get('display') not in CHARTS:
            continue
        aid = d.get('asset_id')
        if not isinstance(aid, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', aid):
            raise ValueError('each comparison needs a unique asset_id')
        targets = [r for r in plan['regions'] if d.get('owner_id') in owners[r['id']]]
        if len(targets) != 1:
            raise ValueError(f'{aid}: use a dedicated comparison owner with one region')
        target = targets[0]
        if target.get('asset_ids') and target['asset_ids'] != [aid]:
            raise ValueError(f'{aid}: split comparison and illustration into separate regions')
        target['asset_ids'] = [aid]


def review_design(plan, content, assets):
    design = plan.get('design_bindings', {})
    owners = owner_regions(plan, content)
    source = {s['id']:s['excerpt'] for s in content['sources']}
    edges = {e['relation_id']:e for e in plan['edges']}
    relations = {r['id']:r for r in content['relations']}
    regional = {i:r['id'] for r in plan['regions'] for i in r['label_instance_ids']}
    labels = {label['id']: label for label in content['labels']}
    instances = {i['id']: i for i in content['label_instances'] if labels[i['label_id']]['source_ids']}
    review = {'paths':[], 'traces':[], 'displays':[], 'pending':[]}
    hero = design.get('hero')
    if hero:
        review['hero_regions'] = [r['id'] for r in plan['regions'] if hero in owners[r['id']] and r['role']=='hero']
        if not review['hero_regions']:
            review['pending'].append(f'check the visual emphasis for {hero}')
    for index, path in enumerate(design.get('paths', []), 1):
        if not isinstance(path, dict) or 'relation_ids' not in path:
            review['pending'].append(f'path {index}: legacy description needs visual review')
            continue
        ids = path['relation_ids']
        endpoints = [path.get('input'), path.get('output')]
        if not ids or any(i not in edges for i in ids):
            raise ValueError(f'path {index}: missing drawn relation in {ids}')
        walk = [relations[ids[0]]['from_id']]
        for rid in ids:
            rel = relations[rid]
            if rel['from_id'] != walk[-1]:
                raise ValueError(f'path {index}: disconnected handoff at {rid}')
            walk.append(rel['to_id'])
        if [walk[0],walk[-1]] != endpoints or path.get('intermediate') not in walk:
            raise ValueError(f'path {index}: drawn endpoints or handoff disagree with the brief')
        if not path.get('source_ids') or not set(path['source_ids']) <= source.keys():
            raise ValueError(f'path {index}: missing source')
        review['paths'].append({'owners':walk, 'relation_ids':ids, 'regions':[
            edges[ids[0]]['source_region_id'], *[edges[r]['target_region_id'] for r in ids]]})
    for index, trace in enumerate(design.get('traces', []), 1):
        if not isinstance(trace, dict) or 'owner_id' not in trace:
            review['pending'].append(f'trace {index}: locate before, basis, after and next action')
            continue
        owner = trace['owner_id']
        mapping = trace.get('label_instances', {})
        placed = {k:regional[i] for k,i in mapping.items() if k in TRACE_FIELDS and
                  isinstance(i,str) and i in regional and i in instances and instances[i]['owner_id'] == owner}
        aid = trace.get('asset_id')
        placed_image = aid in assets and owner in assets[aid]['source_content_ids'] and any(
            aid in r.get('asset_ids', []) and owner in owners[r['id']] for r in plan['regions'])
        features = trace.get('asset_features', {}) if placed_image else {}
        missing = [k for k in TRACE_FIELDS if k not in placed and not features.get(k)]
        visible = {k: labels[instances[mapping[k]]['label_id']]['text'] for k in placed}
        review['traces'].append({'owner_id':owner,'label_regions':placed,'visible_text':visible,
                                 'asset_id':aid if placed_image else None,
                                 'asset_features':features,'missing':missing})
        if missing:
            review['pending'].append(f'{owner}: missing trace fields {missing}')
        review['pending'].append(f'{owner}: verify the actual old and new state, basis and next action in the figure')
    for d in design.get('displays', []):
        if not isinstance(d,dict):
            review['pending'].append('inspect legacy evidence display')
            continue
        owner = d.get('owner_id')
        targets = [r for r in plan['regions'] if owner in owners[r['id']]]
        if owner and not targets:
            raise ValueError(f'{owner}: evidence display has no region')
        aid = d.get('asset_id')
        if aid or d.get('display') in CHARTS:
            if not aid or aid not in assets or not any(aid in r.get('asset_ids',[]) for r in targets):
                raise ValueError(f'{owner}: missing declared comparison {aid}')
            if not assets[aid]['contains_evidence'] or owner not in assets[aid]['source_content_ids']:
                raise ValueError(f'{owner}: comparison asset has no matching evidence binding')
        else:
            review['pending'].append(f'{owner}: review {d.get("display","text")} and its comparator')
        review['displays'].append({'owner_id':owner,'regions':[r['id'] for r in targets], **d})
    return review


@contextmanager
def comparison_assets(plan, content, manifests):
    displays = [d for d in plan.get('design_bindings',{}).get('displays',[]) if
                isinstance(d, dict) and d.get('display') in CHARTS]
    if not displays:
        yield manifests
        return
    supplied = {read(path)['id']:Path(path) for path in manifests}
    sources = {s['id']:s['excerpt'] for s in content['sources']}
    result = list(manifests)
    used = set()
    with TemporaryDirectory(prefix='figure-comparisons-') as tmp:
        for d in displays:
            aid = d.get('asset_id','')
            if not isinstance(aid,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',aid) or aid in used:
                raise ValueError('duplicate or invalid comparison asset_id')
            used.add(aid)
            for key in ('metric','unit','baseline','scope','owner_id','value_kind'):
                if not isinstance(d.get(key),str) or not d[key].strip():
                    raise ValueError(f'{aid}: comparison requires {key}')
            if not isinstance(d.get('rows'),list):
                raise ValueError(f'{aid}: missing comparison rows')
            for row in d['rows']:
                if not isinstance(row,dict) or not {'category','value','source_id'} <= row.keys():
                    raise ValueError(f'{aid}: each row needs category, value and source_id')
                if row.get('unit',d['unit']) != d['unit']:
                    raise ValueError(f'{aid}: incompatible units')
                excerpt = sources.get(row['source_id'],'').replace('−','-').replace(',','')
                values = re.findall(r'(?<![0-9A-Za-z.])[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?!\d|\.\d)',excerpt)
                if row['value'] not in [float(v) for v in values]:
                    raise ValueError(f'{aid}: value {row["value"]} absent in source {row["source_id"]}')
            payload = comparison_svg(d, figure_theme(plan))
            if aid in supplied:
                from figure_common import inside
                path = supplied[aid]
                if inside(path.parent, read(path)['asset_path']).read_bytes() != payload:
                    raise ValueError(f'{aid}: chart differs from bound comparison records or theme')
                continue
            svg = Path(tmp)/'comparison.svg'
            svg.write_bytes(payload)
            record = {'id':aid,'source_content_ids':[d['owner_id']],'contains_evidence':True,
                      'scientific_type':'comparison','style_family_id':plan['style_id'],
                      'rights':'authorized_reuse','approval':'production_approved','origin':'locally drawn from source-bound numbers',
                      'reviewer':'figure-design','review_note':'Exact values checked; interpretation requires scientific review.'}
            register(svg, record, tmp)
            result.append(Path(tmp)/aid/'asset.json')
        yield result
