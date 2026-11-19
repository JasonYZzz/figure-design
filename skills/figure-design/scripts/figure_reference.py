"""Task-local design references and semantic color samples."""
from collections import Counter
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from PIL import Image, ImageCms, ImageOps
from figure_common import file_hash
from figure_plan import contrast, registry

ROLES = ('paper', 'surface', 'ink', 'muted', 'accent', 'border', 'secondary', 'tertiary')


def reference_inputs(paths):
    records = []
    for index, filename in enumerate(paths, 1):
        path = Path(filename).resolve()
        record = {'id': f'upload-{index}', 'path': str(path), 'status': 'unavailable'}
        try:
            if not path.is_file() or path.stat().st_size > 30 * 1024 * 1024:
                raise ValueError('reference must be a local image of at most 30 MiB')
            record['sha256'] = file_hash(path)
            if path.suffix.lower() == '.svg':
                from figure_assets import validate_image
                validate_image(path)
                svg = ET.parse(path).getroot()
                if svg.get('viewBox'):
                    _, _, width, height = map(float, svg.get('viewBox').replace(',', ' ').split())
                else:
                    width, height = (float(svg.attrib[key].removesuffix('px')) for key in ('width', 'height'))
                if not 1 <= width <= 100000 or not 1 <= height <= 100000:
                    raise ValueError('invalid SVG reference dimensions')
                record['size'] = [round(width), round(height)]
            else:
                with Image.open(path) as image:
                    if image.width * image.height > 50_000_000:
                        raise ValueError('reference exceeds 50 megapixels')
                    orientation = image.getexif().get(274, 1)
                    record['size'] = list(image.size[::-1] if orientation in (5, 6, 7, 8) else image.size)
                    image.load()
            record['status'] = 'readable'
        except (OSError, ValueError, KeyError, ET.ParseError, Image.DecompressionBombError) as exc:
            record['error'] = str(exc)
        records.append(record)
    return records


def normalized_box(bounds):
    if (not isinstance(bounds, list) or len(bounds) != 4
        or any(type(n) not in (int, float) or not 0 <= n <= 1 for n in bounds)
        or min(bounds[2:]) == 0 or bounds[0] + bounds[2] > 1.000001 or bounds[1] + bounds[3] > 1.000001):
        raise ValueError('reference bounds must be a non-empty normalized rectangle inside the canvas')
    return bounds


def sample_colors(path, samples, base):
    if not samples:
        return {}
    if not path or Path(path).suffix.lower() == '.svg':
        raise ValueError('region sampling requires a readable raster reference; use observed_colors for SVG or visual observations')
    with Image.open(path) as image:
        if image.width * image.height > 50_000_000:
            raise ValueError('reference exceeds 50 megapixels')
        rgba = ImageOps.exif_transpose(image).convert('RGBA')
    samples = dict(samples)
    result = {}
    for role in ROLES:
        if role not in samples:
            continue
        x, y, width, height = normalized_box(samples[role])
        box = (int(x*rgba.width), int(y*rgba.height),
               min(rgba.width, max(int(x*rgba.width)+1, round((x+width)*rgba.width))),
               min(rgba.height, max(int(y*rgba.height)+1, round((y+height)*rgba.height))))
        crop = rgba.crop(box)
        crop.thumbnail((100, 100), Image.Resampling.NEAREST)
        background = Image.new('RGBA', crop.size, result.get('paper', base['paper']))
        rgb = Image.alpha_composite(background, crop).convert('RGB')
        lab = ImageCms.profileToProfile(rgb, ImageCms.createProfile('sRGB'), ImageCms.createProfile('LAB'), outputMode='LAB')
        buckets = {}
        for pixel, perceptual in zip(rgb.getdata(), lab.getdata()):
            key = tuple(component // 16 for component in perceptual)
            buckets.setdefault(key, Counter())[pixel] += 1
        cluster = max(buckets.values(), key=lambda values: sum(values.values()))
        result[role] = '#%02x%02x%02x' % cluster.most_common(1)[0][0]
    return result


def reference_theme(design, image_path, style):
    base = registry()['styles'][style]
    mode = design.get('palette_mode', 'auto')
    if mode not in ('auto', 'monochrome', 'domain'):
        raise ValueError('reference palette_mode must be auto, monochrome or domain')
    if mode == 'domain':
        return None, {'mode': 'domain'}
    samples = design.get('color_samples', {})
    observed = design.get('observed_colors', {})
    if any(role not in ROLES for role in (*samples, *observed)):
        raise ValueError('unknown reference color role')
    if any(not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value) for value in observed.values()):
        raise ValueError('observed_colors must be six-digit hex colors')
    sampled = {**sample_colors(image_path, samples, base), **observed}
    if not sampled and mode != 'monochrome':
        return None, {}
    def gray(value):
        level = round(sum(int(value[i:i+2], 16) * weight for i, weight in zip((1, 3, 5), (.2126, .7152, .0722))))
        return '#%02x%02x%02x' % (level, level, level)
    monochrome = mode == 'monochrome' or (
        'paper' in sampled and 'accent' in sampled and all(value.lower() == gray(value) for value in sampled.values()))
    theme = {**base, **sampled}
    if monochrome:
        theme = {role: gray(value) for role, value in theme.items() if role in ROLES}
    if 'paper' in sampled and 'surface' not in sampled:
        theme['surface'] = theme['paper']
    adjustments = {role: {'observed': value, 'used': theme[role]} for role, value in sampled.items()
                   if value.lower() != theme[role].lower()}
    for role in ('ink', 'muted', 'accent', 'secondary', 'tertiary'):
        if role not in theme:
            continue
        color = theme[role]
        def score(value):
            return min(contrast(value, theme[background]) for background in ('paper', 'surface'))
        if score(color) >= 4.5:
            continue
        rgb = tuple(int(color[index:index+2], 16) for index in (1, 3, 5))
        for step in range(1, 21):
            variants = ['#%02x%02x%02x' % tuple(round(channel + (endpoint-channel)*step/20) for channel in rgb)
                        for endpoint in (0, 255)]
            revised = max(variants, key=score)
            if score(revised) >= 4.5:
                theme[role] = revised
                adjustments[role] = {'observed': sampled.get(role, color), 'used': revised}
                break
        else:
            raise ValueError(f'reference {role} cannot meet contrast across both backgrounds; choose compatible surfaces or an explicit theme')
    theme['rationale'] = ('Monochrome theme preserving the selected reference.' if monochrome else
                          'Role-based colors sampled or observed from the selected reference.')
    return theme, {'mode': 'monochrome' if monochrome else 'reference', 'samples': samples,
                   'observed': sampled, 'adjustments': adjustments}


def apply_reference(plan, brief, suggestions, *, use_reference_colors=True):
    uploads = brief.get('reference_source') == 'upload'
    if uploads:
        if suggestions:
            raise ValueError('uploaded references bypass the library and Wiki')
        records = brief['uploaded_references']
        usable = {record['id']: record for record in records if record['status'] == 'readable'}
        for record in usable.values():
            if file_hash(record['path']) != record['sha256']:
                raise ValueError('uploaded reference changed since the brief was created')
    else:
        records = []
        chosen = {choice['id'] for choice in brief['design_decisions']['reference_choices_with_reasons']}
        usable = {row['id']: {'id': row['id'], 'path': row.get('image_path') if row.get('image_status') == 'verified' else None,
                             'sha256': row['sha256']} for row in (suggestions or {}).get('candidates', []) if row['id'] in chosen}
    design = brief['design_decisions'].get('reference_design')
    if not design:
        if uploads and usable:
            raise ValueError('inspect the uploaded reference and fill design_decisions.reference_design before planning')
        if uploads:
            plan['reference_design'] = {'source': 'upload', 'features': [], 'unavailable': [r['id'] for r in records]}
        return
    primary = design['primary_id']
    if primary not in usable:
        raise ValueError('primary reference must be a readable upload or a reviewed library choice')
    regions = {region['id']: region for region in plan['regions']}
    placements = design['placements']
    if not placements or not design['features']:
        raise ValueError('reference design requires placements and observable features')
    for region_id, change in placements.items():
        if region_id not in regions or change.keys() - {'bounds', 'appearance', 'tone', 'role', 'asset_fraction', 'asset_position'}:
            raise ValueError(f'invalid reference placement for {region_id}')
        normalized_box(change['bounds'])
        regions[region_id].update(change)
    if 'canvas' in design:
        plan['canvas'] = design['canvas']
    elif 'size' in usable[primary]:
        width, height = usable[primary]['size']
        longest = max(width, height)
        plan['canvas'] = {'width': max(400, round(1800*width/longest)), 'height': max(400, round(1800*height/longest))}
    for key in ('groups', 'display_width_px'):
        if key in design:
            plan[key] = design[key]
    features = []
    for item in design['features']:
        reference_id = item['reference_id']
        targets = item['target_regions']
        if (reference_id not in usable or not targets or set(targets) - regions.keys()
            or not item['observation'].strip() or not item['check'].strip()):
            raise ValueError('reference feature needs a usable source, target regions, observation and check')
        feature = {key: item[key] for key in ('reference_id', 'source_bounds', 'target_regions', 'observation', 'check')}
        normalized_box(feature['source_bounds'])
        if item.get('adaptation'):
            feature['adaptation'] = item['adaptation']
        for key in ('target_group', 'target_relations', 'required'):
            if key in item:
                feature[key] = item[key]
        features.append(feature)
    path = usable[primary]['path']
    if path and file_hash(path) != usable[primary]['sha256']:
        raise ValueError('primary reference image no longer matches its recorded hash')
    color_theme, colors = reference_theme(design, path, plan['style_id']) if use_reference_colors else (None, {'mode': 'explicit'})
    if color_theme:
        plan['theme'] = color_theme
    plan['reference_design'] = {
        'source': 'upload' if uploads else 'library', 'primary_id': primary,
        'features': features, 'images': {key: usable[key]['sha256'] for key in {primary, *(f['reference_id'] for f in features)}},
        'unavailable': [r['id'] for r in records if r['status'] != 'readable'],
        'color_evidence': colors,
    }
