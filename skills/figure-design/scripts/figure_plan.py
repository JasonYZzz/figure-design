"""Executable composition families, graph-aware selection and explicit bindings."""
from __future__ import annotations
import math
import yaml
from figure_common import ROOT, fingerprint, schema_check

MIXED_ROUTES = ('asset_composite', 'image_first', 'strict_scientific')


def registry():
    return yaml.safe_load((ROOT / 'assets' / 'layout-registry.yaml').read_text(encoding='utf-8'))


def figure_theme(plan):
    preset = registry()['styles'].get(plan['style_id'])
    if preset is None:
        raise ValueError('unknown style')
    theme = plan.get('theme') or preset

    def luminance(rgb):
        channels = [int(rgb[i:i+2], 16)/255 for i in (1, 3, 5)]
        linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in channels]
        return sum(value*weight for value, weight in zip(linear, (.2126, .7152, .0722)))

    for text in ('ink', 'muted', 'accent'):
        for background in ('paper', 'surface'):
            low, high = sorted((luminance(theme[text]), luminance(theme[background])))
            if (high+.05)/(low+.05) < 4.5:
                raise ValueError(f'theme_contrast: {text} against {background} must reach 4.5:1')
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


def make_plan(content, primary, style, variant='balanced', route='asset_composite'):
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
    owner_ids = list(dict.fromkeys(i['owner_id'] for i in instances
                                  if i['owner_id'] != content['figure_id'] and i['owner_id'] not in {r['id'] for r in content['relations']}))
    # Preserve task input order; Codex may reorder explicitly after scientific review.
    coords = positions(layout['family'], len(owner_ids), variant)
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
    for i, (owner, bounds) in enumerate(zip(owner_ids, coords)):
        rid = f'owner-{i + 1}'
        owner_regions[owner] = rid
        regions.append(region(rid, 'hero' if layout['family'] in ('center', 'radial', 'abstract', 'apparatus') and i == 0 else 'research_task', bounds,
                              [item['id'] for item in instances if item['owner_id'] == owner]))
    edges = []
    for rel in content['relations']:
        if rel['from_id'] not in owner_regions or rel['to_id'] not in owner_regions:
            raise ValueError('every relation endpoint needs a placed label instance')
        edges.append({'relation_id': rel['id'], 'source_region_id': owner_regions[rel['from_id']],
                      'target_region_id': owner_regions[rel['to_id']],
                      'line_style': 'tbar' if rel['type'] == 'inhibits' else 'dashed' if rel['evidence_state'] in ('planned', 'hypothesis') else 'solid'})
        owned = [i['id'] for i in instances if i['owner_id'] == rel['id']]
        for r in regions:
            if r['id'] == owner_regions[rel['from_id']]:
                r['label_instance_ids'].extend(owned)
        if rel.get('condition_label_id') and not any(i['owner_id'] == rel['id'] and i['label_id'] == rel['condition_label_id'] for i in instances):
            raise ValueError('conditional relation needs an explicit condition LabelInstance owned by that relation')
    if caption:
        regions.append(region('caption', 'caption', [.05, .905, .90, .055], caption))
    plan = {'schema_version': '1.0', 'figure_id': content['figure_id'], 'route': route, 'mode': 'mixed',
            'canvas': canvas, 'grammar': {'primary': primary, 'modifiers': [layout['modifier']], 'asset_treatments': []},
            'regions': regions, 'edges': edges, 'style_id': style, 'status': 'draft'}
    schema_check('composition-plan.schema.json', plan)
    return plan


def candidates(content, style='biomedicine-academic', references=None, *, variant='balanced', route='asset_composite'):
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
    suggestions=[]
    if references:
        if references.get('source_content_hash') != fingerprint(content):
            raise ValueError('reference suggestions are stale for this content')
        for row in references.get('candidates',[]):
            if row.get('image_status')=='modified':continue
            layout=row.get('analysis',{}).get('facets',{}).get('layout')
            if layout in registry()['layouts'] and layout not in suggestions:suggestions.append(layout)
        choices=list(dict.fromkeys(suggestions[:2]+choices))
    result = []
    for primary in choices:
        if len(result)==2:break
        try:
            plan = make_plan(content, primary, style, variant=variant, route=route)
            result.append({'plan': plan, 'content_hash': fingerprint(content),
                           'reason': 'topology-based initial candidate; Codex must inspect references and refine', 'status': 'capacity_check_pending',
                           'reference_evidence': [{'id':r['id'],'sha256':r['sha256'],'analysis_hash':r.get('analysis_hash'),
                               'image_status':r.get('image_status'),'visual_review':'pending','transfer_regions':r.get('transfer_regions',[])}
                               for r in (references or {}).get('candidates',[]) if r.get('image_status')!='modified' and r.get('analysis',{}).get('facets',{}).get('layout')==primary]})
        except ValueError:
            continue
    if not result:
        raise ValueError('no initial layout fits owner count; split the figure')
    return result
