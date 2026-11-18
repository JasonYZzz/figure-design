#!/usr/bin/env python3
"""Frozen 60-query ablations; coverage is not relevance or human acceptance."""
from pathlib import Path
import argparse
import copy
import math
import platform
import statistics
import time
from figure_common import ROOT,read,write,file_hash,fingerprint
from figure_knowledge import LIBRARY,records,current
from figure_catalog import search,TAG_FIELDS
from figure_retrieval import rank


def old_search(rows,query):
    words=query.lower().split();result=[]
    for row in rows:
        text=(' '.join(t for k in TAG_FIELDS for t in row.get(k,[]))+' '+' '.join(row.get('observations',[]))).lower()
        score=sum(w in text for w in words)+(.25 if row['review_status']=='human_approved' else 0)
        if not words or score>=1:result.append((score,row['id']))
    return [rid for _,rid in sorted(result,key=lambda x:(-x[0],x[1]))[:5]]


def run(out,library=LIBRARY,judgments=None):
    out=Path(out)
    if out.exists():raise ValueError('output exists; choose a new evaluation directory')
    out.mkdir(parents=True)
    fixture=ROOT/'tests/fixtures/reference-evaluation';queries=read(fixture/'queries.json');baseline=read(fixture/'baseline.json')
    rows=list(records(Path(library)/'catalog.sqlite').values());enhanced=copy.deepcopy(rows)
    for row in enhanced:
        a=read(Path(library)/'analyses'/(row['id']+'.json'))
        row['observations']=[a['title'],*[o['text'] for o in a['observations']],*[o['text'] for o in a['transfer']]]
        row['asset_tags']=[a['facets']['media']];row['composition_tags']=[a['facets']['layout'],*a['facets']['topology']]
        row['domain_tags']=[a['facets']['domain']]
    cases=[];pool=[]
    for q in queries:
        start=time.perf_counter();new=search(Path(library)/'catalog.sqlite',q['query']);elapsed=(time.perf_counter()-start)*1000
        plain=rank(rows,Path(library)/'catalog.sqlite',q['query'],5,diversity=False)
        methods={'old_descriptions_old_search':old_search(baseline,q['query']),
                 'new_descriptions_old_search':old_search(enhanced,q['query']),
                 'new_search_no_diversity':[r['id'] for r in plain], 'new_search':[r['id'] for r in new]}
        cases.append({**q,'methods':methods,'new_search_ms':round(elapsed,3),
                      'layout_families':len({r['analysis']['facets']['layout'] for r in new}),
                      'variant_groups':len({r['analysis']['variant_group'] or r['id'] for r in new})})
        for rid in sorted(set(r for ids in methods.values() for r in ids)):
            pool.append({'query_id':q['id'],'reference_id':rid,'grade':None,'rationale':None})
    times=sorted(c['new_search_ms'] for c in cases)
    report={'query_count':len(queries),'query_file_sha256':file_hash(fixture/'queries.json'),
        'generation':current(library,Path(library)/'catalog.sqlite').name,
        'machine':platform.platform(),'timing_scope':'in-process query including freshness checks; excludes CLI startup, image hashing and human visual review',
        'latency':{'p50_ms':statistics.median(times),'p95_ms':times[math.ceil(len(times)*.95)-1]},
        'nonempty_queries':{m:sum(bool(c['methods'][m]) for c in cases) for m in cases[0]['methods']},
        'human_gold':False,'ndcg_at_5':None,'hit_at_5':None,'structural_accuracy':None,'visual_preference':None,
        'interpretation':'Nonempty retrieval measures coverage only, not relevance. Semantic query families overlap across the initial split; no independent holdout generalization claim.',
        'cases':cases}
    if judgments:
        j=read(judgments)
        if j.get('reviewer_kind')!='human' or not j.get('attestation') or j.get('query_file_sha256')!=report['query_file_sha256']:
            raise ValueError('actual human judgments bound to the frozen queries required')
        grades={}
        for r in j['records']:
            if type(r['grade']) is not int or r['grade'] not in range(4):raise ValueError('all pool grades must be 0–3')
            key=(r['query_id'],r['reference_id'])
            if key in grades:raise ValueError('duplicate judgment')
            grades[key]=r['grade']
        if any((r['query_id'],r['reference_id']) not in grades for r in pool):raise ValueError('candidate pool judgments incomplete')
        results=[]
        def dcg(g):return sum((2**v-1)/math.log2(i+2) for i,v in enumerate(g[:5]))
        for c in cases:
            ideal=dcg(sorted([v for (qid,_),v in grades.items() if qid==c['id']],reverse=True))
            results.append({'query_id':c['id'],'split':c['split'],'pool_has_relevant':any(v>=2 for (qid,_),v in grades.items() if qid==c['id']),
                            'ndcg':{m:dcg([grades[(c['id'],rid)] for rid in ids])/ideal if ideal else None for m,ids in c['methods'].items()},
                            'hit':{m:any(grades[(c['id'],rid)]>=2 for rid in ids) for m,ids in c['methods'].items()}})
        report['judged_pool_metrics']=results;report['human_gold']=True
        report['judgment_scope']='pooled candidates only; not full-library recall or semantic field audit'
    write(out/'report.json',report)
    write(out/'judgments-template.json',{'reviewer':'','reviewer_kind':'human','attestation':'','query_file_sha256':report['query_file_sha256'],'records':pool})
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--library',default=str(LIBRARY));p.add_argument('--judgments');a=p.parse_args()
    r=run(a.out,a.library,a.judgments);print({k:r[k] for k in ('query_count','nonempty_queries','latency','human_gold')})
