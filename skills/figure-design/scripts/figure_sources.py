"""Local extraction and exact source binding; semantic interpretation belongs to Codex."""
from __future__ import annotations
from pathlib import Path
import re
import shutil
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from figure_common import file_hash, fingerprint, read, write, schema_check


def extract_text(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError('source must be a local file of at most 100 MiB')
    ext = path.suffix.lower()
    if ext in ('.txt', '.md'):
        text = path.read_text(encoding='utf-8')
    elif ext == '.docx':
        with ZipFile(path) as z:
            info = z.getinfo('word/document.xml')
            if info.file_size > 20 * 1024 * 1024:
                raise ValueError('DOCX document XML exceeds 20 MiB')
            xml = z.read(info)
            if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
                raise ValueError('XML entities are not supported')
            root = ET.fromstring(xml)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        def paragraph_text(paragraph):
            parts=[]
            for node in paragraph.iter():
                tag=node.tag.split('}')[-1]
                if tag=='t':parts.append(node.text or '')
                elif tag=='tab':parts.append('\t')
                elif tag in ('br','cr'):parts.append('\n')
            return ''.join(parts)
        text = '\n'.join(paragraph_text(p) for p in root.findall('.//w:p', ns))
    elif ext == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(path)
        if reader.is_encrypted or len(reader.pages) > 500:
            raise ValueError('encrypted or over-500-page PDF requires preprocessing')
        text = '\n\f\n'.join(page.extract_text() or '' for page in reader.pages)
    else:
        raise ValueError('supported inputs: UTF-8 .txt/.md, .docx and text PDFs; use Codex vision for scans')
    if not text.strip():
        raise ValueError('no extractable text; OCR/visual transcription needs a checked text source')
    return text


def ingest(path, out):
    path, out = Path(path), Path(out)
    text = extract_text(path)
    ext = path.suffix.lower()
    digest = file_hash(path)
    target = out / digest
    target.mkdir(parents=True, exist_ok=True)
    original = target / ('original' + ext)
    if original.exists() and file_hash(original) != digest:
        raise ValueError('immutable source snapshot was modified')
    if not original.exists():
        shutil.copyfile(path, original)
    result = {'schema_version': '1.0', 'document_sha256': digest,
              'original': original.name, 'text': text, 'text_sha256': fingerprint(text),
              'extraction': ext[1:], 'offset_unit': 'unicode_codepoint',
              'status': 'needs_semantic_review', 'source_name': path.name}
    snapshot = target / 'source.json'
    if snapshot.exists() and read(snapshot) != result:
        raise ValueError('source extraction changed; preserve the existing snapshot and use a new output root')
    write(snapshot, result)
    return {'source': str(snapshot), 'document_sha256': digest, 'characters': len(text),
            'next': 'Codex reads source.json and creates FigureContent using exact chars:start:end locators'}


def evidence(content, source_paths):
    schema_check('figure-content.schema.json', content)
    snapshots = {}
    for path in source_paths:
        path = Path(path)
        source = read(path)
        original = path.parent / source['original']
        if original.resolve().parent != path.parent.resolve():
            raise ValueError('source original path escapes snapshot')
        if file_hash(original) != source['document_sha256'] or fingerprint(source['text']) != source['text_sha256']:
            raise ValueError('source snapshot hash mismatch')
        if extract_text(original) != source['text']:
            raise ValueError('snapshot text differs from re-extracted original')
        snapshots[source['document_sha256']] = source
    errors = []
    for source in content['sources']:
        snapshot = snapshots.get(source['document_sha256'])
        match = re.fullmatch(r'chars:(\d+):(\d+)', source['locator'])
        if not snapshot or not match:
            errors.append(f'{source["id"]}: missing snapshot or exact chars:start:end locator')
            continue
        start, end = map(int, match.groups())
        if not 0 <= start < end <= len(snapshot['text']) or snapshot['text'][start:end] != source['excerpt']:
            errors.append(f'{source["id"]}: excerpt/span mismatch')
        if source['verification'] not in ('verified_exact', 'approved_user_brief'):
            errors.append(f'{source["id"]}: source is {source["verification"]}')
    for item in content['entities'] + content['tasks'] + content['relations']:
        if not item['source_ids']:
            errors.append(f'{item["id"]}: scientific object lacks a source')
    for label in content['labels']:
        if label['kind'] == 'verbatim':
            excerpts = [s['excerpt'] for s in content['sources'] if s['id'] in label['source_ids']]
            if not any(label['text'] in quote for quote in excerpts):
                errors.append(f'{label["id"]}: verbatim label not present in its source')
    owners = {x['owner_id'] for x in content['label_instances'] if x['required']}
    if any(t['id'] not in owners for t in content['tasks']):
        errors.append('every research task needs a required label instance')
    if content['study_status'] in ('planned', 'hypothesized'):
        if any(t['status'] in ('observed', 'validated') for t in content['tasks']):
            errors.append('planned/hypothesized figure contains a completed task')
        if any(r['evidence_state'] in ('observed', 'validated') for r in content['relations']):
            errors.append('planned/hypothesized figure contains an established relation')
    return {'status': 'pass' if not errors else 'blocked_content', 'errors': errors,
            'content_hash': fingerprint(content), 'semantic_review': 'required',
            'note': 'Exact excerpts prove provenance, not scientific truth or faithful paraphrase.'}
