"""Executable composition families, graph-aware selection and explicit bindings."""
from __future__ import annotations
import math
import yaml
from figure_common import MIXED_ROUTES, ROOT, fingerprint, schema_check


def registry():
    return yaml.safe_load((ROOT / 'assets' / 'layout-registry.yaml').read_text(encoding='utf-8'))


def contrast(first, second):
    def luminance(color):
        channels = [int(color[index:index+2], 16)/255 for index in (1, 3, 5)]
        linear = [value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4 for value in channels]
        return sum(value*weight for value, weight in zip(linear, (.2126, .7152, .0722)))
    low, high = sorted((luminance(first), luminance(second)))
    return (high+.05)/(low+.05)


def default_style(domain):
    normalized = domain.casefold()
    for aliases, default in registry()['domain_styles']:
        if any(alias in normalized for alias in aliases):
            return default
    return 'general-roadmap'


def figure_theme(plan):
    preset = registry()['styles'].get(plan['style_id'])
    if preset is None:
        raise ValueError('unknown style')
    theme = plan.get('theme') or preset

    for hue in ('ink', 'muted', 'accent', 'secondary', 'tertiary'):
        if hue in theme and any(contrast(theme[hue], theme[background]) < 4.5 for background in ('paper', 'surface')):
            raise ValueError(f'theme_contrast: {hue} against paper and surface must reach 4.5:1')
    return theme


def positions(family, n, variant='balanced'):
    if not 1 <= n <= 24:
        raise ValueError('one figure supports 1–24 owners; split dense content into figures')
    gap = .035
    def grid(cols):
        rows = math.ceil(n / cols)
        w, h = (.90 - (cols - 1) * gap) / cols, (.68 - (rows - 1) * gap) / rows
        return [[.05 + (i % cols) * (w + gap), .20 + (i // cols) * (h + gap), w, h] for i in range(n)]
    if family == 'lanes':
        return grid(min(n, 4))
    if family == 'stages':
        return grid(1 if n <= 4 else 2)
    if family == 'matrix':
        return grid(2 if n > 1 else 1)
    if family == 'center':
        if n == 1:
            return [[.24, .23, .52, .55]]
        result = [[.34, .31, .32, .36]]
        others = n - 1
        height = min(.27, (.68 - gap * (math.ceil(others / 2) - 1)) / math.ceil(others / 2))
        for i in range(others):
            result.append([.04 if i % 2 == 0 else .72, .20 + (i // 2) * (height + gap), .24, height])
        return result
    if family == 'radial':
        if n > 7:
            raise ValueError('radial composition supports at most seven owners')
        result = [[.38, .43, .24, .20]]
        for i in range(n - 1):
            angle = -math.pi / 2 + i * 2 * math.pi / (n - 1)
            result.append([.39 + .34 * math.cos(angle), .445 + .285 * math.sin(angle), .22, .17])
        return result
    if family == 'funnel':
        h = (.68 - (n - 1) * gap) / n
        return [[.05 + .14 * i / max(1, n - 1), .20 + i * (h + gap),
                 .90 - .28 * i / max(1, n - 1), h] for i in range(n)]
    if family == 'fork':
        if n < 3:
            return grid(n)
        if n > 6:
            raise ValueError('fork layout supports at most six owners')
        count = n - 2
        width = (.90 - (count - 1) * gap) / count
        return [[.28, .18, .44, .16]] + [[.05 + i * (width + gap), .40, width, .20] for i in range(count)] + [[.28, .69, .44, .16]]
    if family == 'scales':
        if n > 4:
            return grid(2)
        widths = [.90 - i * .12 for i in range(n)]
        h = (.68 - gap * (n - 1)) / n
        return [[.05 + i * .10, .20 + i * (h + gap), widths[i], h] for i in range(n)]
    if family == 'apparatus':
        if n < 2:
            return grid(1)
        h = (.68 - (n - 2) * gap) / (n - 1)
        return [[.05, .20, .52, .68]] + [[.63, .20 + i * (h + gap), .32, h] for i in range(n - 1)]
    if family == 'abstract':
        if n > 3:
            raise ValueError('graphical abstract supports at most three owners')
        return [[.08, .27, .48, .47]] + [[.63, .22 + i * .33, .29, .26] for i in range(n - 1)]
    raise ValueError('unknown layout family')


def owner_slots(content):
    excluded = {content['figure_id'], *(relation['id'] for relation in content['relations'])}
    owners = dict.fromkeys(item['owner_id'] for item in content['label_instances'] if item['owner_id'] not in excluded)
    return {f'owner-{index}': owner for index,owner in enumerate(owners,1)}


def make_plan(content, primary, style, variant='balanced', route='asset_composite', *, decisions=None):
    schema_check('figure-content.schema.json', content)
    if route not in MIXED_ROUTES:
        raise ValueError('use Diagram Design for text diagrams')
    config = registry()
    layout = config['layouts'].get(primary)
    if not layout:
        raise ValueError('unknown layout')
    variants = {'balanced':(1600,1200,False), 'wide':(1800,1200,False),
                'portrait':(1200,1800,False), 'landscape':(2000,1000,False),
                'mirrored':(1600,1200,True), 'wide-mirrored':(1800,1200,True),
                'portrait-mirrored':(1200,1800,True), 'landscape-mirrored':(2000,1000,True)}
    if variant not in variants:
        raise ValueError('unknown variant: '+', '.join(variants))
    if style not in config['styles']:
        raise ValueError('unknown style')
    instances = content['label_instances']
    slots = owner_slots(content)
    decisions = decisions or {}
    owner_ids = list(slots.values())
    order = decisions.get('reading_order', [])
    hero = decisions.get('hero_owner_id')
    # Older briefs used prose for the reading order. Keep those hints for manual review.
    order = [o for o in order if isinstance(o, str) and o in owner_ids] if isinstance(order, list) else []
    hero = hero if hero in owner_ids else None
    ordered = list(dict.fromkeys([*order, *owner_ids]))
    central = layout['family'] in ('center', 'radial', 'abstract', 'apparatus')
    if central and hero:
        ordered.remove(hero)
        ordered.insert(0, hero)
    # Keep owner-N stable for reference placements even when reading order changes.
    region_ids = {owner: rid for rid, owner in slots.items()}
    coords = positions(layout['family'], len(slots), variant)
    cw,ch,mirrored=variants[variant]
    if mirrored:coords=[[1-x-w,y,w,h] for x,y,w,h in coords]
    canvas = {'width':cw, 'height':ch}
    regions = []
    def region(rid, role, bounds, ids):
        return {'id': rid, 'role': role, 'bounds': bounds, 'label_instance_ids': ids,
                'visual_priority': 9 if role in ('hero', 'title') else 6,
                'text_safe': {'min_font_px': 24, 'max_lines': 14, 'padding_px': 24}}
    title = [i['id'] for i in instances if i['owner_id'] == content['figure_id'] and i['role'] == 'title']
    caption = [i['id'] for i in instances if i['owner_id'] == content['figure_id'] and i['role'] != 'title']
    if title:
        regions.append(region('title', 'title', [.05, .035, .90, .12], title))
    owner_regions = {}
    for i, (owner, bounds) in enumerate(zip(ordered, coords)):
        rid = region_ids[owner]
        owner_regions[owner] = rid
        regions.append(region(rid, 'hero' if owner == hero or (central and i == 0 and not hero) else 'research_task', bounds,
                              [item['id'] for item in instances if item['owner_id'] == owner]))
    edges = []
    for rel in content['relations']:
        if rel['from_id'] not in owner_regions or rel['to_id'] not in owner_regions:
            raise ValueError('every relation endpoint needs a placed label instance')
        edges.append({'relation_id': rel['id'], 'source_region_id': owner_regions[rel['from_id']],
                      'target_region_id': owner_regions[rel['to_id']],
                      'line_style': 'tbar' if rel['type'] == 'inhibits' else 'dashed' if rel['evidence_state'] in ('planned', 'hypothesis') else 'solid'})
        owned = [i for i in instances if i['owner_id'] == rel['id']]
        for r in regions:
            if r['id'] == owner_regions[rel['from_id']]:
                r['label_instance_ids'].extend(i['id'] for i in owned if i['role'] != 'operation')
        for instance in owned:
            if instance['role'] == 'operation':
                edges[-1]['label_instance_id'] = instance['id']
        if rel.get('condition_label_id') and not any(i['owner_id'] == rel['id'] and i['label_id'] == rel['condition_label_id'] for i in instances):
            raise ValueError('conditional relation needs an explicit condition LabelInstance owned by that relation')
    if caption:
        regions.append(region('caption', 'caption', [.05, .905, .90, .055], caption))
    plan = {'schema_version': '1.0', 'figure_id': content['figure_id'], 'route': route, 'mode': 'mixed',
            'canvas': canvas, 'grammar': {'primary': primary, 'modifiers': [layout['modifier']], 'asset_treatments': []},
            'regions': regions, 'edges': edges, 'style_id': style, 'status': 'draft'}
    schema_check('composition-plan.schema.json', plan)
    return plan


def reference_choices(content, references, brief):
    if brief['source_content_hash'] != fingerprint(content):
        raise ValueError('reference review is stale for this content')
    rows = {row['id']:row for row in references['candidates']}
    choices = {}
    selected = brief['design_decisions']['reference_choices_with_reasons']
    if len(selected) > 2:
        raise ValueError('select at most two primary reference regions')
    for choice in selected:
        rid = choice['id']
        row = rows.get(rid)
        if row is None or rid in choices or row.get('image_status') == 'modified':
            raise ValueError(f'invalid selected reference: {rid}')
        if choice.get('basis') not in ('original', 'knowledge') or (choice['basis']=='original' and row.get('image_status')!='verified'):
            raise ValueError(f'invalid reference review basis: {rid}')
        if choice.get('region_id') not in {region['id'] for region in row['analysis']['regions']} or not choice.get('use','').strip():
            raise ValueError(f'reference review requires a valid region and a concrete transfer: {rid}')
        choices[rid] = {key:choice[key] for key in ('region_id','use','basis')}
    return choices


def arrange_paths(plan, content, decisions, evidence_first):
    """Use each scientific owner once, even when several paths visit it."""
    paths = decisions['main_paths']
    slots = owner_slots(content)
    regions = {r['id']: r for r in plan['regions']}
    by_owner = {owner: regions[rid] for rid, owner in slots.items()}
    declared_order = decisions.get('reading_order') or []
    order = list(dict.fromkeys([*(o for o in declared_order if isinstance(o, str) and o in by_owner), *by_owner]))
    columns = []
    assigned = set()
    for key in ('intermediate', 'input', 'output'):
        members = {p[key] for p in paths}
        if members - by_owner.keys():
            raise ValueError('main_paths refers to an unplaced owner')
        columns.append([o for o in order if o in members - assigned])
        assigned.update(members)
    middle, left, right = columns
    evidence = [o for o in order if o not in assigned]
    width = plan['canvas']['width']
    height = 40
    boxes = {}
    labels = {label['id']: label['text'] for label in content['labels']}
    texts = {i['id']: labels[i['label_id']] for i in content['label_instances']}

    anchors = decisions.get('label_anchors') or {}
    bands = {'before_paths': [], 'before_evidence': [], 'input_column': [], 'shared_column': [], 'output_column': []}
    caption = regions.get('caption')
    anchored = {}
    for iid, target in anchors.items():
        if not caption or iid not in caption['label_instance_ids']:
            raise ValueError('label_anchors must reference figure-wide non-title instances')
        if target not in by_owner and target not in bands:
            raise ValueError('unknown label anchor: ' + str(target))
        caption['label_instance_ids'].remove(iid)
        anchored.setdefault(target, []).append(iid)
    for owner, ids in anchored.items():
        if owner in by_owner:
            by_owner[owner]['label_instance_ids'][:0] = ids
        else:
            rid = 'heading-' + owner
            r = {**caption, 'text_safe': dict(caption['text_safe']), 'id':rid, 'role':'support',
                 'appearance':'plain', 'label_instance_ids':ids}
            plan['regions'].append(r)
            regions[rid] = r
            bands[owner] = [r]
    if caption and not caption['label_instance_ids']:
        plan['regions'].remove(caption)
        del regions['caption']
    depicted = {v.get('owner_id') for v in decisions.get('visual_concept', {}).get('depictions', [])
                if isinstance(v, dict)}

    def text_height(r, w):
        # Conservative line estimate for the sketch; preflight uses shaped glyphs.
        count = sum(sum(max(1, math.ceil(len(line) * 26 / (w - 32))) for line in texts[i].split('\n'))
                    for i in r['label_instance_ids'])
        return max(80, 32 + count * 38 + max(0, len(r['label_instance_ids']) - 1) * 16)

    def place(r, x, y, w, h):
        boxes[r['id']] = (x, y, w, h)
        r['text_safe']['padding_px'] = 12

    if 'title' in regions:
        r = regions['title']
        h = max(96, text_height(r, width * .92) * 2)
        place(r, width * .04, height, width * .92, h)
        height += h + 20

    def heading(name, x, y, w):
        for r in bands[name]:
            h = text_height(r, w)
            place(r, x, y, w, h)
            return y + h + 12
        return y

    def evidence_rows(y):
        y = heading('before_evidence', width * .035, y, width * .93)
        for start in range(0, len(evidence), 3):
            row = [by_owner[o] for o in evidence[start:start+3]]
            w = width * .89 / len(row)
            h = max(text_height(r, w) for r in row)
            # Reserve room above the text for a representative chart or illustration.
            h = math.ceil((h + 36) / .56)
            for index, r in enumerate(row):
                place(r, width * .04 + index * (w + width * .015), y, w, h)
                if r['role'] != 'hero':
                    r['role'] = 'validation'
            y += h + 48
        return y

    if evidence_first:
        height = evidence_rows(height)
    height = heading('before_paths', width * .035, height, width * .93)
    height = max(heading(key, x * width, height, w * width) for key, x, w in
                 [('input_column', .035, .23), ('shared_column', .37, .26), ('output_column', .735, .23)])
    # Align matched endpoints across the page. Shared objects span their lanes.
    paths = sorted(paths, key=lambda path: (order.index(path['intermediate']), order.index(path['input'])))
    spans = {}
    for path in paths:
        row_height = max(128, *(text_height(by_owner[path[key]], width * fraction)
                                for key, fraction in [('input', .23), ('intermediate', .26), ('output', .23)]))
        for o in (path['input'], path['intermediate'], path['output']):
            top = spans.get(o, (height, height))[0]
            spans[o] = (top, height + row_height)
        height += row_height + 60
    for owners, x, w in ((left, .035, .23), (middle, .37, .26), (right, .735, .23)):
        bottom = 0
        for o in sorted(owners, key=lambda owner: spans[owner][0]):
            top, end = spans[o]
            # Reused endpoints in non-adjacent lanes still occupy a single region.
            y = max(top, bottom)
            content_height = text_height(by_owner[o], width * w)
            if o in depicted:
                by_owner[o].update(asset_position='left', asset_fraction=.30)
                content_height = text_height(by_owner[o], width * w * .64)
            h = max(content_height, end - y)
            place(by_owner[o], width * x, y, width * w, h)
            bottom = y + h + 60
        height = max(height, bottom)
    if not evidence_first:
        height = evidence_rows(height)
    if 'caption' in regions:
        # Old figure-wide editorial labels have no owner geometry. Keep them all.
        r = regions['caption']
        h = text_height(r, width * .92)
        place(r, width * .04, height, width * .92, h)
        height += h
    height += 80
    plan['canvas']['height'] = max(height, plan['canvas']['height'])
    for rid, (x, y, w, h) in boxes.items():
        regions[rid]['bounds'] = [x/width, y/plan['canvas']['height'], w/width, h/plan['canvas']['height']]
    if len(middle) > 1:
        for o in middle:
            by_owner[o]['appearance'] = 'panel'
        plan['groups'] = [{'id': 'shared-representations', 'regions': [by_owner[o]['id'] for o in middle]}]
    schema_check('composition-plan.schema.json', plan)


def candidates(content, style='biomedicine-academic', references=None, *, variant='balanced', route='asset_composite', reviewed=None, decisions=None):
    rels = content['relations']
    types = {r['type'] for r in rels}
    degree = {}
    for r in rels:
        degree[r['from_id']] = degree.get(r['from_id'], 0) + 1
    if types & {'activates', 'inhibits', 'feedback'}:
        choices = ['center-hero-side-support', 'macro-micro-mechanism']
    elif any(v > 1 for v in degree.values()):
        choices = ['fork-merge-validation', 'top-overview-multi-lane']
    elif types <= {'sequence', 'depends_on'} and rels:
        choices = ['annual-stage-timeline', 'top-overview-multi-lane']
    else:
        choices = ['top-overview-multi-lane', 'comparative-panels']
    reviewed = reviewed or {}
    suggestions=[]
    if references:
        if references.get('source_content_hash') != fingerprint(content):
            raise ValueError('reference suggestions are stale for this content')
        for row in references.get('candidates',[]):
            if row['id'] not in reviewed:continue
            layout=row.get('analysis',{}).get('facets',{}).get('layout')
            if layout in registry()['layouts'] and layout not in suggestions:suggestions.append(layout)
        choices=list(dict.fromkeys(suggestions[:2]+choices))
    decisions = decisions or {}
    paths = decisions.get('main_paths') or []
    path_layout = not decisions.get('reference_design') and bool(paths) and all(isinstance(p, dict) and
        all(isinstance(p.get(k), str) for k in ('input', 'intermediate', 'output')) for p in paths)
    path_owners = {p[k] for p in paths for k in ('input', 'intermediate', 'output')} if path_layout else set()
    # Prose paths from older briefs remain design notes; only actual IDs determine geometry.
    path_layout = path_layout and path_owners <= set(owner_slots(content).values())
    compare_evidence = path_layout and any(i['role'] == 'readout' and i['owner_id'] not in path_owners
                                           for i in content['label_instances'])
    if path_layout:
        choices = list(dict.fromkeys(['top-overview-multi-lane', *(['comparative-panels'] if compare_evidence else []), *choices]))
    result = []
    for primary in choices:
        if len(result)==2:break
        try:
            plan = make_plan(content, primary, style, variant=variant, route=route, decisions=decisions)
            reason = 'refine this initial layout using topology and reviewed reference regions'
            if path_layout and (not result or compare_evidence):
                evidence_first = bool(result)
                arrange_paths(plan, content, decisions, evidence_first)
                if variant.endswith('mirrored'):
                    for r in plan['regions']:
                        x, y, w, h = r['bounds']
                        r['bounds'] = [1-x-w, y, w, h]
                reason = '先读实验对照，再追溯机制' if evidence_first else '先读共享对象与可选路径，再核对实验'
            result.append({'plan': plan, 'content_hash': fingerprint(content),
                           'reason': reason, 'status': 'capacity_check_pending',
                           'reference_review': reviewed,
                           'reference_evidence': [{'id':r['id'],'sha256':r['sha256'],'analysis_hash':r.get('analysis_hash'),
                               'image_status':r.get('image_status'),'visual_review':reviewed.get(r['id'], 'pending'),'transfer_regions':r.get('transfer_regions',[])}
                               for r in (references or {}).get('candidates',[]) if r.get('image_status')!='modified' and r.get('analysis',{}).get('facets',{}).get('layout')==primary]})
        except ValueError as exc:
            if 'supports at most' not in str(exc):
                raise
            continue
    if not result:
        raise ValueError('no initial layout fits owner count; split the figure')
    return result
