"""Local extraction and exact source binding; semantic interpretation belongs to Codex."""
from __future__ import annotations
from pathlib import Path
import errno
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from figure_common import file_hash, fingerprint, read, write, schema_check


PDF_PAGE_SEPARATOR = '\n\f\n'


def extract_text(path, *, provenance=None, transcripts=None):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError('source must be a local file of at most 100 MiB')
    ext = path.suffix.lower()
    if transcripts and ext != '.pdf':
        raise ValueError('PDF page transcripts require a PDF original')
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
        page_keys = {str(number) for number in range(1, len(reader.pages) + 1)}
        transcripts = transcripts or {}
        for number, text in transcripts.items():
            if (number not in page_keys or not isinstance(text, str) or not text.strip()
                or '\f' in text or re.search(r'[\ud800-\udfff\ufffd]', text)):
                raise ValueError(f'invalid verified UTF-8 transcript for PDF page {number}')
        pages = []
        for number, page in enumerate(reader.pages, 1):
            if str(number) in transcripts:
                pages.append(transcripts[str(number)].rstrip())
                continue
            try:
                raw = page.extract_text() or ''
                pages.append(raw.encode('utf-16-le', 'surrogatepass').decode('utf-16-le'))
            except UnicodeError:
                pages.append('\ud800')
        damaged = [number for number, page in enumerate(pages, 1) if re.search(r'[\ud800-\udfff]', page)]
        if damaged:
            converter = shutil.which('pdftotext')
            page_list = ', '.join(map(str, damaged))
            if not converter:
                raise ValueError(f'PDF has invalid Unicode on pages {page_list}; provide Poppler (pdftotext) or verified --pdf-page-text PAGE=FILE')
            incomplete = []
            for number in damaged:
                try:
                    recovered = subprocess.run([converter, '-f', str(number), '-l', str(number), '-enc', 'UTF-8',
                                                '-nopgbrk', '-layout', str(path.resolve()), '-'],
                                               capture_output=True, check=True, timeout=30).stdout.decode('utf-8')
                except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
                    raise ValueError(f'cannot recover PDF page {number}; provide verified --pdf-page-text {number}=FILE') from exc
                if not recovered.strip() or '\ufffd' in recovered:
                    incomplete.append(number)
                pages[number-1] = recovered.rstrip() or '\ufffd'
            if provenance is not None:
                provenance.update(pdf_fallback={'backend': 'poppler-pdftotext', 'pages': damaged, 'incomplete_pages': incomplete,
                                                'review': 'verify recovered pages against the original before citing'})
        if provenance is not None and transcripts:
            provenance['pdf_transcripts'] = {number: text.rstrip() for number, text in transcripts.items()}
        text = PDF_PAGE_SEPARATOR.join(pages)
    else:
        raise ValueError('supported inputs: UTF-8 .txt/.md, .docx and text PDFs; use Codex vision for scans')
    if not text.strip():
        raise ValueError('no extractable text; OCR/visual transcription needs a checked text source')
    return text


def ingest(path, out, *, transcripts=None):
    path, out = Path(path), Path(out)
    provenance = {}
    text = extract_text(path, provenance=provenance, transcripts=transcripts)
    ext = path.suffix.lower()
    digest = file_hash(path)
    target = out / digest
    original = 'original' + ext
    result = {'schema_version': '1.0', 'document_sha256': digest,
              'original': original, 'text': text, 'text_sha256': fingerprint(text),
              'extraction': ext[1:], 'offset_unit': 'unicode_codepoint',
              'status': 'needs_semantic_review', 'source_name': path.name, **provenance}
    snapshot = target / 'source.json'
    out.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        with TemporaryDirectory(dir=out) as tmp:
            staged = Path(tmp)/'snapshot'
            staged.mkdir()
            shutil.copyfile(path, staged/original)
            if file_hash(staged/original) != digest:
                raise ValueError('source changed during ingestion')
            write(staged/'source.json', result)
            try:
                staged.rename(target)
            except OSError as exc:
                if exc.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                    raise
    if not snapshot.is_file() or not (target/original).is_file():
        raise ValueError('incomplete source snapshot; preserve it and use a new output root')
    if file_hash(target/original) != digest:
        raise ValueError('immutable source snapshot was modified')
    if read(snapshot) != result:
        raise ValueError('source extraction changed; preserve the existing snapshot and use a new output root')
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
        provenance = {}
        if extract_text(original, provenance=provenance, transcripts=source.get('pdf_transcripts')) != source['text']:
            raise ValueError('snapshot text differs from re-extracted original')
        snapshots[source['document_sha256']] = {'text': source['text'], **provenance}
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
        page_start = snapshot['text'].count(PDF_PAGE_SEPARATOR, 0, start) + 1
        page_end = snapshot['text'].count(PDF_PAGE_SEPARATOR, 0, end) + 1
        incomplete = snapshot.get('pdf_fallback', {}).get('incomplete_pages', [])
        if '\ufffd' in source['excerpt'] or any(page_start <= page <= page_end for page in incomplete):
            errors.append(f"{source['id']}: unreadable PDF characters; use verified visual transcription for this excerpt")
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
    pdf_sources = [{'document_sha256': digest, 'fallback': snapshot.get('pdf_fallback'),
                    'transcribed_pages': [int(page) for page in snapshot.get('pdf_transcripts', {})]}
                   for digest, snapshot in snapshots.items() if 'pdf_fallback' in snapshot or 'pdf_transcripts' in snapshot]
    return {'status': 'pass' if not errors else 'blocked_content', 'errors': errors,
            'content_hash': fingerprint(content), 'semantic_review': 'required',
            **({'pdf_sources': pdf_sources} if pdf_sources else {}),
            'note': 'Exact excerpts prove provenance, not scientific truth or faithful paraphrase.'}
