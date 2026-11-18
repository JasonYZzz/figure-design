from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_contract import validate
from inventory_refs import inventory
from figure_render import bindings

class FigureSkillSmoke(unittest.TestCase):
    def setUp(self):
        self.cs=json.loads((ROOT/'schemas/figure-content.schema.json').read_text())
        self.ps=json.loads((ROOT/'schemas/composition-plan.schema.json').read_text())
        self.content=json.loads((ROOT/'tests/fixtures/figure_content.json').read_text())
        self.plan=json.loads((ROOT/'tests/fixtures/composition_plan.json').read_text())
    def test_fixtures_validate(self):
        self.assertEqual(validate(self.cs,self.content),[])
        self.assertEqual(validate(self.ps,self.plan),[])
    def test_dangling_relation_blocks(self):
        bad=copy.deepcopy(self.content);bad['relations'][0]['to_id']='MISSING'
        self.assertTrue(validate(self.cs,bad))
    def test_dangling_region_blocks(self):
        bad=copy.deepcopy(self.plan);bad['edges'][0]['target_region_id']='MISSING'
        self.assertTrue(validate(self.ps,bad))
    def test_duplicate_plan_relation_blocks(self):
        bad=copy.deepcopy(self.plan); bad['edges'].append(copy.deepcopy(bad['edges'][0]))
        self.assertTrue(validate(self.ps,bad))
    def test_inventory_dupes_and_rights(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'one.png'
            Image.new('RGB',(20,30),(230,100,70)).save(p)
            (root/'two.png').write_bytes(p.read_bytes())
            rows,errors=inventory(root)
            self.assertFalse(errors)
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[1]['exact_duplicate_of'],rows[0]['id'])
            self.assertTrue(all(r['license_state']=='unknown' for r in rows))

    def test_required_instances_and_critical_edges_block(self):
        for change in ('missing_label','duplicate_label','unknown_label','missing_edge','wrong_owner'):
            with self.subTest(change=change):
                content,plan=copy.deepcopy(self.content),copy.deepcopy(self.plan)
                if change=='missing_label':plan['regions'][0]['label_instance_ids']=[]
                if change=='duplicate_label':plan['regions'][1]['label_instance_ids'].append('LI_TITLE')
                if change=='unknown_label':plan['regions'][0]['label_instance_ids']=['MISSING']
                if change=='missing_edge':plan['edges']=[]
                if change=='wrong_owner':plan['edges'][0]['source_region_id']='R_HERO'
                with self.assertRaises(ValueError):bindings(content,plan)



    def test_ambiguous_owner_blocks(self):
        self.content['entities'][0]['id']='TASK1'
        self.assertTrue(validate(self.cs,self.content))

    def test_external_schema_reference_rejected(self):
        self.assertTrue(validate({'$ref':'https://example.invalid/no-network'},{}))


    def test_inventory_nested_exif_corrupt_and_readonly(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);nested=root/'nested';nested.mkdir()
            image=Image.new('RGB',(20,30));exif=Image.Exif();exif[274]=6
            image.save(nested/'rotated.jpg',exif=exif)
            (root/'bad.png').write_bytes(b'not an image')
            before={p.relative_to(root):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
            rows,errors=inventory(root)
            self.assertEqual(len(errors),1)
            self.assertEqual((rows[0]['width'],rows[0]['height']),(30,20))
            self.assertEqual(rows[0]['path'],'nested/rotated.jpg')
            self.assertEqual(before,{p.relative_to(root):(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()})

    def test_inventory_symlinks_rejected(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);refs=root/'refs';refs.mkdir()
            Image.new('RGB',(20,30)).save(root/'outside.png')
            (refs/'link.png').symlink_to(root/'outside.png')
            rows,errors=inventory(refs)
            self.assertFalse(rows);self.assertEqual(len(errors),1)

    def test_inventory_cli_protects_original_and_reports_count(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);refs=root/'refs';refs.mkdir()
            original=refs/'one.png';Image.new('RGB',(20,30)).save(original)
            before=original.read_bytes()
            command=[sys.executable,str(ROOT/'scripts/inventory_refs.py'),'--input',str(refs),'--out']
            result=subprocess.run(command+[str(original)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2);self.assertEqual(original.read_bytes(),before)
            out=root/'references.jsonl'
            result=subprocess.run(command+[str(out),'--expected-count','2'],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertFalse(json.loads(result.stdout)['count_matches'])
            out.with_suffix('.errors.json').write_text('["stale error"]')
            result=subprocess.run(command+[str(out),'--expected-count','1'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(out.with_suffix('.errors.json').read_text()),[])
            self.assertEqual(original.read_bytes(),before)

if __name__=='__main__':unittest.main()
