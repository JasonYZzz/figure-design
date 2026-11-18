"""Synthetic research briefs for software verification; not experimental evidence."""
from pathlib import Path
from figure_common import read
from figure_sources import ingest


def make_case(root, number=0, count=4, relation_type='sequence'):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    domains=['水质传感系统','细胞培养流程','材料制备方法','城市环境研究']
    title=domains[number%4]+'研究计划（虚构测试）'
    names=['拟明确研究对象与对照条件','拟采集数据并检查质量','拟开展模型分析与验证','拟汇总指标并复核来源','拟进行独立重复验证'][:count]
    if number==1:names[1]='拟测量 α、β 信号；浓度 10 μmol/L'
    if number==2:names[2]=names[1]
    if number==3:names[1]='拟核对 A < B 与 C & D 的条件'
    text='软件验收专用虚构研究计划，不代表任何真实研究或结果。\n'+title+'\n'+'\n'.join(names)+'\n所有步骤拟开展；来源内容不含实测结果。'
    path=root/'brief.md';path.write_text(text,encoding='utf-8')
    snapshot=ingest(path,root/'sources')['source'];source=read(snapshot)
    sources=[]
    labels=[]
    for idx,label in enumerate([title]+names):
        start=text.index(label)
        sources.append({'id':f'S{idx}','document_sha256':source['document_sha256'],'locator':f'chars:{start}:{start+len(label)}','excerpt':label,'verification':'verified_exact'})
        labels.append({'id':f'L{idx}','text':label,'kind':'verbatim','approved':True,'source_ids':[f'S{idx}']})
    content={'schema_version':'1.0','figure_id':f'TEST-{number}','purpose':title,'domain':'synthetic-validation','study_status':'planned',
             'sources':sources,'entities':[],'tasks':[{'id':f'T{i+1}','title_label_id':f'L{i+1}','status':'planned','source_ids':[f'S{i+1}']} for i in range(count)],
             'relations':[{'id':f'R{i+1}','from_id':f'T{i+1}','to_id':f'T{i+2}','type':relation_type,'evidence_state':'planned','source_ids':[f'S{i+1}',f'S{i+2}'],'critical':True} for i in range(count-1)],
             'labels':labels,'label_instances':[{'id':'I0','label_id':'L0','owner_id':f'TEST-{number}','role':'title','required':True}]+
                 [{'id':f'I{i+1}','label_id':f'L{i+1}','owner_id':f'T{i+1}','role':'task','required':True} for i in range(count)]}
    return content,[snapshot]
