#!/usr/bin/env python3
"""Tiny deterministic SVG scene demo. NOT the production scientific artwork renderer.
No AI, network calls, image reuse, font raster QA or complete edge-routing here.
"""
from __future__ import annotations
import argparse
from html import escape
import json
from pathlib import Path
from validate_contract import validate


def svg_content(content:dict,plan:dict)->str:
    skill=Path(__file__).resolve().parents[1]
    cs=json.loads((skill/'schemas/figure-content.schema.json').read_text(encoding='utf-8'))
    ps=json.loads((skill/'schemas/composition-plan.schema.json').read_text(encoding='utf-8'))
    problems=validate(cs,content)+validate(ps,plan)
    if problems:raise ValueError('\n'.join(problems))
    if content['figure_id']!=plan['figure_id']:raise ValueError('Figure ID mismatch')
    if plan['route']!='text_structured':raise ValueError('Only text_structured smoke previews are implemented')
    labels={x['id']:x['text'] for x in content['labels']}
    inst={x['id']:x for x in content['label_instances']}
    relations={x['id']:x for x in content['relations']}
    w,h=plan['canvas']['width'],plan['canvas']['height']
    regions={r['id']:r for r in plan['regions']}
    placed=[iid for r in plan['regions'] for iid in r['label_instance_ids']]
    if len(placed)!=len(set(placed)):raise ValueError('Duplicate placement of a label instance')
    if set(placed)-inst.keys():raise ValueError('Unknown label instance')
    if {x['id'] for x in inst.values() if x['required']}-set(placed):
        raise ValueError('Missing required label instances')
    if {x['id'] for x in relations.values() if x['critical']}-{x['relation_id'] for x in plan['edges']}:
        raise ValueError('Missing critical relations')
    if any(r.get('asset_ids') for r in plan['regions']):raise ValueError('Assets are not supported in the smoke renderer')
    for edge in plan['edges']:
        rel=relations.get(edge['relation_id'])
        if not rel:raise ValueError(f'Unknown relation {edge["relation_id"]}')
        if rel['type']!='sequence' or rel.get('condition_label_id') or edge['line_style'] not in ('solid','dashed'):
            raise ValueError('Smoke renderer supports only unconditional sequence arrows, solid or dashed')
        for region_key,owner_key in [('source_region_id','from_id'),('target_region_id','to_id')]:
            owners={inst[iid]['owner_id'] for iid in regions[edge[region_key]]['label_instance_ids']}
            if rel[owner_key] not in owners:raise ValueError('Relation endpoint does not match region owner')
    c=['<svg xmlns="http://www.w3.org/2000/svg" data-status="draft-smoke-only" viewBox="0 0 %d %d" width="%d" height="%d">'%(w,h,w,h),
       '<title>离线冒烟预览（非科研终稿；未验证字体与几何）</title>',
       '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8Z" fill="#286F78"/></marker></defs>',
       '<rect width="100%" height="100%" fill="#FFFFFF"/>']
    for r in plan['regions']:
        x,y,bw,bh=r['bounds']; x*=w;y*=h;bw*=w;bh*=h
        is_title=r['role']=='title'
        c.append(f'<g id="region-{escape(r["id"],quote=True)}">')
        if not is_title:
            c.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="14" fill="#E8F3F2" stroke="#9CBCC3" stroke-width="2"/>')
        for i, iid in enumerate(r['label_instance_ids']):
            if iid not in inst:raise ValueError(f'Unknown label instance {iid}')
            label=inst[iid]; value=labels[label['label_id']]
            size=36 if is_title else 24
            ty=y+(size*1.4)+(i*size*1.6)
            if ty>y+bh-8:raise ValueError(f'Text vertical overflow in {r["id"]}')
            c.append(f'<text id="label-{escape(iid,quote=True)}" x="{x+16:.1f}" y="{ty:.1f}" font-size="{size}" fill="#243342" font-family="Noto Sans CJK SC,Source Han Sans SC,Microsoft YaHei,sans-serif">{escape(value)}</text>')
        c.append('</g>')
    for edge in plan['edges']:
        rel=relations.get(edge['relation_id']);
        if not rel:raise ValueError(f'Unknown relation {edge["relation_id"]}')
        source=regions[edge['source_region_id']]['bounds'];target=regions[edge['target_region_id']]['bounds']
        x1=(source[0]+source[2]/2)*w;y1=(source[1]+source[3])*h
        x2=(target[0]+target[2]/2)*w;y2=target[1]*h
        dash=' stroke-dasharray="9 6"' if edge['line_style']=='dashed' else ''
        c.append(f'<path id="relation-{escape(rel["id"],quote=True)}" d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" fill="none" stroke="#286F78" stroke-width="3" marker-end="url(#arr)"{dash}/>')
    c.append('</svg>')
    return '\n'.join(c)+'\n'

def main()->int:
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--content',required=True,type=Path);a.add_argument('--plan',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
    args=a.parse_args()
    if args.out.resolve() in {args.content.resolve(),args.plan.resolve()}:a.error('Output must not overwrite inputs')
    try:
        content=json.loads(args.content.read_text(encoding='utf-8'));plan=json.loads(args.plan.read_text(encoding='utf-8'))
        xml=svg_content(content,plan)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(xml,encoding='utf-8')
    except (OSError,ValueError) as exc:a.error(str(exc))
    placed=[n for r in plan['regions'] for n in r['label_instance_ids']]
    print(f'Wrote DEMO SVG: {args.out} ({len(placed)} exact label instances); production font/geometry QA NOT implemented')
    return 0
if __name__=='__main__':raise SystemExit(main())
