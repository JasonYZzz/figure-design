"""Shared local file contracts for the standalone skill."""
from __future__ import annotations
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.5.0'
DIAGRAM_DESIGN = ROOT / 'third_party/diagram-design'
DIAGRAM_TEMPLATE = DIAGRAM_DESIGN / 'skills/diagram-design/assets/template.html'
DIAGRAM_LICENSE = DIAGRAM_DESIGN / 'LICENSE'
ARTIFACTS = ('preview.svg', 'preview.png', 'preview.html', 'figure-content.json',
             'composition-plan.json', 'scene.json', 'quality-report.json')


def implementation_hash():
    return fingerprint({p.relative_to(ROOT).as_posix(): file_hash(p)
        for p in sorted([*(ROOT/'scripts').rglob('*.py'), ROOT/'assets/layout-registry.yaml',
                         DIAGRAM_TEMPLATE, DIAGRAM_LICENSE])})


def figure_html(svg, title, diagram_type=None):
    title = escape(title)
    base = '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    if diagram_type is None:
        return (f'<!DOCTYPE html><html lang="zh-CN"><head>{base}<title>{title}</title>'
                '<style>body{margin:0}svg{display:block;max-width:100%;height:auto}</style></head>'
                f'<body>{svg}</body></html>')

    # Keep the upstream responsive frame and use the scientific SVG title and embedded font.
    template = DIAGRAM_TEMPLATE.read_text(encoding='utf-8')
    template = re.sub(r'^  <link[^\n]+\n', '', template, flags=re.MULTILINE)
    template = re.sub(r'^    (?:<p class="eyebrow">.*</p>|<h1>.*</h1>)\n', '', template, flags=re.MULTILINE)
    template = template.replace('<html lang="en">', '<html lang="zh-CN">')
    frame_style = 'body{padding:0}.frame{max-width:none}svg{min-width:0;height:auto}'
    template = template.replace('</head>', f'<style>{frame_style}</style></head>', 1)
    template = template.replace('<title>Diagram</title>', f'<title>{title}</title>', 1)
    template = template.replace('<div class="diagram-container">', f'<div class="diagram-container" data-diagram-type="{diagram_type}">', 1)
    license_notice = DIAGRAM_LICENSE.read_text(encoding='utf-8')
    template = template.replace('<!DOCTYPE html>', f'<!DOCTYPE html>\n<!-- Diagram Design template\n{license_notice}-->')
    return re.sub(r'<svg\b.*?</svg>', lambda _: svg, template, count=1, flags=re.DOTALL)


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
