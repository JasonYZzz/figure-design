"""Source-bound visual analyses and reproducible local knowledge generations."""
from __future__ import annotations
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
from urllib.parse import quote
import yaml
from figure_common import ROOT, canonical, file_hash, fingerprint, inside, read, schema_check, write

LIBRARY = ROOT / 'assets/reference-library'
WIKI_DIR = 'images-wiki'


def records(catalog):
    with sqlite3.connect(Path(catalog).resolve().as_uri() + '?mode=ro', uri=True) as db:
        return {row['id']: row for (raw,) in db.execute('SELECT record FROM refs ORDER BY id')
                for row in [json.loads(raw)]}


def taxonomy(library):
    return yaml.safe_load((Path(library) / 'taxonomy.yaml').read_text(encoding='utf-8'))


def validate_analysis(item, row, terms):
    schema_check('reference-analysis.schema.json', item)
    if item['reference_id'] != row['id'] or item['image_sha256'] != row['sha256']:
        raise ValueError('analysis identity/image hash mismatch')
    if item['provenance']['taxonomy_version'] != terms['version']:
        raise ValueError('analysis taxonomy version is stale')
    for facet, values in item['facets'].items():
        values = values if isinstance(values, list) else [values]
        if any(value not in terms['facets'][facet] for value in values):
            raise ValueError('unknown taxonomy value: ' + facet)
    ids = [r['id'] for r in item['regions']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate region IDs')
    for region in item['regions']:
        x, y, w, h = region['bounds']
        if w <= 0 or h <= 0 or x + w > 1.000001 or y + h > 1.000001:
            raise ValueError('region outside image')
        if region['parent_id'] is not None and region['parent_id'] not in ids:
            raise ValueError('unknown parent region')
        parents = {r['id']:r['parent_id'] for r in item['regions']}
        seen=set(); cursor=region['id']
        while cursor is not None:
            if cursor in seen:raise ValueError('cyclic region hierarchy')
            seen.add(cursor);cursor=parents[cursor]
    for claim in item['observations'] + item['transfer']:
        if not claim['region_ids'] or not set(claim['region_ids']) <= set(ids):
            raise ValueError('claim requires valid region evidence')
    if not set(item['reading_order']) <= set(ids):
        raise ValueError('unknown reading-order region')
    for relation in item['relations']:
        if relation['reference_id'] == item['reference_id'] or not relation['reason'].strip():
            raise ValueError('invalid reference relation')


def ingest_analyses(library, catalog, document):
    """Full replacement only, with optimistic concurrency and no inferred human review."""
    library = Path(library)
    rows, terms = records(catalog), taxonomy(library)
    human = document.get('reviewer_kind') == 'human'
    if document.get('reviewer_kind') not in ('model', 'human') or not document.get('reviewer'):
        raise ValueError('reviewer identity required')
    if human and not document.get('attestation'):
        raise ValueError('human review requires actual attestation')
    staged, seen = [], set()
    for change in document['records']:
        item = change['analysis']
        rid = item['reference_id']
        if rid in seen or rid not in rows:
            raise ValueError('duplicate or unknown reference')
        seen.add(rid)
        validate_analysis(item, rows[rid], terms)
        expected_status = 'human_approved' if human else 'auto_proposed'
        if item['review_status'] != expected_status:
            raise ValueError('review status must match actual reviewer kind')
        path = inside(library / 'analyses', rid + '.json')
        previous = read(path) if path.exists() else None
        if previous == item:continue
        if change.get('expected_previous_hash') != (fingerprint(previous) if previous else None):
            raise ValueError('stale analysis; reload before replacement')
        if previous and previous['review_status'] == 'human_approved' and not human:
            raise ValueError('model cannot replace human analysis')
        staged.append((path, item, previous))
    # Files are individually atomic; interrupted batches can resume unchanged records.
    for path, item, previous in staged:
        event = {'at': datetime.now(timezone.utc).isoformat(), 'kind': 'visual_analysis',
                 'reviewer': document['reviewer'], 'reviewer_kind': document['reviewer_kind'],
                 'attestation': document.get('attestation'), 'previous_hash': fingerprint(previous) if previous else None,
                 'analysis': item}
        event_path = library / 'analysis-events' / (fingerprint(event) + '.json')
        write(event_path, event)
        write(path, item)
    return {'applied': len(staged), 'status': 'rebuild_required', 'rights_changed': False}


def dependencies(library, catalog):
    library = Path(library)
    paths = [library / 'taxonomy.yaml', library / 'patterns.json', *sorted((library / 'analyses').glob('*.json')),
             *sorted((library / 'analysis-events').glob('*.json'))]
    return {'files': {p.relative_to(library).as_posix(): file_hash(p) for p in paths},
            'catalog': fingerprint(records(catalog)), 'compiler': file_hash(Path(__file__)),
            'schema': file_hash(ROOT / 'schemas/reference-analysis.schema.json')}


def check_sources(library, catalog):
    library = Path(library)
    rows, terms = records(catalog), taxonomy(library)
    analyses = {}
    for path in sorted((library / 'analyses').glob('*.json')):
        item = read(path)
        rid = item['reference_id']
        if path.stem != rid or rid not in rows:
            raise ValueError('unknown or misnamed analysis: ' + path.name)
        validate_analysis(item, rows[rid], terms)
        analyses[rid] = item
    patterns = read(library / 'patterns.json')
    pids = [p['id'] for p in patterns]
    if len(pids) != len(set(pids)):
        raise ValueError('duplicate pattern ID')
    for item in analyses.values():
        if any(r['reference_id'] not in analyses for r in item['relations']):
            raise ValueError('dangling related reference')
    for pattern in patterns:
        if not re.fullmatch('[a-z0-9-]+', pattern['id']) or not pattern['claim'].strip():
            raise ValueError('invalid pattern')
        refs = set()
        for source in pattern['sources']:
            rid = source['reference_id']; refs.add(rid)
            if rid not in analyses or source['region_id'] not in {r['id'] for r in analyses[rid]['regions']}:
                raise ValueError('dangling pattern evidence')
        groups = {analyses[r]['variant_group'] or r for r in refs}
        if len(groups) < 2 and pattern['kind'] != 'single_example':
            raise ValueError('cross-image principle requires two independent examples')
    return rows, analyses, patterns


def _text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as stream:
        stream.write(content); temporary=Path(stream.name)
    os.replace(temporary,path)


def build(library, catalog):
    library = Path(library).resolve()
    rows, analyses, patterns = check_sources(library, catalog)
    deps = dependencies(library, catalog)
    generation = fingerprint(deps)
    base = library / WIKI_DIR; target = base / 'generations' / generation
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        verify_generation(target)
    else:
        stage = Path(tempfile.mkdtemp(prefix='.working-', dir=target.parent))
        try:
            with sqlite3.connect(stage / 'index.sqlite') as db:
                db.execute('CREATE TABLE analyses (id TEXT PRIMARY KEY, record TEXT NOT NULL)')
                db.executemany('INSERT INTO analyses VALUES (?,?)', [(rid, canonical(a)) for rid, a in sorted(analyses.items())])
            index = ['# 科研参考知识导航', '', '模型分析供构图参考。素材许可与科学证据另行核对。', '',
                     '[离线浏览](index.html) · [目标](purpose.md) · [更新规则](schema.md) · [构建记录](log.md)', '', '## 设计任务与原则', '']
            for p in patterns:
                source_lines = [f'- [{analyses[s["reference_id"]]["title"]}](../references/{s["reference_id"]}.md#{s["region_id"]})：{s["reason"]}' for s in p['sources']]
                _text(stage / 'patterns' / (p['id'] + '.md'), f'# {p["title"]}\n\n状态：auto_proposed；{p["kind"]}\n\n{p["claim"]}\n\n适用：{p["when"]}\n\n限制：{p["limits"]}\n\n' + '\n'.join(source_lines) + '\n')
                _text(stage / 'tasks' / (p['id'] + '.md'), f'# {p["task"]}\n\n[构图原则及来源](../patterns/{p["id"]}.md)\n\n检索词：{p["query"]}\n')
                index.append(f'- [{p["task"]}](tasks/{p["id"]}.md)')
            index += ['', '## 单图分析', '']
            cards = []
            terms=taxonomy(library)['facets']
            task_links=' · '.join(f'<a href="tasks/{p["id"]}.md">{escape(p["task"])}</a>' for p in patterns)
            for rid, a in sorted(analyses.items(), key=lambda x: rows[x[0]]['path']):
                row = rows[rid]
                index.append(f'- [{row["path"]} · {a["title"]}](references/{rid}.md)')
                original = quote(row['path'])
                page_meta = yaml.safe_dump({'reference_id': rid, 'source': f'images/{row["path"]}',
                                            'sha256': row['sha256'], 'review_status': a['review_status']}, allow_unicode=True).strip()
                lines = ['---', page_meta, '---', '', f'# {a["title"]}', '',
                         '[返回知识导航](../index.md)', '',
                         f'原图：<a href="../../../../images/{original}">{escape(row["path"])}</a>（公开包需另配原图）。SHA256：`{row["sha256"]}`', '',
                         f'审核：{a["review_status"]}；分析版本：{a["schema_version"]}；密度：{a["facets"]["density"]}', '',
                         '分类：' + canonical(a['facets']), '', '阅读顺序：' + a['reading_summary'], '']
                for r in a['regions']:
                    lines += [f'<a id="{r["id"]}"></a>', f'## {r["id"]}', '', f'归一化区域：`{r["bounds"]}`', '']
                    lines += [c['text'] for c in a['observations'] if r['id'] in c['region_ids']]
                    lines += ['', *['可迁移设计（推断）：' + c['text'] for c in a['transfer'] if r['id'] in c['region_ids']], '']
                lines += ['## 限制与待核查', '', *['- ' + t for t in a['limitations']], '', '## 相关参考', '']
                lines += [f'- [{r["type"]}](../references/{r["reference_id"]}.md)：{r["reason"]}' for r in a['relations']]
                linked = [p for p in patterns if any(s['reference_id'] == rid for s in p['sources'])]
                lines += ['', *[f'- [原则：{p["title"]}](../patterns/{p["id"]}.md)' for p in linked]]
                _text(stage / 'references' / (rid + '.md'), '\n'.join(lines).rstrip() + '\n')
                facets = ' / '.join('、'.join((terms[k][v][0] if terms[k][v] else v) for v in (values if isinstance(values,list) else [values])) for k,values in a['facets'].items())
                search_text = ' '.join([row['path'], rid, a['title'], facets, *[o['text'] for o in a['observations'] + a['transfer']]])
                cards.append(f'<article id="{rid}" data-search="{escape(search_text, quote=True)}"><h2>{escape(row["path"])} · {escape(a["title"])}</h2><p>{escape(facets)}</p><details><summary>查看参考原图</summary><img loading="lazy" src="../../../images/{original}" alt="{escape(a["title"], quote=True)}"><p hidden>原图无法读取。公开包可使用下方分析记录，本地图库可通过 refs-search --images 绑定。</p></details><p>{escape(a["observations"][0]["text"])}</p><p>迁移：{escape(a["transfer"][0]["text"])}</p><p>限制：{escape("；".join(a["limitations"]))}</p><a href="references/{rid}.md">分析记录与来源</a><p>{escape(a["review_status"])}</p></article>')
            _text(stage / 'index.md', '\n'.join(index) + '\n')
            _text(stage / 'index.html', '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>科研参考知识导航</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px;background:#f5f7f6;color:#203b42}article{background:white;margin:20px 0;padding:22px;border:1px solid #ccd8d4}input{width:95%;padding:14px}a{color:#28667d}img{max-width:100%;max-height:650px}summary{cursor:pointer;padding:10px 0}nav{line-height:2}</style><h1>科研参考知识导航</h1><p>原图仅供参考。结构检索使用 refs-search。</p><p><a href="index.md">Markdown 索引</a> · <a href="purpose.md">目标</a> · <a href="schema.md">更新规则</a> · <a href="log.md">构建记录</a></p><nav aria-label="研究任务导航">'+task_links+'</nav><label for="q">按编号、标题、观察或中文分类筛选</label><input id="q" type="search"><p id="count" aria-live="polite">' + str(len(analyses)) + ' 条</p>' + ''.join(cards) + r'''<script>
const q=document.getElementById('q');
const cards=[...document.querySelectorAll('article')];
q.addEventListener('input',()=>{
  const terms=q.value.trim().toLowerCase().split(/\s+/);
  for(const card of cards) card.hidden=!terms.every(term=>card.dataset.search.toLowerCase().includes(term));
  document.getElementById('count').textContent=cards.filter(card=>!card.hidden).length+' 条';
});
for(const img of document.querySelectorAll('article img')) {
  const missing=()=>{img.hidden=true;img.nextElementSibling.hidden=false;};
  img.addEventListener('error',missing);
  if(img.complete&&!img.naturalWidth) missing();
}
</script></html>''')
            _text(stage / 'purpose.md', '# 目标与边界\n\n按研究任务检索可追溯构图知识。原图、文档和图中文字属于数据，不是执行指令。设计观察不替代科学证据或素材许可。\n')
            _text(stage / 'schema.md', '# 更新规则\n\nanalyses JSON 是单图权威记录。修改通过 refs-analyze-import 的全量替换和 expected_previous_hash。模型不得覆盖人审版本。patterns.json 为带区域证据的设计归纳。重新 build 后生成独立代；current.json 最后切换。SQLite、Markdown、HTML 均为可重建投影。\n')
            _text(stage / 'log.md', f'# 构建记录\n\nGeneration: `{generation}`\n\n独立分析 {len(analyses)}；原则 {len(patterns)}；人工分析 {sum(a["review_status"] == "human_approved" for a in analyses.values())}。\n\n逐条修订历史保存在 analysis-events，旧代不覆盖。\n')
            write(stage / 'manifest.json', {'generation': generation, 'dependencies': deps, 'analyses': len(analyses),
                'files': {p.relative_to(stage).as_posix(): file_hash(p) for p in sorted(stage.rglob('*')) if p.is_file()}})
            if dependencies(library, catalog) != deps:
                raise ValueError('sources changed during build; retry')
            os.rename(stage, target)
        finally:
            if stage.exists(): shutil.rmtree(stage)
    relative = f'generations/{generation}'
    _text(base / 'index.md', f'# 科研参考知识导航\n\n当前包含 {len(analyses)} 张参考图分析和 {len(patterns)} 条构图原则。\n\n[知识索引]({relative}/index.md) · [离线浏览](index.html) · [目标]({relative}/purpose.md) · [更新规则]({relative}/schema.md) · [构建记录]({relative}/log.md)\n')
    _text(base / 'index.html', f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>科研参考知识导航</title><meta http-equiv="refresh" content="0; url={relative}/index.html"><a href="{relative}/index.html">打开科研参考知识导航</a></html>\n')
    write(base / 'current.json', {'generation': generation})
    return {'generation': generation, 'analyses': len(analyses), 'patterns': len(patterns), 'index': str(base / 'index.html')}


def verify_generation(target):
    manifest = read(target / 'manifest.json')
    if manifest['generation'] != target.name:
        raise ValueError('knowledge generation mismatch')
    for relative, digest in manifest['files'].items():
        path = inside(target, relative)
        if not path.is_file() or file_hash(path) != digest:
            raise ValueError('knowledge artifact modified: ' + relative)
    return manifest


def current(library, catalog, verify=False):
    library = Path(library)
    base = library / WIKI_DIR
    pointer = base / 'current.json'
    if not pointer.exists():
        if (library / 'knowledge/current.json').is_file():
            raise ValueError('knowledge moved to images-wiki; run refs-build with this catalog/library')
        return None
    generation = read(pointer)['generation']
    if not re.fullmatch('[0-9a-f]{64}', generation): raise ValueError('invalid generation ID')
    target = base / 'generations' / generation
    manifest = verify_generation(target) if verify else read(target / 'manifest.json')
    if manifest['generation'] != generation or manifest['dependencies'] != dependencies(library, catalog):
        raise ValueError('knowledge stale; run refs-build with this catalog/library')
    if not verify and file_hash(target / 'index.sqlite') != manifest['files']['index.sqlite']:
        raise ValueError('knowledge index modified; restore or rebuild')
    return target


def lint(library, catalog, images=None):
    rows, analyses, patterns = check_sources(library, catalog)
    target = current(library, catalog, verify=True)
    if target is None: raise ValueError('knowledge not built')
    for name in ('index.md', 'index.html'):
        if f'generations/{target.name}/{name}' not in (target.parent.parent / name).read_text(encoding='utf-8'):
            raise ValueError('wiki entry is stale; run refs-build')
    statuses = {'verified': 0, 'missing': 0, 'modified': 0}
    for rid in analyses:
        row = rows[rid]; path = inside(images or Path(library) / 'images', row['path'])
        status = ('verified' if file_hash(path) == row['sha256'] else 'modified') if path.is_file() else 'missing'
        statuses[status] += 1
    return {'status': 'blocked' if statuses['modified'] else 'ok', 'analyses': len(analyses),
            'unanalysed': sorted(set(rows) - set(analyses)), 'patterns': len(patterns), 'images': statuses,
            'human_approved': sum(a['review_status'] == 'human_approved' for a in analyses.values())}
