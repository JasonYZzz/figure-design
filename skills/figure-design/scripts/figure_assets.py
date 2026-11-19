"""Local assets and an explicit ledger for Codex-hosted image operations."""
from __future__ import annotations
from pathlib import Path
import shutil
import os
import re
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from PIL import Image
from figure_common import fingerprint, file_hash, read, write, inside, schema_check
from vendor.ppt_master_svg_resources import svg_image_payload_error


def validate_image(path):
    path = Path(path)
    if path.stat().st_size > 30 * 1024 * 1024:
        raise ValueError('asset exceeds 30 MiB')
    if path.suffix.lower() == '.svg':
        data = path.read_bytes()
        if b'<!' in data:
            raise ValueError('SVG declarations/entities are unsupported')
        resource_error = svg_image_payload_error(data)
        if resource_error:
            raise ValueError('SVG resource closure: '+resource_error)
        root = ET.fromstring(data)
        allowed = {'svg', 'g', 'path', 'rect', 'line', 'circle', 'ellipse', 'polyline', 'polygon', 'defs',
                   'linearGradient', 'radialGradient', 'stop', 'clipPath', 'text', 'tspan', 'title', 'desc'}
        for e in root.iter():
            if e.tag.split('}')[-1] not in allowed:
                raise ValueError('unsupported SVG element')
            for key, value in e.attrib.items():
                if key.lower().startswith('on') or key.split('}')[-1] in ('href', 'style'):
                    raise ValueError('active SVG attributes are unsupported')
                if 'url(' in value and not re.fullmatch(r'url\(#[\w-]+\)', value):
                    raise ValueError('external SVG URL is unsupported')
        return 'image/svg+xml'
    with Image.open(path) as im:
        if im.format not in ('PNG', 'JPEG', 'WEBP') or im.width * im.height > 40_000_000:
            raise ValueError('unsupported asset format or dimensions')
        mime = Image.MIME[im.format]
        im.verify()
    return mime


def register(path, metadata, out):
    required = ('id', 'scientific_type', 'style_family_id', 'rights', 'approval', 'origin',
                'source_content_ids', 'reviewer', 'review_note', 'contains_evidence')
    if any(k not in metadata for k in required):
        raise ValueError('asset metadata requires: ' + ', '.join(required))
    if not re.fullmatch(r'[A-Za-z0-9_-]+', metadata['id']):
        raise ValueError('invalid asset ID')
    if metadata['rights'] != 'authorized_reuse' or metadata['approval'] != 'production_approved':
        raise ValueError('only explicitly authorized and reviewed assets enter the production registry')
    if not metadata['reviewer'] or not metadata['review_note'] or not metadata['origin'] or not metadata['source_content_ids']:
        raise ValueError('provenance, review and content binding must be supplied')
    if not isinstance(metadata['source_content_ids'],list) or any(not isinstance(x,str) for x in metadata['source_content_ids']) or not isinstance(metadata['contains_evidence'],bool):
        raise ValueError('source_content_ids must be a string array; contains_evidence must be boolean')
    path, out = Path(path), Path(out)
    mime = validate_image(path)
    digest = file_hash(path)
    folder = out / metadata['id']
    target = folder / ('image' + path.suffix.lower())
    record = {**metadata, 'file_sha256': digest, 'asset_path': target.name, 'mime': mime}
    schema_check('asset-record.schema.json',record)
    if folder.exists():
        current = read(folder / 'asset.json')
        if current['file_sha256'] == digest and all(current[k] == v for k, v in metadata.items()):
            return current
        raise ValueError('asset ID exists with different bytes or metadata; use a new version ID')
    folder.mkdir(parents=True)
    shutil.copyfile(path, target)
    write(folder / 'asset.json', record)
    return record


def theme_hash(theme):
    from figure_reference import ROLES
    return fingerprint({role: theme[role].lower() for role in ROLES if role in theme})


def register_themed(path, metadata, out, plan):
    from figure_plan import figure_theme
    path = Path(path)
    if path.suffix.lower() != '.svg' or path.stat().st_size > 30 * 1024 * 1024:
        raise ValueError('theme tokens require a local SVG of at most 30 MiB')
    schema_check('composition-plan.schema.json', plan)
    theme = figure_theme(plan)
    def resolve_token(match):
        role, variant = match[1], match[2]
        if role not in theme or not re.fullmatch(r'#[0-9a-fA-F]{6}', theme[role]):
            raise ValueError(f'unknown SVG theme token: {role}')
        if not variant:
            return theme[role]
        weight = .38 if variant == 'light' else .14
        return '#%02x%02x%02x' % tuple(
            round(int(theme[role][i:i+2],16)*weight + int(theme['paper'][i:i+2],16)*(1-weight))
            for i in (1,3,5))
    source = path.read_text(encoding='utf-8')
    payload, count = re.subn(r'\{\{figure:([a-z]+)(?:-(light|pale))?\}\}', resolve_token, source)
    if not count or '{{figure:' in payload:
        raise ValueError('provide valid SVG theme tokens such as {{figure:accent}}')
    with TemporaryDirectory() as tmp:
        resolved = Path(tmp)/'illustration.svg'
        resolved.write_text(payload, encoding='utf-8')
        return register(resolved, {**metadata, 'theme_sha256': theme_hash(theme)}, out)


def resolve(manifests, content):
    ids = {x['id'] for x in content['entities'] + content['tasks']}
    result = {}
    for manifest in manifests:
        manifest = Path(manifest)
        item = read(manifest)
        schema_check('asset-record.schema.json',item)
        path = inside(manifest.parent, item['asset_path'])
        if item['rights'] != 'authorized_reuse' or item['approval'] != 'production_approved':
            raise ValueError('asset rights/approval gate failed')
        if not set(item['source_content_ids']) <= ids or not item['source_content_ids']:
            raise ValueError('asset depicts an object absent from content')
        if file_hash(path) != item['file_sha256']:
            raise ValueError('asset hash mismatch')
        if validate_image(path)!=item.get('mime'):
            raise ValueError('asset MIME does not match the image')
        if item['id'] in result:
            raise ValueError('duplicate asset ID')
        result[item['id']] = {**item, '_path': path}
    return result


def request(content, entity_id, prompt, out, operation_id, budget):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',operation_id):raise ValueError('invalid operation ID')
    folder=Path(out)/operation_id;folder.mkdir(parents=True,exist_ok=True)
    lock=folder/'request.lock';descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(descriptor)
    try:
        return _request(content,entity_id,prompt,out,operation_id,budget)
    finally:
        lock.unlink(missing_ok=True)


def _request(content, entity_id, prompt, out, operation_id, budget):
    entities = {x['id']: x for x in content['entities'] + content['tasks']}
    if entity_id not in entities or not entities[entity_id]['source_ids']:
        raise ValueError('image requests require a source-bound entity/task')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', operation_id) or budget < 0:
        raise ValueError('invalid operation ID/budget')
    payload = {'operation_id': operation_id, 'content_hash': fingerprint(content), 'entity_id': entity_id,
               'prompt': prompt, 'budget_limit': budget, 'constraint': 'illustration only; no text, arrows, invented data or experimental results'}
    path = Path(out) / operation_id / 'operation.json'
    if path.exists():
        old = read(path)
        if old['request'] != payload:
            raise ValueError('idempotency key reused with a different request')
        return old
    operation = {'request': payload, 'status': 'prepared', 'provider': None, 'receipt': None,
                 'cost': 'unknown', 'image_sha256': None, 'paid_calls': 0}
    write(path, operation)
    return operation


def operation_update(path, status, receipt=None, image=None, provider=None):
    path=Path(path);lock=path.with_suffix('.lock')
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(descriptor)
    try:
        return _operation_update(path,status,receipt,image,provider)
    finally:
        lock.unlink(missing_ok=True)


def _operation_update(path, status, receipt=None, image=None, provider=None):
    current = read(path)
    allowed = {'prepared': {'submitted', 'cancelled'}, 'submitted': {'succeeded', 'unknown', 'failed'},
               'unknown': {'succeeded', 'failed', 'cancelled'}, 'failed': set(), 'cancelled': set(), 'succeeded': set()}
    if status not in allowed.get(current['status'], set()):
        raise ValueError('invalid transition; never automatically resubmit an unknown operation')
    if status == 'submitted':
        if not provider:
            raise ValueError('record provider before calling the tool')
        current['provider'] = provider
        current['paid_calls'] = 1
    if status == 'succeeded':
        if not receipt or not image:
            raise ValueError('completion requires actual receipt/tool result and image path')
        validate_image(image)
        current['image_sha256'] = file_hash(image)
        current['receipt'] = receipt
    current['status'] = status
    write(path, current)
    return current


def split_sheet(path, boxes, out):
    """Explicit rectangles only; crops remain candidates, never automatic production assets."""
    path,out=Path(path),Path(out)
    if out.exists():raise ValueError('sheet output exists')
    validate_image(path)
    if path.suffix.lower()=='.svg':raise ValueError('sheet splitting requires a raster image')
    records=[]
    with Image.open(path) as original:
        im=original.convert('RGBA')
        for item in boxes:
            if not re.fullmatch(r'[A-Za-z0-9_-]+',item['id']):raise ValueError('invalid crop ID')
            x,y,w,h=item['bounds']
            if not all(isinstance(v,int) for v in (x,y,w,h)) or min(x,y)<0 or min(w,h)<=0 or x+w>im.width or y+h>im.height:
                raise ValueError('invalid crop bounds')
        if len({item['id'] for item in boxes})!=len(boxes):raise ValueError('duplicate crop ID')
        out.mkdir(parents=True)
        for item in boxes:
            x,y,w,h=item['bounds'];crop=im.crop((x,y,x+w,y+h));target=out/(item['id']+'.png');crop.save(target)
            alpha=crop.getchannel('A');edge=[alpha.getpixel((i,0)) for i in range(w)]+[alpha.getpixel((i,h-1)) for i in range(w)]+[alpha.getpixel((0,i)) for i in range(h)]+[alpha.getpixel((w-1,i)) for i in range(h)]
            records.append({'id':item['id'],'path':target.name,'bounds':item['bounds'],'sheet_sha256':file_hash(path),
                            'file_sha256':file_hash(target),'approval':'candidate','rights':'unknown',
                            'opaque_border_fraction':sum(v>0 for v in edge)/len(edge),'review_required':['rights','scientific_object','crop_completeness','edge_quality']})
    write(out/'candidates.json',records)
    return records
