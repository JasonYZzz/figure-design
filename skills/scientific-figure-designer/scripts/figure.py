#!/usr/bin/env python3
"""Standalone Scientific Figure Designer CLI. Semantic tasks run in Codex."""
from __future__ import annotations
import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
from figure_common import ARTIFACTS, DIAGRAM_TEMPLATE, ROOT, VERSION, figure_html, read, write, fingerprint, file_hash, inside, implementation_hash


def verify_bundle(folder):
    folder = Path(folder)
    manifest = read(folder / 'artifact-manifest.json')
    for relative, digest in manifest['files'].items():
        if file_hash(inside(folder, relative)) != digest:
            raise ValueError('artifact modified: ' + relative)
    report = read(folder / 'quality-report.json')
    if report['render_hash'] != manifest['render_hash']:
        raise ValueError('render hash mismatch')
    return report


def render_job(content, plan, sources, out, assets=()):
    from figure_render import render
    from figure_sources import evidence
    from figure_assets import resolve
    out = Path(out)
    checked = evidence(content, sources)
    if checked['errors']:
        raise ValueError('\n'.join(checked['errors']))
    if out.exists():
        report = verify_bundle(out)
        if report['renderer'].get('implementation_hash') != implementation_hash():
            raise ValueError('renderer implementation changed; render into a new output version')
        if report['renderer']['font_sha256'] != file_hash(ROOT/'assets/fonts/NotoSansCJKsc-Regular.otf'):
            raise ValueError('font changed; render into a new output version')
        if read(out/'figure-content.json') != content or read(out/'composition-plan.json') != plan:
            raise ValueError('output already contains a different version; use a new directory')
        resolved = resolve(assets, content)
        used = {aid for r in plan['regions'] for aid in r.get('asset_ids', [])}
        if {aid:resolved[aid]['file_sha256'] for aid in used} != report['asset_hashes']:
            raise ValueError('asset bytes changed; use a new output directory')
        report['metrics']['cache_hit'] = True
        return report
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = out.parent / (out.name + '.lock')
    descriptor = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.close(descriptor)
    stage = Path(tempfile.mkdtemp(prefix=out.name+'-working-', dir=out.parent))
    try:
        report = render(content, plan, sources, stage, assets)
        for path in sources:
            path = Path(path);snapshot = read(path)
            target = stage/'sources'/snapshot['document_sha256'];target.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target/'source.json')
            shutil.copyfile(path.parent/snapshot['original'],target/snapshot['original'])
        for path in assets:
            path = Path(path);record=read(path)
            target=stage/'assets'/record['id'];target.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target/'asset.json')
            shutil.copyfile(inside(path.parent,record['asset_path']),target/record['asset_path'])
        write(stage/'artifact-manifest.json',{'render_hash':report['render_hash'],
            'files':{p.relative_to(stage).as_posix():file_hash(p) for p in stage.rglob('*') if p.is_file() and p.name!='artifact-manifest.json'}})
        if out.exists():
            raise ValueError('output appeared during render; refusing to replace it')
        os.rename(stage,out)
        return report
    except Exception as exc:
        write(stage/'failure.json',{'status':'failed','error':str(exc),'paid_calls':0,'retry':'repeat with the same output; completed outputs are never overwritten'})
        raise ValueError(f'{exc}; diagnostics: {stage}') from exc
    finally:
        lock.unlink(missing_ok=True)


def export(folder, out, review=None, final=False):
    folder,out=Path(folder),Path(out)
    report=verify_bundle(folder)
    if report['errors']:
        raise ValueError('hard QA failure blocks export')
    if final:
        decision=read(review) if review else {}
        if decision.get('render_hash')!=report['render_hash'] or decision.get('decision')!='accepted' or decision.get('reviewer_kind')!='human' or not decision.get('attestation'):
            raise ValueError('final export needs actual human acceptance bound to this render hash')
        if any(not decision.get(k) for k in ('scientific_review','visual_review','asset_review')):
            raise ValueError('science, visual and asset review must all be recorded')
        if 'native_image_text_and_arrows_review' in report['pending'] and not decision.get('image_first_review'):
            raise ValueError('image-first final requires specific native text and arrow review')
    if out.exists():raise ValueError('export path already exists')
    files = read(folder/'artifact-manifest.json')['files']
    legacy_html = None
    if 'preview.html' not in files and 'preview.pdf' in files:
        legacy_html = figure_html((folder/'preview.svg').read_text(encoding='utf-8'),
                                  read(folder/'figure-content.json')['purpose'])
    if set(ARTIFACTS) - files.keys() - ({'preview.html'} if legacy_html is not None else set()):
        raise ValueError('artifact manifest does not include all required export files')
    out.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(out,'x',ZIP_DEFLATED) as z:
        for name in ARTIFACTS:
            if name == 'preview.html' and legacy_html is not None:
                z.writestr(name, legacy_html)
            else:
                z.write(folder/name,name)
        z.writestr('export-status.json',json.dumps({'status':'accepted' if final else 'review_required','render_hash':report['render_hash'],
            'notice':'Source excerpts may be confidential. Original source documents are not included.'},ensure_ascii=False,indent=2))
        if final:z.write(review,'acceptance.json')
    return {'export':str(out),'sha256':file_hash(out),'status':'accepted' if final else 'review_required'}


def pack(out, references=None):
    out=Path(out)
    if out.exists():raise ValueError('package already exists; choose a new version/path')
    if out.resolve().is_relative_to(ROOT):raise ValueError('package output must be outside the skill')
    knowledge=ROOT/'assets/reference-library/knowledge'
    active=read(knowledge/'current.json')['generation'] if (knowledge/'current.json').exists() else None
    library=ROOT/'assets/reference-library'
    if active:
        from figure_knowledge import lint
        if lint(library,library/'catalog.sqlite')['status']!='ok':
            raise ValueError('reference knowledge or original images are invalid')
    allowed={'scripts','references','schemas','assets','tests','agents','third_party'}
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='.DS_Store'
           and not any(p.relative_to(ROOT).is_relative_to('assets/reference-library/'+d) for d in ('images','thumbnails','crops','review','private','feedback'))
           and not (p.is_relative_to(library) and p.relative_to(library).parts[0] not in {'catalog.sqlite','library.json','taxonomy.yaml','patterns.json','analyses','analysis-events','knowledge'})
           and not (p.is_relative_to(library) and p.suffix.lower()=='.html' and p!=knowledge/'generations'/str(active)/'index.html')
           and not any(part.startswith('.working-') for part in p.parts)
           and not (p.is_relative_to(knowledge/'generations') and active and p.relative_to(knowledge/'generations').parts[0]!=active)
           and not (p.suffix.lower() in ('.png','.jpg','.jpeg','.webp','.svg','.pdf') and p.relative_to(ROOT).is_relative_to('assets/reference-library'))
           and (p.relative_to(ROOT).parts[0] in allowed
                or p.relative_to(ROOT).as_posix() in ('SKILL.md','LICENSE','requirements.txt','requirements.lock','README.md'))]
    if any(p.is_symlink() or not p.resolve().is_relative_to(ROOT.resolve()) for p in files):
        raise ValueError('package may not include symlinks or files outside the skill')
    manifest={'version':VERSION,'files':{p.relative_to(ROOT).as_posix():file_hash(p) for p in files},
              'reference_images_included':bool(references),'reference_rights':'local_reference_only; no redistribution rights inferred'}
    images=[]
    if references:
        from inventory_refs import inventory
        rows,errors=inventory(Path(references))
        if errors:raise ValueError('reference pack contains invalid inputs')
        from figure_catalog import search
        records=search(ROOT/'assets/reference-library/catalog.sqlite',limit=10000)
        expected={path:row['sha256'] for row in records for path in row.get('paths',[row['path']])}
        if {row['path']:row['sha256'] for row in rows}!=expected:
            raise ValueError('reference images do not match the bundled catalog; index and review the intended library first')
        for row in rows:
            relative='assets/reference-library/images/'+row['path'];images.append((Path(references)/row['path'],relative))
            manifest['files'][relative]=row['sha256']
    out.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(out,'x',ZIP_DEFLATED) as z:
        for p in files:z.write(p,'scientific-figure-designer/'+p.relative_to(ROOT).as_posix())
        for p,relative in images:z.write(p,'scientific-figure-designer/'+relative)
        z.writestr('scientific-figure-designer/package-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    return {'package':str(out),'sha256':file_hash(out),'files':len(manifest['files']),'version':VERSION}


def doctor():
    import importlib.util
    missing=[name for name in ('playwright','fontTools','pypdf','PIL','yaml','jsonschema') if importlib.util.find_spec(name) is None]
    if missing:return {'version':VERSION,'ready':False,'missing_modules':missing,'action':'python -m pip install -r '+str(ROOT/'requirements.txt')}
    from figure_render import FONT
    from playwright.sync_api import sync_playwright
    result={'version':VERSION,'python':sys.version.split()[0],'font':FONT.is_file(),'catalog':(ROOT/'assets/reference-library/catalog.sqlite').is_file(),
            'reference_images':(ROOT/'assets/reference-library/images').is_dir(),'diagram_design_template':DIAGRAM_TEMPLATE.is_file(),
            'codex_semantic_tools':'host_provided','image_generation':'host_capability_required; no API key required by this CLI'}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();result['chromium']=browser.version;browser.close()
    except Exception as exc:
        result['chromium']=False;result['action']='python -m playwright install chromium';result['error']=str(exc).splitlines()[0]
    result['ready']=bool(result['font'] and result['chromium'] and result['diagram_design_template'])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    c=sub.add_parser('ingest');c.add_argument('--input',required=True);c.add_argument('--out',required=True)
    c=sub.add_parser('refs-index');c.add_argument('--input',required=True);c.add_argument('--catalog',required=True)
    c=sub.add_parser('refs-search');c.add_argument('--catalog',default=str(ROOT/'assets/reference-library/catalog.sqlite'));c.add_argument('--images',default=str(ROOT/'assets/reference-library/images'));c.add_argument('--query',default='');c.add_argument('--limit',type=int,default=5);c.add_argument('--reviewed-only',action='store_true');c.add_argument('--brief');c.add_argument('--require',action='append',default=[],metavar='FACET=VALUE')
    for name in ('refs-build','refs-lint','refs-analyze-import'):
        c=sub.add_parser(name);c.add_argument('--catalog',default=str(ROOT/'assets/reference-library/catalog.sqlite'));c.add_argument('--library',default=str(ROOT/'assets/reference-library'));c.add_argument('--images');c.add_argument('--annotations')
    c=sub.add_parser('refs-feedback');c.add_argument('--input',required=True);c.add_argument('--out',required=True)
    c=sub.add_parser('refs-annotate');c.add_argument('--catalog',required=True);c.add_argument('--annotations',required=True)
    c=sub.add_parser('refs-review');c.add_argument('--catalog',default=str(ROOT/'assets/reference-library/catalog.sqlite'));c.add_argument('--images',default=str(ROOT/'assets/reference-library/images'));c.add_argument('--out',required=True);c.add_argument('--count',type=int,default=30)
    c=sub.add_parser('content-check');c.add_argument('--content',required=True);c.add_argument('--sources',nargs='+',required=True)
    c=sub.add_parser('research-brief');c.add_argument('--reference-query');c.add_argument('--catalog',default=str(ROOT/'assets/reference-library/catalog.sqlite'));c.add_argument('--content',required=True);c.add_argument('--sources',nargs='+',required=True);c.add_argument('--out',required=True)
    c=sub.add_parser('plan');c.add_argument('--references');c.add_argument('--content',required=True);c.add_argument('--out',required=True);c.add_argument('--layout');c.add_argument('--style',default='biomedicine-academic');c.add_argument('--variant',default='balanced');c.add_argument('--route',choices=['text_structured','asset_composite','strict_scientific','image_first'])
    c.add_argument('--mode', choices=['text','mixed'], help='Select text-only diagrams or diagrams with approved illustrations')
    c.add_argument('--diagram-type', choices=['architecture','roadmap'], help='Choose the text diagram layout family')
    for name in ('preflight','render'):
        c=sub.add_parser(name);c.add_argument('--content',required=True);c.add_argument('--plan',required=True);c.add_argument('--sources',nargs='+',required=True);c.add_argument('--assets',nargs='*',default=[])
        c.add_argument('--out',required=name=='render',default='unused')
    c=sub.add_parser('qa');c.add_argument('--render',required=True)
    c=sub.add_parser('patch-label');c.add_argument('--render',required=True);c.add_argument('--expected-render-hash',required=True);c.add_argument('--label',required=True);c.add_argument('--text',required=True);c.add_argument('--reason',required=True);c.add_argument('--out',required=True)
    c=sub.add_parser('export');c.add_argument('--render',required=True);c.add_argument('--out',required=True);c.add_argument('--review');c.add_argument('--final',action='store_true')
    c=sub.add_parser('asset-register');c.add_argument('--input',required=True);c.add_argument('--metadata',required=True);c.add_argument('--out',required=True)
    c=sub.add_parser('asset-sheet');c.add_argument('--input',required=True);c.add_argument('--boxes',required=True);c.add_argument('--out',required=True)
    c=sub.add_parser('asset-search');c.add_argument('--library',required=True);c.add_argument('--type',required=True);c.add_argument('--style')
    c=sub.add_parser('data-chart');c.add_argument('--input',required=True);c.add_argument('--out',required=True);c.add_argument('--x',required=True);c.add_argument('--y',required=True);c.add_argument('--title',required=True);c.add_argument('--kind',choices=['line','bar'],default='line')
    c=sub.add_parser('image-request');c.add_argument('--content',required=True);c.add_argument('--entity',required=True);c.add_argument('--prompt',required=True);c.add_argument('--out',required=True);c.add_argument('--operation-id',required=True);c.add_argument('--budget',required=True,type=float)
    c=sub.add_parser('image-status');c.add_argument('--operation',required=True);c.add_argument('--status',required=True,choices=['submitted','succeeded','unknown','failed','cancelled']);c.add_argument('--provider');c.add_argument('--receipt');c.add_argument('--image')
    c=sub.add_parser('pack');c.add_argument('--out',required=True);c.add_argument('--references')
    for command_parser in sub.choices.values():command_parser.add_argument('--dry-run',action='store_true',help='Describe the request without executing or writing files')
    a=p.parse_args()
    try:
        if a.dry_run:
            print(json.dumps({'status':'not_executed','request':vars(a),'paid_calls':0},ensure_ascii=False,indent=2));return 0
        if a.command=='doctor':result=doctor()
        elif a.command=='ingest':
            from figure_sources import ingest
            result=ingest(a.input,a.out)
        elif a.command=='refs-index':
            from figure_catalog import index
            result=index(a.input,a.catalog)
        elif a.command=='refs-search':
            from figure_catalog import search
            if not 1<=a.limit<=10000:raise ValueError('limit must be 1–10000')
            from figure_retrieval import resolve_images
            require={}
            for value in a.require:
                if '=' not in value: raise ValueError('require must be FACET=VALUE')
                key,value=value.split('=',1)
                if key in require: raise ValueError('duplicate required facet')
                require[key]=value
            brief=read(a.brief) if a.brief else {}
            request=brief.get('reference_requirements',{})
            require={**request.get('require',{}),**require}
            query=a.query or request.get('query','')
            result=resolve_images(search(a.catalog,query,a.limit,a.reviewed_only,require),a.images)
            if a.brief: result={'source_content_hash':brief['source_content_hash'],'query':query,'candidates':result,'status':'visual_review_pending'}
        elif a.command in ('refs-build','refs-lint','refs-analyze-import'):
            from figure_knowledge import build,lint,ingest_analyses
            if a.command=='refs-build':result=build(a.library,a.catalog)
            elif a.command=='refs-lint':result=lint(a.library,a.catalog,a.images)
            else:
                if not a.annotations:raise ValueError('--annotations required')
                result=ingest_analyses(a.library,a.catalog,read(a.annotations))
        elif a.command=='refs-feedback':
            from figure_retrieval import save_feedback
            result=save_feedback(read(a.input),a.out,ROOT/'assets/reference-library')
        elif a.command=='refs-annotate':
            from figure_catalog import annotate
            result=annotate(a.catalog,read(a.annotations))
        elif a.command=='refs-review':
            from figure_catalog import sheets
            if not 1<=a.count<=10000:raise ValueError('count must be 1–10000')
            result=sheets(a.catalog,a.images,a.out,a.count)
        elif a.command=='content-check':
            from figure_sources import evidence
            result=evidence(read(a.content),a.sources)
        elif a.command=='research-brief':
            from figure_research import research_brief
            if Path(a.out).exists():raise ValueError('research brief exists; use a new version path')
            result=research_brief(read(a.content),a.sources)
            if a.reference_query:
                from figure_retrieval import suggest
                result['reference_suggestions']=suggest(a.catalog,read(a.content),a.reference_query)
                result['reference_requirements']['query']=a.reference_query
            write(a.out,result)
        elif a.command=='plan':
            from figure_plan import MODE_ROUTES, candidates, make_plan, text_diagram_type
            content=read(a.content);out=Path(a.out)
            if out.exists():raise ValueError('plan output exists')
            suggestions=read(a.references) if a.references else None
            if suggestions and suggestions.get('source_content_hash')!=fingerprint(content):raise ValueError('reference suggestions bound to another content version')
            mode = a.mode or ('text' if a.diagram_type else None)
            route = a.route or MODE_ROUTES[mode or 'text'][0]
            if mode and route not in MODE_ROUTES[mode]:
                raise ValueError(f'route {route} is incompatible with mode {mode}')
            if a.diagram_type and mode != 'text':
                raise ValueError('--diagram-type requires text mode')
            diagram_type = (a.diagram_type or text_diagram_type(content)) if mode == 'text' else None
            options = {'variant': a.variant, 'route': route, 'mode': mode, 'diagram_type': diagram_type}
            plans=[{'plan':make_plan(content,a.layout,a.style,**options),'content_hash':fingerprint(content)}] if a.layout else candidates(content,a.style,suggestions,**options)
            out.mkdir(parents=True)
            for i,item in enumerate(plans):write(out/f'candidate-{i+1}.json',item['plan'])
            write(out/'selection.json',plans);result={'candidates':len(plans),'out':str(out),'route':route,
                'mode': mode or ('mixed' if route in ('asset_composite','image_first') else 'text'), 'diagram_type':diagram_type,
                'next':'Refine candidate layouts and bind route-required assets before preflight.'}
        elif a.command in ('preflight','render'):
            from figure_render import render
            result=render(read(a.content),read(a.plan),a.sources,a.out,a.assets,True) if a.command=='preflight' else render_job(read(a.content),read(a.plan),a.sources,a.out,a.assets)
        elif a.command=='qa':result=verify_bundle(a.render)
        elif a.command=='patch-label':
            folder=Path(a.render);report=verify_bundle(folder)
            if report['render_hash']!=a.expected_render_hash:raise ValueError('stale render hash; reload the current version')
            content=read(folder/'figure-content.json');found=False
            for label in content['labels']:
                if label['id']==a.label:
                    label['text']=a.text;label['kind']='approved_summary';found=True
            if not found:raise ValueError('label ID not found')
            result=render_job(content,read(folder/'composition-plan.json'),list(folder.glob('sources/*/source.json')),a.out,list(folder.glob('assets/*/asset.json')))
            write(Path(a.out)/'patch-event.json',{'previous_render_hash':report['render_hash'],'label_id':a.label,'reason':a.reason,'paid_calls':0,'review_invalidated':True})
        elif a.command=='export':result=export(a.render,a.out,a.review,a.final)
        elif a.command=='asset-register':
            from figure_assets import register
            result=register(a.input,read(a.metadata),a.out)
        elif a.command=='asset-sheet':
            from figure_assets import split_sheet
            result=split_sheet(a.input,read(a.boxes),a.out)
        elif a.command=='asset-search':
            result=[]
            for path in Path(a.library).glob('*/asset.json'):
                item=read(path)
                if item['scientific_type']==a.type and (not a.style or item['style_family_id']==a.style) and item['rights']=='authorized_reuse' and item['approval']=='production_approved':result.append({'manifest':str(path),**item})
        elif a.command=='data-chart':
            from figure_data import chart
            result=chart(a.input,a.out,a.x,a.y,a.title,a.kind)
        elif a.command=='image-request':
            from figure_assets import request
            result=request(read(a.content),a.entity,a.prompt,a.out,a.operation_id,a.budget)
        elif a.command=='image-status':
            from figure_assets import operation_update
            result=operation_update(a.operation,a.status,a.receipt,a.image,a.provider)
        elif a.command=='pack':result=pack(a.out,a.references)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if isinstance(result,dict) and (result.get('status') in ('blocked','blocked_content') or result.get('ready') is False):return 2
        return 0
    except (ValueError,OSError,KeyError,TypeError,ImportError) as exc:
        print(json.dumps({'status':'error','message':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
