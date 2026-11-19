import os
from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from figure_assets import validate_image
from figure_common import read
from figure_legend import validate_scene, render_legend


class ThreeLegendTests(unittest.TestCase):
    def test_invalid_shape_size_and_position(self):
        for key, value in [('shape', 'custom'), ('size', [1, 0, 1]), ('position', [1, float('nan'), 0])]:
            scene = read(ROOT/'assets/legends/feature-stack.json')
            scene['objects'][0][key] = value
            with self.assertRaises(ValueError):
                validate_scene(scene)

    @unittest.skipUnless(os.getenv('FIGURE_RENDER_TESTS'), 'requires Chromium')
    def test_vector_output_fits_asset_contract(self):
        scene = read(ROOT/'assets/legends/storage-tiers.json')
        scene['title'] = '<tier> & capacity'
        with tempfile.TemporaryDirectory() as directory:
            svg = Path(directory)/'legend.svg'
            render_legend(scene, svg)
            self.assertEqual(validate_image(svg), 'image/svg+xml')
            root = ET.parse(svg).getroot()
            self.assertEqual(root.find('{*}title').text, scene['title'])
            self.assertGreater(len(root.findall('{*}path')), 1)
            with self.assertRaisesRegex(ValueError, 'new .svg'):
                render_legend(scene, svg)
