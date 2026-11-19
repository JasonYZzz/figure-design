"""Small-library bilingual lexical retrieval with evidence and explicit constraints."""
from __future__ import annotations
from collections import Counter
import json
import math
from pathlib import Path
import re
import sqlite3
from figure_catalog import resolve_image
from figure_common import fingerprint, write
from figure_knowledge import current, taxonomy


def tokens(text):
    text = text.lower()
    result = set(re.findall(r'[a-z0-9]+(?:[-_][a-z0-9]+)*', text))
    for run in re.findall(r'[\u3400-\u9fff]+', text):
        result.update(run[i:i+2] for i in range(len(run)-1))
    return result


def normalize(query, terms):
    text = query.lower()
    intents = {}
    for facet, values in terms['facets'].items():
        hits = [v for v, aliases in values.items() if any(a.lower() in text for a in [v, *aliases])]
        if hits: intents[facet] = hits
    expanded = set(tokens(text))
    for aliases in terms.get('aliases', {}).values():
        if any(a.lower() in text for a in aliases):
            for alias in aliases: expanded.update(tokens(alias))
    return expanded, intents


def rank(rows, catalog, query, limit, reviewed_only=False, require=None, diversity=True):
    library = Path(catalog).resolve().parent
    target = current(library, catalog)
    if target is None: return None
    terms = taxonomy(library)
    require = require or {}
    for key, value in require.items():
        if key in ('columns','task_lanes','duration_years'):
            if not str(value).isdigit() or int(value)<1:raise ValueError('positive count required')
            continue
        if key not in terms['facets'] or value not in terms['facets'][key]:
            raise ValueError('unknown required facet: ' + key)
    with sqlite3.connect((target / 'index.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        analyses = {rid: json.loads(raw) for rid, raw in db.execute('SELECT id,record FROM analyses')}
    patterns = json.loads((library/'patterns.json').read_text(encoding='utf-8'))
    qtokens, intents = normalize(query, terms)
    counts={}
    numerals={'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
    for pattern,key in [(r'([一二两三四五六七八九]|[0-9]+)年','duration_years'),(r'([一二两三四五六七八九]|[0-9]+)列','columns'),(r'([一二两三四五六七八九]|[0-9]+)(?:条|项)(?:并行)?(?:研究)?任务','task_lanes')]:
        match=re.search(pattern,query)
        if match:counts[key]=numerals.get(match[1],int(match[1]) if match[1].isdigit() else None)
    documents = {}
    for rid, a in analyses.items():
        documents[rid] = {
            'title': a['title'],
            'observation': ' '.join(o['text'] for o in a['observations']),
            'transfer': ' '.join(o['text'] for o in a['transfer']),
        }
    dtokens = {rid: {field: tokens(text) for field, text in doc.items()} for rid, doc in documents.items()}
    df = Counter(t for doc in dtokens.values() for t in set().union(*doc.values()))
    weights = {t: math.log(1 + len(documents) / (1 + df[t])) for t in qtokens}
    total = sum(weights.values()) or 1
    scored = []
    for row in rows:
        a = analyses.get(row['id'])
        if not a or (reviewed_only and a['review_status'] != 'human_approved'): continue
        facets = {k: v if isinstance(v, list) else [v] for k, v in a['facets'].items()}
        if any((a['spatial'].get(k)!=int(v) if k in a['spatial'] else v not in facets[k]) for k, v in require.items()): continue
        hits = {f: sorted(qtokens & ts) for f, ts in dtokens[row['id']].items()}
        lexical = sum(sum(weights[t] for t in ts) / total * w for (f,ts), w in zip(hits.items(), [3,2,1]))
        matched = {k: sorted(set(v) & set(facets[k])) for k,v in intents.items()}
        structure = sum({'topology':2,'layout':2,'media':2,'temporal_axis':2,'purpose':1.5,'domain':1,'density':1}[k] * len(v)/len(intents[k]) for k,v in matched.items())
        if query.strip() and not lexical and not structure: continue
        # A structural match may still miss other preferences; expose each unmet dimension.
        evidence = [{'field': f, 'tokens': t} for f,t in hits.items() if t]
        evidence += [{'field': k, 'values': v} for k,v in matched.items() if v]
        capacity=sum(3 if a['spatial'].get(k)==v else -1 if a['spatial'].get(k) is not None else 0 for k,v in counts.items())
        evidence += [{'field':k,'requested':v,'observed':a['spatial'].get(k),'status':'match' if a['spatial'].get(k)==v else 'unknown' if a['spatial'].get(k) is None else 'mismatch'} for k,v in counts.items()]
        score = max(0,lexical + structure + capacity)
        scored.append({**row, 'retrieval_score': round(score,6), 'score_components': {'lexical':round(lexical,6),'structure':round(structure,6),'capacity':capacity},
            'analysis': a, 'analysis_hash':fingerprint(a), 'analysis_status':a['review_status'], 'generation':target.name,
            'knowledge_page':str(target/'references'/(row['id']+'.md')),
            'related_patterns':[{'id':p['id'],'claim':p['claim'],'page':str(target/'patterns'/(p['id']+'.md'))} for p in patterns if any(s['reference_id']==row['id'] for s in p['sources'])], 'matching_evidence':evidence,
            'unmatched_preferences':{k:sorted(set(v)-set(facets[k])) for k,v in intents.items() if set(v)-set(facets[k])},
            'limitations':a['limitations'], 'transfer_regions':[r for r in a['regions'] if r['id']=='focus'],
            'query_interpretation':{'query':query,'soft_preferences':{**intents,**counts},'explicit_constraints':require},
            'visual_review':'pending', 'knowledge_status':'current'})
    selected, variants, layouts = [], Counter(), Counter()
    while scored and len(selected) < limit:
        def adjusted(row):
            a=row['analysis']; group=a['variant_group'] or row['id']
            penalty=(0.85 if variants[group] else 0) + min(.24, .08*layouts[a['facets']['layout']]) if diversity else 0
            return row['retrieval_score']*(1-min(.95,penalty))
        scored.sort(key=lambda r:(-adjusted(r),r['id']))
        row=scored.pop(0); row['selection_score']=round(adjusted(row),6)
        a=row['analysis'];variants[a['variant_group'] or row['id']]+=1;layouts[a['facets']['layout']]+=1
        selected.append(row)
    return selected


def resolve_images(rows, images):
    for row in rows:
        path, digest, status = resolve_image(row, images)
        row['image_path'] = str(path)
        row['image_file_sha256'] = digest
        row['image_status'] = status
    return rows


def suggest(catalog, content, query='', require=None):
    from figure_catalog import search
    types={r['type'] for r in content['relations']}
    inferred=['反馈' if t=='feedback' else '串行' if t in ('sequence','depends_on') else t for t in sorted(types)]
    effective = query or ' '.join([content['purpose'],*inferred])
    results=resolve_images(search(catalog,effective,5,require=require),Path(catalog).parent/'images')
    return {'source_content_hash':fingerprint(content),'query':effective,'explicit_constraints':require or {},
            'candidates':results,'status':'visual_review_pending','content_policy':'design_only; scientific content unchanged'}


def save_feedback(document, out, library):
    out=Path(out)
    if out.resolve().is_relative_to(Path(library).resolve()):
        raise ValueError('task feedback must stay outside shared reference library')
    if out.exists(): raise ValueError('feedback exists; choose a new version')
    if not re.fullmatch('[0-9a-f]{64}',document.get('source_content_hash','')):
        raise ValueError('feedback requires source_content_hash')
    if document.get('reviewer_kind') not in ('human','model') or not document.get('reviewer'):
        raise ValueError('feedback reviewer required')
    if document['reviewer_kind']=='human' and not document.get('attestation'):
        raise ValueError('actual human attestation required')
    for key in ('query','candidates','selected','changes','preflight','outcome'):
        if key not in document: raise ValueError('missing feedback field: '+key)
    if not set(document['selected']) <= set(document['candidates']):
        raise ValueError('selected reference absent from candidate list')
    value={**document,'status':'human_reported' if document['reviewer_kind']=='human' else 'auto_proposed'}
    write(out,value)
    return {'feedback':str(out),'status':value['status']}
