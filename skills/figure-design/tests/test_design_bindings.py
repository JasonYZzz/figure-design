from pathlib import Path
import sys
import tempfile
import unittest
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from cases import make_case
from figure_assets import resolve
from figure_common import read
from figure_data import chart
from figure_design_checks import bind_design, comparison_assets, review_design
from figure_plan import candidates, make_plan


class MixedDesignTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.content, _ = make_case(self.root)
        self.content['sources'][1]['excerpt'] = 'The reported change in gain was −0.234 vs 0.000 in a matched subset.'
        self.display = {'owner_id':'T4','display':'horizontal-bar','asset_id':'results',
                        'metric':'增益变化','unit':'分','value_kind':'delta','baseline':'不加规则',
                        'scope':'配对子集','rows':[{'category':'条件甲','value':-0.234,'source_id':'S1'},
                                                {'category':'条件乙','value':0,'source_id':'S1'}]}
        self.path = {'input':'T1','intermediate':'T2','output':'T3','relation_ids':['R1','R2'],'source_ids':['S1']}
        self.decisions = {'hero_owner_id':'T2','main_paths':[self.path],
                          'visual_concept':{'evidence_displays':[self.display]}}
        self.plan = make_plan(self.content,'top-overview-multi-lane','cs-academic',decisions=self.decisions)
        bind_design(self.plan,self.content,self.decisions)

    def test_paths_and_hero_change_final_regions(self):
        alternate = dict(self.decisions, hero_owner_id='T3')
        one, two = [candidates(self.content, decisions=d)[0]['plan'] for d in (self.decisions,alternate)]
        self.assertEqual(next(r['id'] for r in one['regions'] if r['role']=='hero'),'owner-2')
        self.assertEqual(next(r['id'] for r in two['regions'] if r['role']=='hero'),'owner-3')
        direct = deepcopy(self.decisions)
        direct['main_paths'] = [dict(self.path, intermediate='T3')]
        other = candidates(self.content, decisions=direct)[0]['plan']
        self.assertNotEqual([r['bounds'] for r in one['regions']], [r['bounds'] for r in other['regions']])
        preferred = dict(self.decisions, reference_design={'placements':{}})
        self.assertNotEqual(candidates(self.content,decisions=preferred)[0]['plan']['regions'],one['regions'])

    def test_bound_marks_sources_and_missing_regions(self):
        with comparison_assets(self.plan,self.content,[]) as paths:
            asset = resolve(paths,self.content)
            svg = asset['results']['_path'].read_text()
            for token in ('变化量','不加规则','-0.234','配对子集'):
                self.assertIn(token, svg)
            report = review_design(self.plan,self.content,asset)
            self.assertEqual(report['paths'][0]['owners'],['T1','T2','T3'])
            self.plan['edges'].pop(0)
            with self.assertRaisesRegex(ValueError,'missing drawn relation'):
                review_design(self.plan,self.content,asset)
        self.display['rows'][0]['value']=0.234
        with self.assertRaisesRegex(ValueError,'absent in source'):
            with comparison_assets(self.plan,self.content,[]):pass

    def test_trace_gaps_and_missing_asset(self):
        trace = {'owner_id':'T2','label_instances':{'before':'I2'}}
        self.plan['design_bindings']['traces'] = [trace]
        with self.assertRaisesRegex(ValueError,'missing declared comparison'):
            review_design(self.plan,self.content,{})
        self.plan['design_bindings']['displays']=[]
        result = review_design(self.plan,self.content,{})
        self.assertEqual(result['traces'][0]['missing'],['basis','after','next_action'])
        self.assertEqual(result['traces'][0]['visible_text']['before'], self.content['labels'][2]['text'])
        # A shared region can contain another owner's caption.
        region = next(r for r in self.plan['regions'] if 'I2' in r['label_instance_ids'])
        region['label_instance_ids'].append('I3')
        trace['label_instances']['after'] = 'I3'
        self.assertIn('after',review_design(self.plan,self.content,{})['traces'][0]['missing'])

    def test_csv_pair_conditions_units_and_zero(self):
        csv = self.root/'test.csv'
        opts = dict(condition='condition',unit='ms',baseline='A',scope='same cohort')
        csv.write_text('name,condition,value,unit\nx,A,0,ms\nx,B,-3,ms\ny,A,4,ms\ny,B,1,ms\n')
        result = chart(csv,self.root/'plot','name','value','latency','paired-dot',**opts)
        self.assertEqual(len(result['rows']),4)
        self.assertEqual(read(self.root/'plot/data-provenance.json')['baseline'],'A')
        csv.write_text(csv.read_text().replace('y,B,1,ms','y,B,1,s'))
        with self.assertRaisesRegex(ValueError,'mixed units'):
            chart(csv,self.root/'bad','name','value','latency','paired-dot',**opts)
        csv.write_text(csv.read_text().replace('y,B,1,s',''))
        with self.assertRaisesRegex(ValueError,'two named conditions'):
            chart(csv,self.root/'bad','name','value','latency','paired-dot',**opts)
