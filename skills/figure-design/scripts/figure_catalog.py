"""Portable SQLite reference catalog with append-only review history."""
from __future__ import annotations
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from html import escape
from base64 import b64encode
from PIL import Image, ImageOps, ImageDraw
from inventory_refs import inventory
from figure_common import canonical, fingerprint, inside, read, write

TAG_FIELDS = ('domain_tags', 'figure_type_tags', 'composition_tags', 'asset_tags')


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('CREATE TABLE IF NOT EXISTS refs (id TEXT PRIMARY KEY, sha TEXT NOT NULL, record TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, ref_id TEXT, event TEXT NOT NULL)')
    return db


def index(root, catalog):
    root = Path(root).resolve()
    if Path(catalog).resolve().is_relative_to(root):
        raise ValueError('catalog must be outside original images')
    rows, errors = inventory(root)
    if errors:
        raise ValueError(canonical(errors))
    with connect(catalog) as db:
        for row in rows:
            row['id'] = 'ref-' + row['sha256'][:20]
            old = db.execute('SELECT record FROM refs WHERE id=?', (row['id'],)).fetchone()
            if old:
                old = json.loads(old[0])
                old['paths'] = sorted(set(old.get('paths', [old['path']])) | {row['path']})
                db.execute('UPDATE refs SET record=? WHERE id=?', (canonical(old), row['id']))
            else:
                row['paths'] = [row['path']]
                row['observations'], row['hypotheses'] = [], []
                db.execute('INSERT INTO refs VALUES (?,?,?)', (row['id'], row['sha256'], canonical(row)))
    return {'indexed_images': len(rows), 'errors': errors, 'catalog': str(catalog)}


def search(catalog, query='', limit=5, reviewed_only=False, require=None):
    if not Path(catalog).is_file():
        raise ValueError('catalog not found; run refs-index first')
    with connect(catalog) as db:
        rows = [json.loads(row[0]) for row in db.execute('SELECT record FROM refs ORDER BY id')]
    if query.strip() or require:
        from figure_retrieval import rank
        ranked = rank(rows, catalog, query, limit, reviewed_only, require)
        if ranked is not None:
            return ranked
        if require:
            raise ValueError('structured constraints require a compiled knowledge library')
    words = query.lower().split()
    for row in rows:
        tags = ' '.join(t for key in TAG_FIELDS for t in row.get(key, []))
        text = (tags + ' ' + ' '.join(row.get('observations', []))).lower()
        row['retrieval_score'] = sum(word in text for word in words) + (0.25 if row['review_status'] == 'human_approved' else 0)
    if reviewed_only:
        rows = [row for row in rows if row['review_status'] == 'human_approved']
    if words:
        rows = [row for row in rows if row['retrieval_score'] >= 1]
    return sorted(rows, key=lambda row: (-row['retrieval_score'], row['id']))[:limit]


def annotate(catalog, document):
    if document.get('reviewer_kind') not in ('model', 'human') or not document.get('reviewer'):
        raise ValueError('reviewer and reviewer_kind model/human required')
    if document['reviewer_kind'] == 'human' and not document.get('attestation'):
        raise ValueError('human review requires the actual reviewer attestation')
    with connect(catalog) as db:
        for item in document['records']:
            result = db.execute('SELECT record FROM refs WHERE id=?', (item['id'],)).fetchone()
            if not result:
                raise ValueError('unknown reference: ' + item['id'])
            record = json.loads(result[0])
            if item.get('sha256') != record['sha256']:
                raise ValueError('annotation image hash mismatch')
            if any(key in item for key in ('license_state', 'approval', 'review_status')):
                raise ValueError('classification cannot change rights or set its own review status')
            for key in TAG_FIELDS + ('observations', 'hypotheses'):
                values = item.get(key, [])
                if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                    raise ValueError(key + ' must be an array of strings')
                record[key] = values
            density = item.get('text_density', 'unknown')
            if density not in ('unknown', 'low', 'medium', 'high'):
                raise ValueError('invalid density')
            record['text_density'] = density
            record['review_status'] = 'human_approved' if document['reviewer_kind'] == 'human' else 'auto_proposed'
            event = {'at': datetime.now(timezone.utc).isoformat(), 'reviewer': document['reviewer'],
                     'reviewer_kind': document['reviewer_kind'], 'annotation': item,
                     'attestation': document.get('attestation'), 'previous_hash': fingerprint(json.loads(result[0]))}
            db.execute('INSERT INTO events(ref_id,event) VALUES (?,?)', (item['id'], canonical(event)))
            db.execute('UPDATE refs SET record=? WHERE id=?', (canonical(record), item['id']))
    return {'applied': len(document['records']), 'rights_changed': False}


def sheets(catalog, image_root, out, count=30):
    rows = search(catalog, limit=10000)
    library=Path(catalog).resolve().parent
    enriched=[]
    for row in rows:
        path=library/'analyses'/(row['id']+'.json')
        analysis=read(path) if path.is_file() else {}
        facets=analysis.get('facets',{})
        key=tuple(facets.get(k,'unknown') for k in ('domain','layout','media','density'))
        enriched.append((row,key,analysis))
    from collections import Counter
    seen=Counter();chosen=[];analyses={}
    while enriched and len(chosen)<count:
        enriched.sort(key=lambda item:(sum(seen[(i,v)] for i,v in enumerate(item[1])),item[0]['id']))
        row,key,analysis=enriched.pop(0);chosen.append(row);analyses[row['id']]=analysis
        seen.update((i,v) for i,v in enumerate(key))
    out = Path(out)
    if out.resolve().is_relative_to(Path(image_root).resolve()):
        raise ValueError('review output must be outside originals')
    out.mkdir(parents=True, exist_ok=True)
    html = ['<!doctype html><meta charset="utf-8"><title>Reference review</title><style>body{font:16px sans-serif;background:#f4f5f3}article{padding:24px;background:white;margin:20px}img{max-width:100%;max-height:700px}code{word-break:break-all}</style><h1>Reference candidates — human review pending</h1>']
    for row in chosen:
        path = inside(image_root, row['path'])
        from figure_common import file_hash
        if file_hash(path) != row['sha256']:
            raise ValueError('reference bytes changed')
        import io
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((1400, 1400))
            buffer = io.BytesIO(); im.save(buffer, 'JPEG', quality=85)
        analysis=analyses[row['id']]
        details=escape('；'.join(o['text'] for o in analysis.get('observations',[])))
        html.append(f'<article><h2>{escape(row["path"])}</h2><code>{row["id"]}</code><p>{details}</p><p>{escape(" / ".join(row["composition_tags"]))}</p><img alt="Reference for review" src="data:image/jpeg;base64,{b64encode(buffer.getvalue()).decode()}"></article>')
    (out / 'review.html').write_text('\n'.join(html), encoding='utf-8')
    write(out / 'annotations.json', {'reviewer': '', 'reviewer_kind': 'human', 'attestation': '',
        'records': [{k: row[k] for k in ('id', 'sha256', *TAG_FIELDS, 'text_density', 'observations', 'hypotheses')} for row in chosen]})
    import copy
    changes=[]
    for row in chosen:
        old=analyses[row['id']]
        if old:
            item=copy.deepcopy(old);item['review_status']='human_approved'
            changes.append({'expected_previous_hash':fingerprint(old),'analysis':item})
    write(out/'analysis-review.json',{'reviewer':'','reviewer_kind':'human','attestation':'','records':changes})
    return {'selected': len(chosen), 'html': str(out / 'review.html'), 'status': 'human_review_pending'}
