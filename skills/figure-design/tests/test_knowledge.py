import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from figure_common import read,write,fingerprint,file_hash
from figure_knowledge import LIBRARY,WIKI_DIR,build,current,lint,records,validate_analysis,taxonomy,ingest_analyses
from figure_catalog import search,index
from figure_retrieval import tokens,resolve_images,save_feedback


class KnowledgeContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.lib=self.root/'library'
        self.lib.mkdir()
        for name in ('taxonomy.yaml','patterns.json','catalog.sqlite'):
            shutil.copyfile(LIBRARY/name,self.lib/name)
        shutil.copytree(LIBRARY/'analyses',self.lib/'analyses')
        self.catalog=self.lib/'catalog.sqlite'
        self.active_count=read(LIBRARY/'library.json')['count']
        self.result=build(self.lib,self.catalog)
    def tearDown(self):self.temp.cleanup()

    def test_chinese_constraints_and_enumeration(self):
        self.assertIn('并行',tokens('三条并行任务汇合'))
        self.assertEqual(len(search(self.catalog,limit=10000)),self.active_count)
        rows=search(self.catalog,'生物医药图文混合路线',require={'domain':'biomedicine','media':'illustrated'})
        self.assertTrue(rows)
        self.assertTrue(all(r['selection_score']>=0 for r in search(self.catalog,'并行',limit=self.active_count)))
        self.assertTrue(all(r['analysis']['facets']['media']=='illustrated' for r in rows))
        self.assertEqual(search(self.catalog,'四年技术路线图',require={'duration_years':'4'})[0]['path'],'ref-008.png')
        self.assertEqual(search(self.catalog,'卡通企鹅火星餐厅'),[])
        self.assertEqual(search(self.catalog,'图文',reviewed_only=True),[])
        with self.assertRaises(ValueError):search(self.catalog,'',require={'untrusted':'x'})

    def test_stale_analysis_and_corrupt_projection_block(self):
        p=next((self.lib/'analyses').glob('*.json'));a=read(p);a['title']+='变更';write(p,a)
        with self.assertRaisesRegex(ValueError,'stale'):search(self.catalog,'图文')
        new=build(self.lib,self.catalog);self.assertNotEqual(new['generation'],self.result['generation'])
        target=current(self.lib,self.catalog);(target/'index.sqlite').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'modified'):search(self.catalog,'图文')

    def test_build_failure_keeps_previous_generation_and_recovers(self):
        wiki=self.lib/WIKI_DIR
        previous=read(wiki/'current.json')
        p=next((self.lib/'analyses').glob('*.json'));a=read(p);a['title']+='新版';write(p,a)
        with patch('figure_knowledge._text',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):build(self.lib,self.catalog)
        self.assertEqual(read(wiki/'current.json'),previous)
        self.assertFalse(list((wiki/'generations').glob('.working-*')))
        new=build(self.lib,self.catalog);self.assertEqual(build(self.lib,self.catalog)['generation'],new['generation'])
        self.assertEqual(lint(self.lib,self.catalog)['images']['missing'],self.active_count)

    def test_wiki_entry_and_local_source_links(self):
        wiki=self.lib/WIKI_DIR
        self.assertEqual(Path(self.result['index']),(wiki/'index.html').resolve())
        generation=current(self.lib,self.catalog,verify=True)
        self.assertIn(f'generations/{generation.name}/index.html',(wiki/'index.html').read_text())
        row=search(self.catalog,'四年技术路线图',require={'duration_years':'4'})[0]
        card=Path(row['knowledge_page'])
        self.assertEqual(card.parent.parent,generation.resolve())
        self.assertIn('href="../../../../images/ref-008.png"',card.read_text())
        (wiki/'index.html').write_text('stale')
        with self.assertRaisesRegex(ValueError,'wiki entry is stale'):lint(self.lib,self.catalog)
        build(self.lib,self.catalog)
        self.assertEqual(lint(self.lib,self.catalog)['status'],'ok')

    def test_schema_sources_and_human_protection(self):
        rows=records(self.catalog);a=read(next((self.lib/'analyses').glob('*.json')));r=rows[a['reference_id']]
        bad=copy.deepcopy(a);bad['regions'][1]['bounds']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError):validate_analysis(bad,r,taxonomy(self.lib))
        bad=copy.deepcopy(a);bad['regions'][0]['parent_id']='focus'
        with self.assertRaisesRegex(ValueError,'cyclic'):validate_analysis(bad,r,taxonomy(self.lib))
        bad=copy.deepcopy(a);bad['observations'][0]['region_ids']=['missing']
        with self.assertRaises(ValueError):validate_analysis(bad,r,taxonomy(self.lib))
        edited=copy.deepcopy(a);edited['title']+='修订'
        doc={'reviewer':'test','reviewer_kind':'model','records':[{'analysis':edited,'expected_previous_hash':'wrong'}]}
        with self.assertRaisesRegex(ValueError,'stale'):ingest_analyses(self.lib,self.catalog,doc)
        doc['records'][0]['expected_previous_hash']=fingerprint(a);ingest_analyses(self.lib,self.catalog,doc)
        self.assertEqual(ingest_analyses(self.lib,self.catalog,doc)['applied'],0)
        human=copy.deepcopy(edited);human['review_status']='human_approved'
        doc={'reviewer':'test fixture only','reviewer_kind':'human','attestation':'synthetic fixture','records':[{'analysis':human,'expected_previous_hash':fingerprint(edited)}]}
        ingest_analyses(self.lib,self.catalog,doc)
        doc['reviewer_kind']='model';doc['records']=[{'analysis':edited,'expected_previous_hash':fingerprint(human)}]
        with self.assertRaisesRegex(ValueError,'cannot replace'):ingest_analyses(self.lib,self.catalog,doc)
        patterns=read(self.lib/'patterns.json');patterns[0]['sources'][0]['region_id']='missing';write(self.lib/'patterns.json',patterns)
        with self.assertRaisesRegex(ValueError,'dangling'):build(self.lib,self.catalog)

    def test_image_alias_missing_modified_and_legacy_catalog(self):
        from PIL import Image
        images=self.root/'images';images.mkdir();Image.new('RGB',(12,20),'red').save(images/'a.png')
        catalog=self.root/'legacy.sqlite';index(images,catalog)
        row=search(catalog)[0];self.assertEqual(resolve_images([row],images)[0]['image_status'],'verified')
        shutil.copyfile(images/'a.png',images/'alias.png');row['paths']=['a.png','alias.png']
        (images/'a.png').write_bytes(b'modified')
        self.assertTrue(resolve_images([row],images)[0]['image_path'].endswith('alias.png'))
        (images/'alias.png').unlink();self.assertEqual(resolve_images([row],images)[0]['image_status'],'modified')
        (images/'a.png').unlink();self.assertEqual(resolve_images([row],images)[0]['image_status'],'missing')
        self.assertEqual(len(search(catalog)),1)

    def test_suggestions_do_not_change_science(self):
        from cases import make_case
        from figure_retrieval import suggest
        from figure_plan import candidates,reference_choices
        c,s=make_case(self.root/'case');original=copy.deepcopy(c)
        suggestions=suggest(self.catalog,c,'图文混合生物医药')
        plans=candidates(c,references=suggestions)
        self.assertLessEqual(len(plans),2);self.assertEqual(c,original)
        self.assertTrue(all(not p['reference_review'] for p in plans))
        ref=suggestions['candidates'][0]
        choice={'id':ref['id'],'region_id':'focus','basis':'knowledge','use':'Separate the shared validation panel'}
        brief={'source_content_hash':fingerprint(c),'design_decisions':{'reference_choices_with_reasons':[choice]}}
        reviewed=reference_choices(c,suggestions,brief)
        plans=candidates(c,references=suggestions,reviewed=reviewed)
        self.assertTrue(all(p['reference_review'][ref['id']]['use']==choice['use'] for p in plans))
        choice['region_id']='nonexistent'
        with self.assertRaisesRegex(ValueError,'valid region'):reference_choices(c,suggestions,brief)
        c['labels'][0]['text']+='变更'
        with self.assertRaisesRegex(ValueError,'stale'):candidates(c,references=suggestions)
        with self.assertRaises(ValueError):save_feedback({},self.lib/'feedback.json',self.lib)
