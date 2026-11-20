"""Regression coverage for uploaded references, themed assets and PDF recovery."""
import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from cases import make_case
from figure import export, render_job, visual_review
from figure_assets import register_themed
from figure_common import file_hash, read, write
from figure_plan import default_style, figure_theme, registry
from figure_reference import ROLES, reference_theme
from figure_render import readout_visuals, render
from figure_sources import evidence, ingest


class ReferenceDesign(unittest.TestCase):
    def test_readout_visuals_follow_owner_across_regions(self):
        instances = {key: {'owner_id': owner, 'role': role} for key, owner, role in [
            ('a', 'trial', 'readout'), ('b', 'trial', 'task'), ('c', 'control', 'readout')]}
        regions = {'results': {'label_instance_ids': ['a', 'c']},
                   'graph': {'label_instance_ids': ['b'], 'asset_ids': ['measure']}}
        assets = {'measure': {'source_content_ids': ['trial'], 'contains_evidence': True}}
        trial, control = readout_visuals(regions, instances, assets)
        self.assertEqual(trial['evidence_assets'], ['measure'])
        self.assertEqual(control['evidence_assets'], [])
        self.assertEqual(trial['readout_instances'], ['a'])

    @unittest.skipUnless(os.environ.get('FIGURE_RENDER_TESTS') == '1', 'requires Chromium')
    def test_source_bound_edge_label_and_evidence_target(self):
        from figure_plan import make_plan
        from figure_render import bindings

        content, sources = make_case(self.root/'operation', count=2, relation_type='tests')
        content['labels'].append(dict(id='action', text='核对采集条件', kind='approved_summary',
                                      approved=True, source_ids=['S1', 'S2']))
        content['label_instances'].append(dict(id='operation', label_id='action', owner_id='R1',
                                               role='operation', required=True))
        plan = make_plan(content, 'top-overview-multi-lane', 'computing-systems', route='asset_composite')
        self.assertEqual(plan['edges'][0]['label_instance_id'], 'operation')
        bad = copy.deepcopy(plan)
        bad['edges'][0]['label_instance_id'] = 'I1'
        with self.assertRaisesRegex(ValueError, 'owned by its relation'):
            bindings(content, bad)
        for region, x in zip(plan['regions'][1:], [.05, .65]):
            region['bounds'] = [x, .3, .30, .42]
        asset = self.root/'operation.svg'
        asset.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><circle cx="10" cy="10" r="7" fill="{{figure:accent}}"/></svg>')
        register_themed(asset, dict(id='sample', scientific_type='fixture',style_family_id='test',
            rights='authorized_reuse', approval='production_approved', origin='test fixture',
            source_content_ids=['T1'], reviewer='fixture', review_note='geometric test',contains_evidence=False),
            self.root/'assets', plan)
        plan['regions'][1]['asset_ids'] = ['sample']
        report = render_job(content, plan, sources, self.root/'operation-render', [self.root/'assets/sample/asset.json'])
        self.assertFalse(report['errors'])
        self.assertEqual(report['relation_label_manifest'][0]['text'], '核对采集条件')
        self.assertEqual([item['id'] for item in report['label_manifest']].count('operation'), 1)
        self.assertEqual(report['composition']['relation_review']['evidence_links'], content['relations'])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.content, self.sources = make_case(self.root/'case', count=3)
        self.content['domain'] = '睡眠科技'
        self.content_path = self.root/'content.json'
        write(self.content_path, self.content)

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/figure.py'), *map(str,args)],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return json.loads(result.stdout if ok else result.stderr)

    def reference_plan(self, variant='wide'):
        width, height = (960,600) if variant == 'wide' else (600,960)
        primary = '#663574' if variant == 'wide' else '#244f83'
        reference = self.root/(variant+'.png')
        paper = '#f7f4ef'
        image = Image.new('RGB', (width,height), paper)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0,height//5,width*9//10,height*4//5),fill='#ff1100')
        draw.rectangle((width//10,height//10,width//2,height//7),fill=primary)
        image.save(reference)
        corrupt = self.root/'invalid.svg'
        corrupt.write_text('<svg')
        brief_path = self.root/(variant+'-brief.json')
        self.cli('research-brief','--content',self.content_path,'--sources',*self.sources,
            '--reference-image',corrupt,reference,'--reference-query','sleep','--catalog',self.root/'nonexistent',
            '--out',brief_path)
        brief = read(brief_path)
        self.assertNotIn('reference_suggestions',brief)
        self.assertEqual([record['status'] for record in brief['uploaded_references']],['unavailable','readable'])
        error = self.cli('refs-search','--brief',brief_path,'--catalog',self.root/'nonexistent',ok=False)
        self.assertIn('bypass the library',error['message'])
        coords = ([[.04,.21,.25,.6],[.375,.21,.25,.6],[.71,.21,.25,.6]] if variant == 'wide'
                  else [[.12,.19,.76,.18],[.12,.45,.76,.18],[.12,.71,.76,.18]])
        bounds = [.08,.19,.84,.7]
        brief['design_decisions']['reference_design'] = {
            'primary_id':'upload-2',
            'placements':{f'owner-{i}':{'bounds':box,'appearance':'band','tone':'secondary'}
                          for i,box in enumerate(coords,1)},
            'features':[{'reference_id':'upload-2','source_bounds':bounds,'target_regions':['owner-1','owner-2','owner-3'],
                         'observation':'主流程按参考图分区','check':'观察目标尺寸的分区方向'}],
            'color_samples':{'paper':[.01,.01,.04,.02],'accent':[.15,.11,.06,.015]},
            'observed_colors':{'secondary':'#245788','tertiary':'#834224'}}
        write(brief_path, brief)
        out = self.root/(variant+'-plan')
        self.cli('plan','--mode','mixed','--content',self.content_path,'--brief',brief_path,'--out',out)
        plan = read(out/'candidate-1.json')
        self.assertEqual(plan['theme']['paper'],paper)
        self.assertEqual(plan['theme']['accent'],primary)
        self.assertEqual(plan['reference_design']['images'],{'upload-2':file_hash(reference)})
        return plan, brief_path

    def test_upload_route_and_reference_geometry(self):
        wide, brief = self.reference_plan()
        tall, _ = self.reference_plan('tall')
        self.assertGreater(wide['canvas']['width'],wide['canvas']['height'])
        self.assertLess(tall['canvas']['width'],tall['canvas']['height'])
        self.assertNotEqual(wide['regions'][2]['bounds'],tall['regions'][2]['bounds'])
        override = self.root/'override'
        self.cli('plan','--mode','mixed','--content',self.content_path,'--brief',brief,
                 '--style','materials-testing','--out',override)
        explicit = read(override/'candidate-1.json')
        self.assertEqual(explicit['theme_source'],'explicit')
        self.assertNotEqual(figure_theme(explicit)['accent'],wide['theme']['accent'])
        self.assertEqual(explicit['regions'],wide['regions'])
        bad = read(brief)['uploaded_references'][0]['path']
        unavailable = self.root/'unavailable.json'
        self.cli('research-brief','--content',self.content_path,'--sources',*self.sources,
                 '--reference-image',bad,'--out',unavailable)
        self.cli('plan','--mode','mixed','--content',self.content_path,'--brief',unavailable,'--out',self.root/'fallback')
        self.assertIn('bypass',self.cli('refs-search','--brief',unavailable,ok=False)['message'])
        for style in registry()['styles']:
            figure_theme({'style_id':style})
        self.assertEqual(default_style(self.content['domain']),'sleep-systems')
        no_reference = self.root/'no-reference.json'
        self.cli('research-brief','--content',self.content_path,'--sources',*self.sources,'--out',no_reference)
        fallback = self.root/'domain-plan'
        self.cli('plan','--mode','mixed','--content',self.content_path,'--brief',no_reference,'--out',fallback)
        plan = read(fallback/'candidate-1.json')
        self.assertEqual((plan['theme_source'], plan['style_id']), ('domain_preset', 'sleep-systems'))

    def test_monochrome_reference_and_explicit_palette_intent(self):
        design = {'observed_colors': {'paper':'#FFFFFF','accent':'#444444'}}
        theme, detail = reference_theme(design, None, 'sleep-systems')
        self.assertEqual(detail['mode'], 'monochrome')
        self.assertEqual(theme['accent'], '#444444')
        for role in ROLES:
            self.assertEqual(len({theme[role][column:column+2] for column in (1, 3, 5)}), 1)
        self.assertEqual(reference_theme({**design, 'palette_mode':'domain'}, None, 'sleep-systems'),
                         (None, {'mode':'domain'}))
        _, detail = reference_theme({'observed_colors': {'paper':'#ffffff'}}, None, 'sleep-systems')
        self.assertEqual(detail['mode'], 'reference')

    def test_pdf_unicode_recovery_and_atomic_failure(self):
        pdf = self.root/'source.pdf'
        pdf.write_bytes(b'fixture')
        reader = SimpleNamespace(is_encrypted=False,pages=[SimpleNamespace(extract_text=lambda:'有效\ud800'),
                                                           SimpleNamespace(extract_text=lambda:'valid')])
        target = self.root/'snapshots'
        with patch('pypdf.PdfReader',return_value=reader):
            with patch('figure_sources.shutil.which',return_value=None):
                with self.assertRaisesRegex(ValueError,'pages 1'):
                    ingest(pdf,target)
            self.assertFalse(target.exists())
            with patch('figure_sources.shutil.which',return_value='/local/pdftotext'), \
                 patch('figure_sources.subprocess.run',return_value=SimpleNamespace(stdout='修复页\n'.encode())) as poppler:
                source = read(ingest(pdf,target)['source'])
                self.assertEqual(source['pdf_fallback']['pages'],[1])
                self.assertEqual(source['text'],'修复页\n\f\nvalid')
                self.assertEqual(poppler.call_args.args[0][1:5],['-f','1','-l','1'])
        fixture_text = read(self.sources[0])['text']
        reader.pages[1].extract_text = lambda: fixture_text
        content = copy.deepcopy(self.content)
        for citation in content['sources']:
            citation['document_sha256'] = file_hash(pdf)
        with patch('pypdf.PdfReader',return_value=reader), patch('figure_sources.shutil.which',return_value=None):
            transcribed = ingest(pdf, self.root/'transcribed', transcripts={'1':fixture_text})['source']
            self.assertEqual(read(transcribed)['pdf_transcripts'], {'1':fixture_text})
            check = evidence(content, [transcribed])
            self.assertFalse(check['errors'])
            self.assertEqual(check['pdf_sources'][0]['transcribed_pages'], [1])
        with patch('pypdf.PdfReader',return_value=reader), patch('figure_sources.shutil.which',return_value='/local/pdftotext'), \
             patch('figure_sources.subprocess.run',return_value=SimpleNamespace(stdout=(fixture_text+'\ufffd').encode())):
            incomplete = ingest(pdf, self.root/'incomplete')['source']
            self.assertTrue(any('unreadable PDF characters' in error for error in evidence(content, [incomplete])['errors']))

    @unittest.skipUnless(os.environ.get('FIGURE_RENDER_TESTS')=='1','requires Chromium')
    def test_reference_render_review_footer_theme_and_replay_export(self):
        for variant in ('wide','tall'):
            plan, _ = self.reference_plan(variant)
            picture = self.root/'themed.svg'
            picture.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20">'
                               '<rect width="40" height="20" fill="{{figure:accent}}"/>'
                               '<circle cx="20" cy="10" r="5" fill="#cf2307"/></svg>')
            asset_root = self.root/(variant+'-assets')
            register_themed(picture,{'id':'demo','scientific_type':'test','style_family_id':'test',
                'rights':'authorized_reuse','approval':'production_approved','origin':'original test SVG',
                'source_content_ids':['T1'],'reviewer':'automated test','review_note':'software fixture',
                'contains_evidence':False},asset_root,plan)
            asset = asset_root/'demo/asset.json'
            resolved = (asset.parent/'image.svg').read_text()
            self.assertIn(plan['theme']['accent'],resolved)
            self.assertIn('#cf2307',resolved)
            plan['regions'][1]['asset_ids']=['demo']
            if variant == 'wide':
                plan['regions'][1].update(asset_position='left',asset_fraction=.28)
                plan['groups'] = [{'id':'linked-stages','regions':['owner-1','owner-2','owner-3'],'tone':'tertiary'}]
                plan['reference_design']['features'][0].update(target_group='linked-stages', target_relations=['R1'], required=True)
                plan['edges'][0]['tone'] = 'secondary'
            plan['display_width_px'] = 600
            out = self.root/(variant+'-render')
            report = render_job(self.content,plan,self.sources,out,[asset])
            self.assertFalse(report['errors'])
            display = report['composition']['display_check']
            self.assertEqual(display['width_px'], 600)
            self.assertAlmostEqual(display['min_font_px_at_1000'], display['min_font_px'] * 1000 / 600)
            if variant == 'wide':
                objects = {item['id']: item for item in read(out/'scene.json')['objects']}
                x, _, w, _ = objects['image-owner-1']['bounds']
                self.assertLess(x+w,objects['label-I1']['bounds'][0])
                self.assertIn('R1', report['composition']['reference_relations'])
                svg = (out/'preview.svg').read_text()
                self.assertIn('data-region-group="linked-stages"', svg)
                self.assertIn('marker-end="url(#arrow-secondary)"', svg)
            bad = copy.deepcopy(plan)
            bad['reference_design']['features'][0]['target_regions']=['deleted']
            with self.assertRaisesRegex(ValueError,'targets missing regions'):
                render(self.content,bad,self.sources,None,[asset],preflight=True)
            bad = copy.deepcopy(plan)
            bad['theme']['accent']='#343030'
            with self.assertRaisesRegex(ValueError,'another theme'):
                render(self.content,bad,self.sources,None,[asset],preflight=True)
            if variant == 'wide':
                bad = copy.deepcopy(plan)
                bad['regions'][0]['bounds']=[.04,.925,.92,.075]
                bad['regions'][0]['text_safe']['padding_px']=8
                with self.assertRaisesRegex(ValueError,'label_overlap:.*figure-footer'):
                    render(self.content,bad,self.sources,None,[asset],preflight=True)
            review = {'render_hash':report['render_hash'],'display_width_px':600,'reflow_count':0,
                'reference_checks':[{'feature':1,'result':'retained','note':'Fixture layout checked'}],
                'palette_note':'Fixture colors checked'}
            self.assertEqual(visual_review(report,review),review)
            with self.assertRaisesRegex(ValueError,'stale'):
                visual_review(report,{**review,'render_hash':'other'})
            with self.assertRaisesRegex(ValueError,'measured display width'):
                visual_review(report,{**review,'display_width_px':601})
            review_path = self.root/'review.json'
            write(review_path,review)
            archive = self.root/(variant+'.zip')
            result = export(out,archive,review_path,include_sources=True,source_files=[picture])
            self.assertEqual(result['sha256'],file_hash(archive))
            with ZipFile(archive) as bundle:
                self.assertIsNone(bundle.testzip())
                self.assertIn('assets/demo/image.svg',bundle.namelist())
                self.assertIn('visual-review.json',bundle.namelist())
                self.assertIn('attachments/themed.svg',bundle.namelist())
                archived = json.loads(bundle.read('quality-report.json'))
                self.assertEqual(archived['visual_review'], review)
                self.assertEqual(archived['reference_review_summary']['retained'], 1)
                entries = json.loads(bundle.read('artifact-manifest.json'))['files']
                self.assertEqual(set(entries), set(bundle.namelist()) - {'artifact-manifest.json'})
                for name, digest in entries.items():
                    self.assertEqual(sha256(bundle.read(name)).hexdigest(), digest)
                self.assertFalse(any('wide.png' in name or 'tall.png' in name for name in bundle.namelist()))
            if variant == 'wide':
                plan.pop('groups')
                split = self.root/'split-render'
                deviation = render_job(self.content,plan,self.sources,split,[asset])
                self.assertNotEqual(deviation['render_hash'], report['render_hash'])
                deviation_review = {**review,'render_hash':deviation['render_hash']}
                with self.assertRaisesRegex(ValueError, 'feature 1 deviated'):
                    visual_review(deviation, deviation_review)
                deviation_review['reference_checks'] = [{'feature':1,'result':'adapted',
                    'note':'Panels are still separate', 'reason':'Shared band was removed'}]
                write(review_path,deviation_review)
                with self.assertRaisesRegex(ValueError, 'requires rework'):
                    export(split,self.root/'blocked.zip',review_path,final=True)
