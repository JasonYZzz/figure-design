#!/usr/bin/env python3
"""Check canonical skill discovery, portable resource paths and active document links."""
from pathlib import Path
import json
import re
import sqlite3
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/scientific-figure-designer'


def check():
    errors = []
    upstream = SKILL/'third_party/diagram-design'
    discovery = ROOT / '.agents/skills/scientific-figure-designer'
    if not discovery.is_symlink() or discovery.resolve() != SKILL:
        errors.append('Codex discovery must link to the canonical skills/ directory')
    frontmatter = yaml.safe_load((SKILL/'SKILL.md').read_text(encoding='utf-8').split('---', 2)[1])
    if frontmatter.get('name') != SKILL.name:
        errors.append('SKILL.md name must match its directory')
    if (SKILL/'LICENSE').read_bytes() != (ROOT/'LICENSE').read_bytes():
        errors.append('bundled skill license must match the repository license')
    documents = [ROOT/'README.md', ROOT/'CONTRIBUTING.md', ROOT/'THIRD_PARTY_NOTICES.md',
                 *(p for p in SKILL.rglob('*.md') if not p.is_relative_to(upstream)),
                 ROOT/'docs/ARCHITECTURE.md', ROOT/'docs/DEVELOPMENT_PLAN.md', ROOT/'docs/releases/1.5.0.md']
    for path in documents:
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if re.match(r'\w+://', target) or target.startswith('#'):
                continue
            target = target.split('#')[0]
            if not (path.parent / target).exists():
                errors.append(f'{path.relative_to(ROOT)}: missing link {target}')
    library = SKILL/'assets/reference-library'
    with sqlite3.connect((library/'catalog.sqlite').as_uri()+'?mode=ro', uri=True) as db:
        rows = [json.loads(row[0]) for row in db.execute('SELECT record FROM refs')]
    if len(rows) != json.loads((library/'library.json').read_text())['count']:
        errors.append('reference catalog count differs from library metadata')
    sys.path.insert(0, str(SKILL/'scripts'))
    from figure_common import file_hash, inside
    third_party = json.loads((SKILL/'third_party/sources.json').read_text())
    for relative, digest in third_party['vendored_files'].items():
        if file_hash(inside(SKILL, relative)) != digest:
            errors.append('vendored code differs from recorded local copy: '+relative)
    for path in (SKILL/'scripts').rglob('*.py'):
        text = path.read_text()
        if re.search(r'https?://(?:raw\.githubusercontent\.com|github\.com)/|/Users/', text):
            errors.append('remote/upstream-machine source reference: '+str(path.relative_to(SKILL)))
    for row in rows:
        image = inside(library/'images', row['path'])
        if (library/'images').is_dir() and (not image.is_file() or file_hash(image) != row['sha256']):
            errors.append('missing or changed reference: '+row['path'])
    from figure_knowledge import lint
    try:
        knowledge=lint(library,library/'catalog.sqlite')
        if knowledge['status']!='ok' or knowledge['unanalysed']:
            errors.append('knowledge coverage or image verification failed')
    except (ValueError,OSError,KeyError) as exc:
        errors.append('knowledge: '+str(exc))
    for error in errors:
        print(error, file=sys.stderr)
    print(json.dumps({'documents':len(documents),'reference_records':len(rows),
                      'private_images_present':(library/'images').is_dir(),'errors':len(errors)}))
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(check())
