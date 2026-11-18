import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from cases import make_case
from figure_common import read,write,file_hash,fingerprint
from figure_sources import ingest,evidence
from figure_catalog import index,search,annotate
from figure_plan import registry,make_plan,candidates
from figure_assets import register,request,operation_update,split_sheet
from figure_geometry import route
from figure_data import chart


class StandaloneContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.content,self.sources=make_case(self.root/'case')
    def tearDown(self):self.temp.cleanup()

    def test_exact_source_and_forged_snapshot(self):
        self.assertEqual(evidence(self.content,self.sources)['status'],'pass')
        bad=copy.deepcopy(self.content);bad['sources'][0]['excerpt']='invented'
        self.assertEqual(evidence(bad,self.sources)['status'],'blocked_content')
        path=Path(self.sources[0]);snapshot=read(path);snapshot['text']+='forged';snapshot['text_sha256']=fingerprint(snapshot['text']);write(path,snapshot)
        with self.assertRaisesRegex(ValueError,'re-extracted'):evidence(self.content,self.sources)

    def test_planned_cannot_be_validated(self):
        self.content['relations'][0]['evidence_state']='validated'
        self.assertIn('established relation',' '.join(evidence(self.content,self.sources)['errors']))

    def test_research_brief_preserves_evidence_without_inventing_decisions(self):
        from figure_research import research_brief
        original=copy.deepcopy(self.content)
        brief=research_brief(self.content,self.sources)
        self.assertEqual(self.content,original)
        self.assertEqual(brief['source_content_hash'],fingerprint(original))
        self.assertEqual(brief['relations'],original['relations'])
        self.assertEqual([r['task_id'] for r in brief['evidence_map']],[t['id'] for t in original['tasks']])
        self.assertIsNone(brief['design_decisions']['main_question_or_supported_claim'])
        self.assertIsNone(brief['design_decisions']['visual_concept']['route'])
        self.content['sources'][0]['excerpt']='invented'
        with self.assertRaises(ValueError):research_brief(self.content,self.sources)

    def test_local_svg_resource_closure(self):
        from figure_assets import validate_image
        from vendor.ppt_master_svg_resources import svg_image_payload_error
        from base64 import b64encode
        bad=b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/a.png"/></svg>'
        nested=b'<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/svg+xml;base64,'+b64encode(bad)+b'"/></svg>'
        self.assertIn('embedded SVG',svg_image_payload_error(nested))
        path=self.root/'external.svg'
        path.write_bytes(b'<?xml-stylesheet href="remote.css"?><svg xmlns="http://www.w3.org/2000/svg"/>')
        with self.assertRaisesRegex(ValueError,'resource closure'):validate_image(path)
        path.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>')
        self.assertEqual(validate_image(path),'image/svg+xml')

    def test_plan_cli_keeps_route_and_variant_when_selecting_layouts(self):
        content_path = self.root/'content.json'
        write(content_path, self.content)
        out = self.root/'plans'
        subprocess.run([sys.executable, str(ROOT/'scripts/figure.py'), 'plan',
                        '--content', str(content_path), '--out', str(out),
                        '--route', 'asset_composite', '--variant', 'portrait'],
                       check=True, capture_output=True, text=True)
        for name in ('candidate-1.json', 'candidate-2.json'):
            plan = read(out/name)
            self.assertEqual(plan['route'], 'asset_composite')
            self.assertEqual(plan['canvas'], {'width': 1200, 'height': 1800})

    def test_docx_and_source_rejection(self):
        path=self.root/'source.docx'
        with ZipFile(path,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>中文文本</w:t></w:r></w:p></w:document>')
        result=ingest(path,self.root/'docs');self.assertEqual(read(result['source'])['text'],'中文文本')
        blank=self.root/'blank.md';blank.write_text(' ')
        with self.assertRaises(ValueError):ingest(blank,self.root/'docs')

    def test_catalog_stable_ids_and_review_gate(self):
        from PIL import Image
        refs=self.root/'refs';refs.mkdir();Image.new('RGB',(10,20),'red').save(refs/'b.png')
        catalog=self.root/'refs.sqlite';index(refs,catalog);original=search(catalog)[0]
        Image.new('RGB',(10,20),'blue').save(refs/'a.png');index(refs,catalog)
        self.assertIn(original['id'],{r['id'] for r in search(catalog)})
        item={'id':original['id'],'sha256':original['sha256'],'composition_tags':['center-hero-side-support'],'observations':['central object']}
        annotate(catalog,{'reviewer':'test model','reviewer_kind':'model','records':[item]})
        self.assertEqual(search(catalog,'center')[0]['review_status'],'auto_proposed')
        self.assertFalse(search(catalog,'center',reviewed_only=True))
        item['license_state']='authorized_reuse'
        with self.assertRaises(ValueError):annotate(catalog,{'reviewer':'test','reviewer_kind':'model','records':[item]})

    def test_all_layouts_and_distinct_candidates(self):
        generated=[]
        for name in registry()['layouts']:
            c,s=make_case(self.root/name,count=3)
            plan=make_plan(c,name,'biomedicine-academic');generated.append(plan)
            placed=[i for r in plan['regions'] for i in r['label_instance_ids']]
            self.assertEqual(set(placed),{i['id'] for i in c['label_instances']})
        self.assertEqual(len(generated),12)
        pair=candidates(self.content)
        self.assertEqual(len(pair),2);self.assertEqual(pair[0]['content_hash'],pair[1]['content_hash'])
        self.assertNotEqual(pair[0]['plan']['regions'],pair[1]['plan']['regions'])

    def test_cli_plan_modes_and_diagram_types(self):
        content_path = self.root/'content.json'
        write(content_path, self.content)
        command = [sys.executable, str(ROOT/'scripts/figure.py'), 'plan', '--content', str(content_path)]
        for name, args, route, diagram_type, layout in (
            ('roadmap', ['--mode', 'text'], 'text_structured', 'roadmap', 'annual-stage-timeline'),
            ('architecture', ['--mode', 'text', '--diagram-type', 'architecture'], 'text_structured',
             'architecture', 'top-overview-multi-lane'),
            ('mixed', ['--mode', 'mixed', '--layout', 'center-hero-side-support'], 'asset_composite',
             None, 'center-hero-side-support'),
        ):
            out = self.root/name
            run = subprocess.run(command + args + ['--out', str(out)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            plan = read(out/'candidate-1.json')
            self.assertEqual(plan['mode'], 'mixed' if name == 'mixed' else 'text')
            self.assertEqual((plan['route'], plan.get('diagram_type'), plan['grammar']['primary']),
                             (route, diagram_type, layout))
        out = self.root/'bad'
        run = subprocess.run(command + ['--mode', 'text', '--route', 'asset_composite', '--out', str(out)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(out.exists())

    def test_route_avoids_middle_obstacle(self):
        source=[30,150,80,80];target=[390,150,80,80];obstacle=[200,100,100,200]
        points=route(source,target,[source,target,obstacle],(500,400))
        self.assertGreater(len(points),2)
        for a,b in zip(points,points[1:]):
            self.assertTrue(a[0]==b[0] or a[1]==b[1])
            if a[0]==b[0]:self.assertFalse(200<a[0]<300 and max(min(a[1],b[1]),100)<min(max(a[1],b[1]),300))
            else:self.assertFalse(100<a[1]<300 and max(min(a[0],b[0]),200)<min(max(a[0],b[0]),300))

    def test_image_request_unknown_is_not_retried(self):
        out=self.root/'operations';a=request(self.content,'T1','illustration',out,'OP1',1)
        self.assertEqual(request(self.content,'T1','illustration',out,'OP1',1),a)
        with self.assertRaises(ValueError):request(self.content,'T1','changed',out,'OP1',1)
        path=out/'OP1/operation.json';operation_update(path,'submitted',provider='test tool');operation_update(path,'unknown')
        with self.assertRaises(ValueError):operation_update(path,'submitted',provider='test tool')

    def test_assets_and_sheets_remain_governed(self):
        from PIL import Image
        im=self.root/'asset.png';Image.new('RGBA',(80,80),(0,90,100,255)).save(im)
        metadata={'id':'asset1','scientific_type':'module','style_family_id':'biomedicine-academic','rights':'unknown','approval':'production_approved','origin':'synthetic test','source_content_ids':['T1'],'reviewer':'test fixture','review_note':'test only','contains_evidence':False}
        with self.assertRaises(ValueError):register(im,metadata,self.root/'library')
        metadata['rights']='authorized_reuse';record=register(im,metadata,self.root/'library');self.assertEqual(record['file_sha256'],file_hash(im))
        crops=split_sheet(im,[{'id':'crop1','bounds':[0,0,40,40]}],self.root/'crops')
        self.assertEqual(crops[0]['approval'],'candidate');self.assertEqual(crops[0]['rights'],'unknown')

    def test_data_chart_preserves_values(self):
        path=self.root/'data.csv';path.write_text('time,value\n1,-2\n2,4\n3,3\n')
        result=chart(path,self.root/'chart','time','value','Synthetic values','bar')
        self.assertEqual(result['points'],[(1.,-2.),(2.,4.),(3.,3.)])
        path.write_text('time,value\n1,NaN\n2,3\n')
        with self.assertRaises(ValueError):chart(path,self.root/'bad','time','value','bad')

    def test_installer_hashes_and_existing_target(self):
        from install import install
        source=self.root/'package';source.mkdir();(source/'SKILL.md').write_text('test skill')
        write(source/'package-manifest.json',{'files':{'SKILL.md':file_hash(source/'SKILL.md')}})
        destination=self.root/'skills';target=install(source,destination)
        self.assertEqual((target/'SKILL.md').read_text(),'test skill')
        with self.assertRaises(ValueError):install(source,destination)
        (source/'SKILL.md').write_text('tampered')
        with self.assertRaises(ValueError):install(source,self.root/'other')

    def test_packages_separate_private_images_and_verify_catalog(self):
        from unittest.mock import patch
        from PIL import Image
        from figure import pack
        from install import install
        skill=self.root/'source';library=skill/'assets/reference-library';images=library/'images'
        images.mkdir(parents=True);(skill/'SKILL.md').write_text('test skill')
        Image.new('RGB',(20,20),'white').save(images/'ref.png')
        index(images,library/'catalog.sqlite')
        (library/'human-review').mkdir();(library/'human-review/review.html').write_text('private pixels')
        (library/'thumbnails').mkdir();(library/'thumbnails/preview.png').write_bytes(b'private pixels')
        with patch('figure.ROOT',skill):
            pack(self.root/'light.zip')
            pack(self.root/'private.zip',images)
            with ZipFile(self.root/'light.zip') as z:
                self.assertFalse(any('/images/' in n or '/human-review/' in n or '/thumbnails/' in n for n in z.namelist()))
                self.assertFalse(json.loads(z.read('scientific-figure-designer/package-manifest.json'))['reference_images_included'])
            with ZipFile(self.root/'private.zip') as z:
                self.assertEqual(sum('/images/' in n for n in z.namelist()),1)
                z.extractall(self.root/'unpacked')
            target=install(self.root/'unpacked/scientific-figure-designer',self.root/'installed')
            self.assertEqual(file_hash(target/'assets/reference-library/images/ref.png'),file_hash(images/'ref.png'))
            Image.new('RGB',(20,20),'black').save(images/'ref.png')
            with self.assertRaisesRegex(ValueError,'match the bundled catalog'):pack(self.root/'mismatch.zip',images)
            self.assertFalse((self.root/'mismatch.zip').exists())


@unittest.skipUnless(os.environ.get('FIGURE_RENDER_TESTS')=='1','set FIGURE_RENDER_TESTS=1 for Chromium integration tests')
class BrowserIntegration(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()

    def test_render_exact_unicode_cache_patch_and_export(self):
        from figure import render_job,verify_bundle,export
        c,s=make_case(self.root/'case',number=1)
        p=make_plan(c,'top-overview-multi-lane','biomedicine-academic',mode='text',diagram_type='architecture')
        out=self.root/'render'
        report=render_job(c,p,s,out);self.assertFalse(report['errors'])
        self.assertEqual(report['composition'], {'route': 'text_structured', 'mode': 'text',
            'diagram_type': 'architecture', 'html_template': 'diagram-design', 'asset_placements': []})
        scene=read(out/'scene.json')
        measured=next(o for o in scene['objects'] if o.get('label_instance_id')=='I2')
        self.assertTrue(any('10 μmol/L' in line for line in measured['lines']))
        html = (out/'preview.html').read_text()
        self.assertIn('class="diagram-container" data-diagram-type="architecture"', html)
        self.assertIn((out/'preview.svg').read_text(), html)
        self.assertNotIn('<image', html)
        self.assertNotIn('fonts.googleapis.com', html)
        self.assertFalse((out/'preview.pdf').exists())
        self.assertEqual(len(report['label_manifest']),len(c['label_instances']))
        self.assertEqual({r['id']:r['text'] for r in report['relation_label_manifest']},{r['id']:'步骤' for r in c['relations']})
        self.assertTrue(render_job(c,p,s,out)['metrics']['cache_hit'])
        with self.assertRaises(ValueError):export(out,self.root/'final.zip',final=True)
        exported=export(out,self.root/'draft.zip');self.assertEqual(exported['status'],'review_required')
        with ZipFile(self.root/'draft.zip') as z:
            self.assertEqual(z.read('preview.html').decode(), html)
            self.assertNotIn('preview.pdf', z.namelist())
        patched=copy.deepcopy(c);patched['labels'][1]['text']='拟调整研究条件';patched['labels'][1]['kind']='approved_summary'
        second=render_job(patched,p,s,self.root/'patch');self.assertEqual(second['metrics']['paid_calls'],0)
        self.assertNotEqual(second['render_hash'],report['render_hash'])
        (out/'preview.html').write_text('tampered')
        with self.assertRaises(ValueError):verify_bundle(out)

    def test_capacity_missing_glyph_and_wrong_edge_block(self):
        from figure_render import render
        c,s=make_case(self.root/'case');p=make_plan(c,'top-overview-multi-lane','cs-academic')
        bad=copy.deepcopy(c);bad['labels'][1]['text']='长标签'*150;bad['labels'][1]['kind']='approved_summary'
        with self.assertRaisesRegex(ValueError,'text_capacity'):render(bad,p,s,self.root/'none',preflight=True)
        bad['labels'][1]['text']='\U0001f984'
        with self.assertRaisesRegex(ValueError,'glyph'):render(bad,p,s,self.root/'none',preflight=True)
        p['edges'][0]['source_region_id']='owner-3'
        with self.assertRaisesRegex(ValueError,'owner'):render(c,p,s,self.root/'none',preflight=True)

    def test_asset_and_image_first_routes(self):
        from PIL import Image
        from figure import render_job
        from figure_render import render
        c,s=make_case(self.root/'case',count=3)
        im=self.root/'asset.png';Image.new('RGBA',(100,100),(0,90,100,255)).save(im)
        register(im,{'id':'module1','scientific_type':'module','style_family_id':'biomedicine-academic','rights':'authorized_reuse','approval':'production_approved','origin':'synthetic test shape','source_content_ids':['T1'],'reviewer':'software test fixture','review_note':'not a human acceptance record','contains_evidence':False},self.root/'library')
        manifest=self.root/'library/module1/asset.json'
        for route in ['asset_composite','image_first','strict_scientific']:
            p=make_plan(c,'center-hero-side-support','biomedicine-academic',route=route,
                        mode='mixed' if route == 'asset_composite' else None)
            if route == 'asset_composite':
                with self.assertRaisesRegex(ValueError, 'requires at least one approved asset'):
                    render(c, p, s, None, preflight=True)
            p['regions'][1]['asset_ids']=['module1']
            report=render_job(c,p,s,self.root/route,[manifest])
            self.assertFalse(report['errors']);self.assertEqual(report['format'],'hybrid_svg')
            self.assertEqual(report['composition'], {'route': route, 'mode': 'mixed',
                'html_template': 'scientific-figure-designer',
                'asset_placements': [{'region_id': p['regions'][1]['id'], 'asset_id': 'module1'}]})
            self.assertIn('href="data:image/png;base64,', (self.root/route/'preview.html').read_text())
            if route=='image_first':self.assertIn('native_image_text_and_arrows_review',report['pending'])
        p=make_plan(c,'annual-stage-timeline','biomedicine-academic',mode='text',diagram_type='roadmap')
        report=render_job(c,p,s,self.root/'roadmap')
        self.assertFalse(report['errors'])
        self.assertEqual(report['composition']['diagram_type'], 'roadmap')
        p['regions'][1]['asset_ids']=['module1']
        with self.assertRaisesRegex(ValueError, 'text mode does not accept'):
            render(c,p,s,None,[manifest],preflight=True)


if __name__=='__main__':unittest.main()
