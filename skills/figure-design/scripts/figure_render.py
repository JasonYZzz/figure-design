"""Chromium-shaped SVG, PNG and standalone HTML with a measured QA manifest."""
from __future__ import annotations
from base64 import b64encode
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
import time
from fontTools.ttLib import TTFont
from fontTools import subset
from playwright.sync_api import sync_playwright
from figure_common import ROOT, VERSION, figure_html, fingerprint, file_hash, write, schema_check, implementation_hash
from figure_sources import evidence
from figure_assets import resolve
from figure_plan import MIXED_ROUTES, figure_theme
from figure_geometry import route, intersects

FONT = ROOT / 'assets/fonts/NotoSansCJKsc-Regular.otf'
RELATIONS = {'sequence': ('步骤', 'arrow'), 'depends_on': ('依赖', 'arrow'), 'parallel': ('并行', 'none'),
             'tests': ('检验', 'open'), 'measures': ('测量', 'open'), 'supports': ('支持', 'open'),
             'activates': ('激活', 'arrow'), 'inhibits': ('抑制', 'bar'), 'feedback': ('反馈', 'arrow'),
             'association': ('关联', 'none')}
STATES = {'planned': '研究计划 · 拟开展', 'hypothesized': '研究假说 · 待验证', 'in_progress': '研究进行中',
          'observed': '观察性结果', 'validated': '已验证（以来源为准）', 'mixed': '混合研究状态', 'unknown': '研究状态待确认'}


def font_data(text):
    with TTFont(FONT,recalcTimestamp=False) as font:
        cmap = font.getBestCmap()
        missing = sorted({c for c in text if not c.isspace() and ord(c) not in cmap})
        if missing:
            raise ValueError('unsupported glyphs: ' + repr(''.join(missing)))
        options = subset.Options()
        options.layout_features = ['*']
        sub = subset.Subsetter(options=options)
        sub.populate(text=text)
        sub.subset(font)
        buffer = BytesIO();font.save(buffer)
    return b64encode(buffer.getvalue()).decode()


def bindings(content, plan):
    schema_check('composition-plan.schema.json', plan)
    if plan['status']=='rejected':
        raise ValueError('rejected composition cannot be rendered')
    if content['figure_id'] != plan['figure_id']:
        raise ValueError('figure ID mismatch')
    instances = {i['id']: i for i in content['label_instances']}
    placed = [iid for r in plan['regions'] for iid in r['label_instance_ids']]
    if len(placed) != len(set(placed)) or not set(placed) <= instances.keys():
        raise ValueError('unknown or duplicate label instance placement')
    if {i['id'] for i in instances.values() if i['required']} - set(placed):
        raise ValueError('missing required label instances')
    relations = {r['id']: r for r in content['relations']}
    regions = {r['id']: r for r in plan['regions']}
    edges = {e['relation_id']: e for e in plan['edges']}
    if not edges.keys() <= relations.keys() or {r['id'] for r in relations.values() if r['critical']} - edges.keys():
        raise ValueError('unknown or missing critical relations')
    for rid, edge in edges.items():
        relation = relations[rid]
        for region_key, owner_key in [('source_region_id', 'from_id'), ('target_region_id', 'to_id')]:
            if relation[owner_key] not in {instances[iid]['owner_id'] for iid in regions[edge[region_key]]['label_instance_ids']}:
                raise ValueError('relation endpoint/owner mismatch')
        if relation.get('condition_label_id') and not any(iid in placed and i['label_id'] == relation['condition_label_id'] and i['owner_id'] == rid for iid,i in instances.items()):
            raise ValueError('condition label instance missing')
    return instances, relations, regions


WRAP = r'''items => {
 const ctx = document.createElement('canvas').getContext('2d');
 const segmenter = new Intl.Segmenter('zh', {granularity:'grapheme'});
 return items.map(item => {
  ctx.font = `${item.weight} ${item.size}px FigureFont`;
  let lines = [], line = '';
  const graphemes = new Map(Array.from(segmenter.segment(item.text), g=>[g.index,g.segment]));
  const tokens=[];
  for(let offset=0;offset<item.text.length;) {
   const match=item.text.slice(offset).match(/^(?:\d+(?:\.\d+)?[ \t]*[A-Za-z\u0370-\u03ffμ%°]+(?:[\/^][A-Za-z0-9\u0370-\u03ffμ+-]+)*|[A-Za-z0-9\u0370-\u03ffμ]+(?:[\/._^+-][A-Za-z0-9\u0370-\u03ffμ]+)*)/u);
   const token=match?match[0]:graphemes.get(offset);tokens.push(token);offset+=token.length;
  }
  for (const ch of tokens) {
   if (ch === '\n') {lines.push(line+'\n');line='';continue;}
   if (line && ctx.measureText(line+ch).width > item.width) {lines.push(line);line='';}
   line+=ch;
  }
  if (line || !lines.length) lines.push(line);
  return {...item,lines,widths:lines.map(l=>ctx.measureText(l.replace(/\n/g,'')).width)};
 });
}'''


def render(content, plan, source_paths, out, asset_manifests=(), preflight=False):
    start = time.perf_counter()
    source_qa = evidence(content, source_paths)
    if source_qa['errors']:
        raise ValueError('\n'.join(source_qa['errors']))
    instances, relations, regions = bindings(content, plan)
    used_assets = {aid for r in regions.values() for aid in r.get('asset_ids', [])}
    route_name = plan['route']
    if plan.get('mode') == 'text' or route_name not in MIXED_ROUTES:
        raise ValueError('text diagrams use the bundled Diagram Design SKILL.md; run plan --mode text')
    assets = resolve(asset_manifests, content)
    if used_assets - assets.keys():
        raise ValueError('unresolved assets: ' + ', '.join(sorted(used_assets - assets.keys())))
    if route_name != 'image_first' and not used_assets:
        raise ValueError('mixed mode requires at least one approved asset bound to a region')
    if plan['route'] == 'image_first' and not used_assets:
        raise ValueError('image_first requires an actual approved base image; submit an image request first')
    if plan['route'] == 'image_first' and len(used_assets) != 1:
        raise ValueError('image_first uses one reviewed base image')
    if plan['route']=='image_first' and sum(len(r.get('asset_ids',[])) for r in regions.values())!=1:
        raise ValueError('place the image-first base image exactly once')
    composition = {'route': route_name, 'mode': 'mixed', 'html_template': 'figure-design',
                   'asset_placements': [
        {'region_id': rid, 'asset_id': aid} for rid, region in regions.items()
        for aid in region.get('asset_ids', [])
    ]}
    labels = {l['id']: l['text'] for l in content['labels']}
    state = STATES[content['study_status']]
    relation_types = sorted({r['type'] for r in relations.values()})
    legend = '   ·   '.join(RELATIONS[t][0] for t in relation_types)
    footer = state + (f'   ｜   关系：{legend}' if len(relation_types) > 1 else '')
    used_text = ''.join(labels.values()) + footer + legend
    if any(token in used_text for token in ('\\frac', '\\begin', '\\sqrt', '$$')):
        raise ValueError('unsupported_math: provide a verified rendered math asset or approved Unicode runs')
    encoded_font = font_data(used_text)
    style = figure_theme(plan)
    width, height = plan['canvas']['width'], plan['canvas']['height']
    bounds = {rid: [r['bounds'][0]*width,r['bounds'][1]*height,r['bounds'][2]*width,r['bounds'][3]*height] for rid,r in regions.items()}
    for a, ra in bounds.items():
        for b, rb in bounds.items():
            if a < b and intersects(ra, rb):
                raise ValueError(f'overlapping regions: {a}, {b}')
    objects, specs = [], []
    heading_roles = {'title', 'section', 'task'}
    for rid, region in regions.items():
        x,y,w,h = bounds[rid]
        pad = region['text_safe']['padding_px']
        aids = region.get('asset_ids', [])
        if len(aids) > 1:
            raise ValueError('one asset per region; split the region or provide a reviewed sheet')
        image_h = h * region.get('asset_fraction', .44) if aids and route_name != 'image_first' else 0
        if aids:
            asset = assets[aids[0]]
            owners = {instances[iid]['owner_id'] for iid in region['label_instance_ids']}
            if not owners.intersection(asset['source_content_ids']):
                raise ValueError('asset is bound to an unrelated region owner')
            if route_name != 'image_first' and (w <= 2*pad or image_h > h-2*pad):
                raise ValueError(f'asset_capacity: enlarge region {rid} or reduce its padding/asset fraction')
            objects.append({'id': 'image-'+rid, 'type': 'image', 'asset_id': aids[0],
                            'bounds': [0,0,width,height] if plan['route']=='image_first' else [x+pad,y+pad,w-2*pad,image_h], 'z_index': 0 if plan['route']=='image_first' else 2,
                            'source_content_ids': asset['source_content_ids']})
        cursor = y + pad + image_h + (16 if aids else 0)
        for iid in region['label_instance_ids']:
            size = 42 if region['role'] == 'title' else max(24, region['text_safe']['min_font_px'])
            specs.append({'id': iid, 'region': rid, 'text': labels[instances[iid]['label_id']],
                          'size': size, 'width': w-2*pad, 'start_y': cursor, 'pad': pad,
                          'weight': 600 if instances[iid]['role'] in heading_roles else 400})
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport={'width':width,'height':height}, device_scale_factor=1)
            page.route('**/*', lambda req: req.abort())
            font_css = f'@font-face{{font-family:FigureFont;src:url(data:font/otf;base64,{encoded_font}) format("opentype")}}'
            page.set_content(f'<style>{font_css}</style><span style="font-family:FigureFont">文字</span>')
            page.evaluate('document.fonts.ready')
            page.evaluate('document.fonts.load("24px FigureFont")')
            shaped = page.evaluate(WRAP, specs)
            cursors = {}
            for spec in shaped:
                rid = spec['region'];x,y,w,h = bounds[rid]
                cursor = cursors.get(rid, spec['start_y'])
                line_height = spec['size']*1.42
                if len(spec['lines']) > regions[rid]['text_safe']['max_lines'] or max(spec['widths']) > spec['width']+.5 or cursor+len(spec['lines'])*line_height > y+h-spec['pad']:
                    raise ValueError(f'text_capacity: {spec["id"]} does not fit {rid}; enlarge/recompose, do not alter approved text')
                obj = {'id': 'label-'+spec['id'], 'type': 'text', 'label_instance_id': spec['id'],
                       'source_content_ids': [instances[spec['id']]['owner_id']], 'region_id': rid,
                       'bounds': [x+spec['pad'],cursor,spec['width'],len(spec['lines'])*line_height],
                       'text': spec['text'], 'lines':spec['lines'], 'font_size':spec['size'], 'line_height':line_height, 'z_index':4}
                objects.append(obj)
                cursors[rid] = cursor + len(spec['lines'])*line_height + 16
            connector_obstacles=[]
            for edge in plan['edges']:
                relation = relations[edge['relation_id']]
                points = route(bounds[edge['source_region_id']],bounds[edge['target_region_id']],list(bounds.values())+connector_obstacles,(width,height))
                for a,b in zip(points,points[1:]):
                    connector_obstacles.append([min(a[0],b[0])-1,min(a[1],b[1])-1,max(abs(a[0]-b[0]),2),max(abs(a[1]-b[1]),2)])
                objects.append({'id':'relation-'+relation['id'],'type':'connector','relation_id':relation['id'],
                                'source_content_ids':[relation['from_id'],relation['to_id']], 'points':points,
                                'relation_type':relation['type'],'evidence_state':relation['evidence_state'],
                                'condition_label_id':relation.get('condition_label_id'),'z_index':3})
            semantic_boxes=[]
            connectors=[o for o in objects if o['type']=='connector']
            for obj in connectors:
                other_lines=[]
                for other in connectors:
                    if other is obj:continue
                    for a,b in zip(other['points'],other['points'][1:]):
                        other_lines.append([min(a[0],b[0])-2,min(a[1],b[1])-2,max(abs(a[0]-b[0]),4),max(abs(a[1]-b[1]),4)])
                segments=sorted(zip(obj['points'],obj['points'][1:]),key=lambda pair:abs(pair[0][0]-pair[1][0])+abs(pair[0][1]-pair[1][1]),reverse=True)
                chosen=None
                for a,b in segments:
                    if abs(a[0]-b[0])+abs(a[1]-b[1])<30:continue
                    mx,my=(a[0]+b[0])/2,(a[1]+b[1])/2
                    offsets=[(-22,-30),(-22,8),(-22,-12)] if a[1]==b[1] else [(8,-12),(-52,-12),(-22,-12)]
                    for dx,dy in offsets:
                        box=[mx+dx,my+dy,44,24]
                        if min(box[0],box[1])<0 or box[0]+44>width or box[1]+24>height:continue
                        if not any(intersects(box,r) for r in list(bounds.values())+semantic_boxes+other_lines):chosen=box;break
                    if chosen:break
                if chosen is None:raise ValueError('relation_label_capacity: add space for '+obj['relation_id'])
                obj['semantic_label_bounds']=chosen;semantic_boxes.append(chosen)
            scene = {'schema_version':'1.1','figure_id':content['figure_id'],'canvas':plan['canvas'],
                     'source_content_hash':fingerprint(content),'plan_hash':fingerprint(plan), 'objects':objects,
                     'render_status':'draft','renderer_version':VERSION}
            schema_check('figure-scene-v1.1.schema.json',scene)
            code_hash = implementation_hash()
            render_hash = fingerprint({'scene':scene,'font':file_hash(FONT),'assets':{aid:assets[aid]['file_sha256'] for aid in used_assets},
                                       'style':style,'code':code_hash,'chromium':browser.version})
            svg = ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','width':str(width),'height':str(height),
                                     'viewBox':f'0 0 {width} {height}','data-render-hash':render_hash,'data-status':'review_required',
                                     'data-mode':'mixed','role':'img','aria-labelledby':'figure-title'})
            ET.SubElement(svg,'title',{'id':'figure-title'}).text = content['purpose']
            ET.SubElement(svg,'style').text = font_css + 'text{font-family:FigureFont;white-space:pre}'
            defs=ET.SubElement(svg,'defs')
            for key,d in [('arrow','M0 0 L10 5 L0 10 Z'),('open','M0 0 L10 5 L0 10'),('bar','M9 0 L9 10')]:
                marker=ET.SubElement(defs,'marker',{'id':key,'viewBox':'0 0 12 12','refX':'10','refY':'5','markerWidth':'7','markerHeight':'7','orient':'auto'})
                ET.SubElement(marker,'path',{'d':d,'stroke':style['accent'],'fill':style['accent'] if key=='arrow' else 'none','stroke-width':'1.5'})
            paper = style['paper']
            ET.SubElement(svg,'rect',{'width':'100%','height':'100%','fill':paper})
            for rid,region in regions.items():
                x,y,w,h=bounds[rid]
                if region['role'] not in ('title','caption') and plan['route']!='image_first':
                    ET.SubElement(svg,'rect',{'x':str(x),'y':str(y),'width':str(w),'height':str(h),'rx':'6','fill':style['surface'],
                                              'stroke':style['border'],'stroke-width':'1.5'})
                    if region['role'] == 'hero':
                        ET.SubElement(svg,'rect',{'x':str(x),'y':str(y),'width':'5','height':str(h),'fill':style['accent']})
            for obj in sorted(objects,key=lambda x:x['z_index']):
                if obj['type']=='image':
                    asset=assets[obj['asset_id']];x,y,w,h=obj['bounds']
                    ET.SubElement(svg,'image',{'id':obj['id'],'x':str(x),'y':str(y),'width':str(w),'height':str(h),'preserveAspectRatio':'xMidYMid meet',
                        'href':f'data:{asset["mime"]};base64,'+b64encode(asset['_path'].read_bytes()).decode()})
                elif obj['type']=='connector':
                    points=obj['points'];attrs={'id':obj['id'],'data-relation-id':obj['relation_id'],'data-relation-type':obj['relation_type'],'data-evidence-state':obj['evidence_state'],
                        'd':'M '+' L '.join(f'{x},{y}' for x,y in points),'fill':'none','stroke':style['accent'],'stroke-width':'2.5','stroke-linejoin':'round'}
                    marker=RELATIONS[obj['relation_type']][1]
                    if marker!='none':attrs['marker-end']=f'url(#{marker})'
                    if obj['evidence_state'] in ('planned','hypothesis') or obj['relation_type']=='association':attrs['stroke-dasharray']='8 6'
                    ET.SubElement(svg,'path',attrs)
                    lx,ly,lw,lh=obj['semantic_label_bounds']
                    ET.SubElement(svg,'rect',{'x':str(lx),'y':str(ly),'width':str(lw),'height':str(lh),'rx':'3','fill':paper,'fill-opacity':'.96'})
                    ET.SubElement(svg,'text',{'data-relation-label':obj['relation_id'],'x':str(lx+6),'y':str(ly+18),'font-size':'16','fill':style['accent']}).text=RELATIONS[obj['relation_type']][0]
                else:
                    x,y,w,h=obj['bounds']
                    if plan['route']=='image_first':
                        ET.SubElement(svg,'rect',{'x':str(x-6),'y':str(y-4),'width':str(w+12),'height':str(h+8),'fill':style['surface']})
                    role = instances[obj['label_instance_id']]['role']
                    heading = role in heading_roles
                    element=ET.SubElement(svg,'text',{'id':obj['id'],'data-label-instance-id':obj['label_instance_id'],
                        'x':str(x),'y':str(y+obj['font_size']),'font-size':str(obj['font_size']),
                        'font-weight':'600' if heading else '400','fill':style['ink'] if heading else style['muted'],
                        '{http://www.w3.org/XML/1998/namespace}space':'preserve'})
                    for idx,line in enumerate(obj['lines']):
                        ET.SubElement(element,'tspan',{'x':str(x),'y':str(y+obj['font_size']+idx*obj['line_height'])}).text=line
            ET.SubElement(svg,'text',{'x':str(width*.05),'y':str(height*.985),'font-size':'18','fill':style['muted']}).text=footer
            xml=ET.tostring(svg,encoding='unicode')
            from vendor.ppt_master_svg_resources import svg_image_payload_error
            resource_error=svg_image_payload_error(xml.encode('utf-8'))
            if resource_error:raise ValueError('SVG resource closure: '+resource_error)
            document = figure_html(xml, content['purpose'])
            page.set_content(document)
            page.evaluate('document.fonts.ready')
            actual=page.evaluate('''() => Array.from(document.querySelectorAll('[data-label-instance-id]')).map(e=>({id:e.dataset.labelInstanceId,text:e.textContent,bbox:(()=>{let b=e.getBBox();return [b.x,b.y,b.width,b.height]})()}))''')
            errors=[]
            semantic_actual=page.evaluate('''() => Array.from(document.querySelectorAll('[data-relation-label]')).map(e=>({id:e.dataset.relationLabel,text:e.textContent}))''')
            if {x['id']:x['text'] for x in semantic_actual}!={o['relation_id']:RELATIONS[o['relation_type']][0] for o in connectors}:
                errors.append('relation_semantic_label_mismatch')
            expected={iid:labels[instances[iid]['label_id']] for r in regions.values() for iid in r['label_instance_ids']}
            if {x['id']:x['text'] for x in actual}!=expected or len(actual)!=len(expected):errors.append('exact_label_manifest_mismatch')
            object_labels={o['label_instance_id']:o for o in objects if o['type']=='text'}
            for label in actual:
                x,y,w,h=label['bbox'];obj=object_labels[label['id']];rx,ry,rw,rh=bounds[obj['region_id']]
                if x < rx-.5 or y < ry-.5 or x+w > rx+rw+.5 or y+h > ry+rh+.5:errors.append('rendered_text_overflow:'+label['id'])
            for i,a in enumerate(actual):
                for b in actual[i+1:]:
                    if intersects(a['bbox'],b['bbox']):errors.append('label_overlap:'+a['id']+':'+b['id'])
            if preflight:
                if errors:
                    raise ValueError('\n'.join(errors))
                return {'status':'pass','render_hash':render_hash,'labels':len(actual),'relations':len(plan['edges']),
                        'composition':composition,'theme':style}
            out = Path(out)
            if out.exists() and any(out.iterdir()):
                raise ValueError('render output must be empty; use a new version directory')
            out.mkdir(parents=True,exist_ok=True)
            (out/'preview.svg').write_text(xml,encoding='utf-8')
            (out/'preview.html').write_text(document,encoding='utf-8')
            page.screenshot(path=str(out/'preview.png'),full_page=True)
            report={'schema_version':'1.1','status':'blocked' if errors else 'review_required','render_hash':render_hash,
                    'hard_gates':{'evidence_binding':True,'label_instances':len(actual),'exact_text':not any('manifest' in e for e in errors),
                                  'glyphs':True,'actual_text_fit':not errors,'asset_rights_metadata':True,'relation_bindings':True,
                                  'theme_contrast':True},
                    'errors':errors,'pending':['scientific_semantic_review','visual_review','user_acceptance']+(['asset_pixels_and_native_text_review'] if used_assets else [])+
                        (['native_image_text_and_arrows_review'] if plan['route']=='image_first' else []),
                    'label_manifest':actual,'relation_label_manifest':semantic_actual,'source_review':source_qa,'format':'hybrid_svg' if used_assets else 'vector_svg',
                    'metrics':{'render_wall_ms':round((time.perf_counter()-start)*1000,2),'paid_calls':0,'cache_hit':False,'scope':'local_render_only','upstream_model_cost':'unknown'},
                    'renderer':{'version':VERSION,'chromium':browser.version,'font_sha256':file_hash(FONT),'implementation_hash':code_hash},
                    'asset_hashes':{aid:assets[aid]['file_sha256'] for aid in used_assets},'composition':composition,'theme':style}
            report['checks_scope']='Native LabelInstance text and deterministic connectors; embedded asset text/data are subject to explicit asset review.'
            write(out/'figure-content.json',content);write(out/'composition-plan.json',plan);write(out/'scene.json',scene);write(out/'quality-report.json',report)
            write(out/'artifact-manifest.json',{'render_hash':render_hash,'files':{p.name:file_hash(p) for p in out.iterdir() if p.is_file()}})
            return report
        finally:
            browser.close()
