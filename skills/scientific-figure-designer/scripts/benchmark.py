#!/usr/bin/env python3
"""12 executable layouts + 4 held-out synthetic stress cases; not a human visual gold test."""
from pathlib import Path
import argparse
import statistics
import sys
import time
from figure_common import ROOT,write
from figure_plan import make_plan,registry
from figure import render_job
sys.path.insert(0,str(ROOT/'tests'))
from cases import make_case


def run(out):
    out=Path(out)
    if out.exists():raise ValueError('benchmark output exists; choose a new directory')
    out.mkdir(parents=True)
    records=[];layouts=list(registry()['layouts'])
    for i in range(16):
        directory=out/f'case-{i+1:02d}'
        name=layouts[i] if i<12 else ['comparative-panels','center-hero-side-support','top-overview-multi-lane','fork-merge-validation'][i-12]
        c,s=make_case(directory,number=i%4,count=3 if i<12 else 4,
                      relation_type=['sequence','depends_on','tests','measures','supports','activates','inhibits','feedback','association','parallel','sequence','tests','feedback','association','sequence','tests'][i])
        if i==14:
            c['labels'][1]['text']='拟核对第一组条件\n拟保留第二行文字';c['labels'][1]['kind']='approved_summary'
        if i==15:
            c['relations'][0]['to_id']='T3';c['relations'][1]['from_id']='T1';c['relations'][1]['to_id']='T2'
        p=make_plan(c,name,list(registry()['styles'])[i%4])
        write(directory/'input-content.json',c);write(directory/'input-plan.json',p)
        begin=time.perf_counter()
        try:
            qa=render_job(c,p,s,directory/'render')
            record={'case':i+1,'group':'development' if i<12 else 'holdout','layout':name,
                    'hard_pass':not qa['errors'],'errors':qa['errors'],'render_hash':qa['render_hash'],
                    'status':qa['status'],'wall_ms':round((time.perf_counter()-begin)*1000,2),'labels':len(qa['label_manifest'])}
        except Exception as exc:
            record={'case':i+1,'group':'development' if i<12 else 'holdout','layout':name,'hard_pass':False,'errors':[str(exc)],'wall_ms':round((time.perf_counter()-begin)*1000,2)}
        records.append(record);print(f'case {i+1:02d}: {record["hard_pass"]} {name}',flush=True)
    times=sorted(r['wall_ms'] for r in records)
    result={'cases':records,'hard_passes':sum(r['hard_pass'] for r in records),'total':16,
            'timing':{'p50_ms':statistics.median(times),'p95_nearest_rank_ms':times[15]},
            'source':'synthetic software fixtures, not real research evidence',
            'human_visual_gold':False,'expert_preference':'not_measured','external_provider_contract':'not_run',
            'notes':'Holdout cases exercise different topology/text combinations; no claim of unseen real-document accuracy.'}
    write(out/'benchmark.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);a=p.parse_args()
    result=run(a.out);raise SystemExit(0 if result['hard_passes']==result['total'] else 2)
