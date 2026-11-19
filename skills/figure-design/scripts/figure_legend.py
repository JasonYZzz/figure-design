"""Render a local, declarative Three.js scene to a transparent vector illustration."""
from pathlib import Path
from math import isfinite
import re

from playwright.sync_api import sync_playwright
from figure_common import ROOT


def validate_scene(scene):
    if not isinstance(scene, dict) or not isinstance(scene.get('title'), str) or not scene['title'].strip():
        raise ValueError('scene needs a title')
    objects = scene.get('objects')
    if not isinstance(objects, list) or not 1 <= len(objects) <= 128:
        raise ValueError('scene needs 1–128 objects')
    for obj in objects:
        if not isinstance(obj, dict) or obj.get('shape') not in ('box', 'sphere', 'cylinder'):
            raise ValueError('shape must be box, sphere or cylinder')
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', str(obj.get('color'))):
            raise ValueError('color must be #RRGGBB')
        for key in ('size', 'position'):
            values = obj.get(key)
            if not isinstance(values, list) or len(values) != 3 or any(
                type(v) not in (int, float) or abs(v) > 1000 or not isfinite(v)
                or (key == 'size' and v < .001) for v in values
            ):
                raise ValueError(f'{key} needs three finite coordinates within scene bounds')


def render_legend(scene, out):
    validate_scene(scene)
    target = Path(out)
    if target.suffix.lower() != '.svg' or target.exists():
        raise ValueError('choose a new .svg output')
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.add_script_tag(path=ROOT/'third_party/three-svg/runtime.js')
        svg = page.evaluate((ROOT/'scripts/legend_scene.js').read_text(), scene)
        browser.close()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(svg)
    return {'svg': str(target), 'objects': len(scene['objects']), 'status': 'review_required'}
