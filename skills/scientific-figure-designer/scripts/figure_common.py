"""Shared local file contracts for the standalone skill."""
from __future__ import annotations
import hashlib
from html import escape
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.6.0'
DIAGRAM_SKILL = ROOT / 'third_party/diagram-design/skills/diagram-design'
ARTIFACTS = ('preview.svg', 'preview.png', 'preview.html', 'figure-content.json',
             'composition-plan.json', 'scene.json', 'quality-report.json')


def implementation_hash():
    return fingerprint({p.relative_to(ROOT).as_posix(): file_hash(p)
        for p in sorted([*(ROOT/'scripts').rglob('*.py'), ROOT/'assets/layout-registry.yaml'])})


def figure_html(svg, title):
    title = escape(title)
    base = '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    return (f'<!DOCTYPE html><html lang="zh-CN"><head>{base}<title>{title}</title>'
            '<style>body{margin:0}svg{display:block;max-width:100%;height:auto}</style></head>'
            f'<body>{svg}</body></html>')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def inside(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('path escapes its resource root')
    return path


def schema_check(name, value):
    from validate_contract import validate
    errors = validate(read(ROOT / 'schemas' / name), value)
    if errors:
        raise ValueError('\n'.join(errors))
