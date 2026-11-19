#!/usr/bin/env python3
"""Create two illustrated compositions from one explicitly fictional research brief."""
from pathlib import Path
import argparse
from figure_common import read,write
from figure_sources import ingest
from figure_plan import make_plan
from figure_assets import register_themed
from figure import render_job


def run(out):
    out=Path(out)
    if out.exists():raise ValueError('demo output already exists')
    out.mkdir(parents=True)
    title='水质传感数据研究路线（虚构示例）'
    groups=[['研究对象与测量条件','拟研究水质传感数据的可靠性','比较不同采样条件下的数据质量','本示例无实测结果'],
            ['数据采集','拟明确采样对象与对照条件','记录传感数据及采样时间','保留原始文件与采样日志'],
            ['质量检查','拟检查缺失值与异常记录','区分仪器误差与环境变化','保留处理规则与原始数值'],
            ['模型分析','拟比较可解释的分析方法','使用预先定义的验证划分','不将预测输出当作因果证据'],
            ['独立核验','拟复核数据来源与指标定义','检查结果是否可重复','输出分析记录与待解决问题']]
    text='软件演示专用虚构研究方案，不对应真实实验。\n'+title+'\n'+'\n'.join('\n'.join(g) for g in groups)+'\n流程拟按研究对象、数据采集、质量检查、模型分析、独立核验的顺序开展。'
    brief=out/'brief.md';brief.write_text(text,encoding='utf-8')
    source_path=ingest(brief,out/'sources')['source'];source=read(source_path)
    sources=[];labels=[];instances=[];tasks=[]
    def label(value,owner,role):
        idx=len(labels);start=text.index(value)
        sources.append({'id':f'S{idx}','document_sha256':source['document_sha256'],'locator':f'chars:{start}:{start+len(value)}','excerpt':value,'verification':'verified_exact'})
        labels.append({'id':f'L{idx}','text':value,'kind':'verbatim','approved':True,'source_ids':[f'S{idx}']})
        instances.append({'id':f'I{idx}','label_id':f'L{idx}','owner_id':owner,'role':role,'required':True})
        return f'L{idx}',f'S{idx}'
    label(title,'ILLUSTRATED-DEMO','title')
    for i,group in enumerate(groups):
        lid,sid=label(group[0],f'T{i+1}','task')
        tasks.append({'id':f'T{i+1}','title_label_id':lid,'status':'planned','source_ids':[sid]})
        for line in group[1:]:label(line,f'T{i+1}','method')
    content={'schema_version':'1.0','figure_id':'ILLUSTRATED-DEMO','purpose':title,'domain':'environmental-data','study_status':'planned','sources':sources,'entities':[],
             'tasks':tasks,'relations':[{'id':f'R{i+1}','from_id':f'T{i+1}','to_id':f'T{i+2}','type':'sequence','evidence_state':'planned','source_ids':[tasks[i]['source_ids'][0],tasks[i+1]['source_ids'][0]],'critical':True} for i in range(4)],'labels':labels,'label_instances':instances}
    write(out/'figure-content.json',content)
    icons=[
        '<ellipse cx="180" cy="130" rx="125" ry="55" fill="#e9edf8"/><path d="M180 35 C180 35 120 105 120 139 A60 60 0 0 0 240 139 C240 105 180 35 180 35Z" fill="#8198c7"/><circle cx="190" cy="145" r="27" fill="#f8f9fc"/>',
        '<rect x="93" y="45" width="174" height="145" rx="18" fill="#e9edf8" stroke="#31598f" stroke-width="4"/><rect x="116" y="67" width="128" height="63" rx="5" fill="white"/><path d="M180 130 V167 M151 167 H209" stroke="#31598f" stroke-width="5"/><circle cx="180" cy="160" r="7" fill="#31598f"/>',
        '<rect x="85" y="45" width="140" height="140" rx="10" fill="#e9edf8"/><path d="M105 78 H190 M105 108 H175 M105 138 H155" stroke="#31598f" stroke-width="6"/><circle cx="215" cy="135" r="40" fill="white" stroke="#31598f" stroke-width="7"/><path d="M245 165 L277 197" stroke="#31598f" stroke-width="12"/>',
        '<path d="M180 35 L290 95 L180 155 L70 95Z" fill="#8198c7"/><path d="M70 130 L180 190 L290 130" fill="none" stroke="#31598f" stroke-width="12"/><path d="M70 160 L180 220 L290 160" fill="none" stroke="#bdcbe4" stroke-width="12"/>',
        '<rect x="100" y="35" width="160" height="180" rx="12" fill="#e9edf8" stroke="#31598f" stroke-width="4"/><path d="M128 95 L147 114 L188 73 M128 160 L147 179 L188 138" fill="none" stroke="#31598f" stroke-width="9"/><path d="M205 98 H235 M205 162 H235" stroke="#8198c7" stroke-width="5"/>']
    variants = [('center-hero-side-support','earth-climate'),('top-overview-multi-lane','earth-process')]
    for primary,style in variants:
        plan=make_plan(content,primary,style,route='asset_composite')
        manifests=[]
        for i,drawing in enumerate(icons):
            for old, role in {'#e9edf8':'accent-pale','#8198c7':'secondary-light','#f8f9fc':'paper',
                              '#31598f':'accent','#bdcbe4':'tertiary-light'}.items():
                drawing=drawing.replace(old, '{{figure:'+role+'}}')
            path=out/f'icon-{i+1}.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="360" height="250" viewBox="0 0 360 250">'+drawing+'</svg>', encoding='utf-8')
            asset_id=f'demo-icon-{i+1}'
            register_themed(path,{'id':asset_id,'scientific_type':'generic-method-symbol','style_family_id':style,
                'rights':'authorized_reuse','approval':'production_approved','origin':'Original geometric SVG authored by this demonstration script',
                'source_content_ids':[f'T{i+1}'],'reviewer':'Codex software demonstration','review_note':'Generic symbol of the named task',
                'contains_evidence':False},out/primary.replace('-','_')/'assets',plan)
            manifests.append(out/primary.replace('-','_')/'assets'/asset_id/'asset.json')
        owner_regions=[r for r in plan['regions'] if r['role']!='title']
        if primary=='center-hero-side-support':
            coordinates=[[.35,.22,.30,.65],[.04,.22,.26,.31],[.70,.22,.26,.31],[.04,.58,.26,.31],[.70,.58,.26,.31]]
            plan['canvas']['height']=1800
        else:
            coordinates=[[.05,.20,.90,.28]]+[[.05+i*.2325,.54,.2025,.36] for i in range(4)]
            plan['canvas']['height']=2200
        for i,(region,bounds) in enumerate(zip(owner_regions,coordinates)):
            region['bounds']=bounds;region['asset_ids']=[f'demo-icon-{i+1}']
        render_job(content,plan,[source_path],out/primary,manifests)
    return {'out':str(out),'same_content':True,'purpose':'synthetic illustrated demonstration; human aesthetic preference not measured'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);a=p.parse_args();print(run(a.out))
