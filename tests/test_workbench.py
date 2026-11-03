import json
from pathlib import Path
import shutil
import tempfile
import unittest

from simcheck.workbench import parse_table, run_campaign, run_spice
from simcheck.studies import inverter, latch, xor_gate


class TableParsing(unittest.TestCase):
    def test_nonfinite_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result.tsv';p.write_text('time v(out)\n0 nan\n')
            with self.assertRaises(RuntimeError):parse_table(p)

    def test_malformed_columns_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result.tsv';p.write_text('time v(out)\n0 1 2\n')
            with self.assertRaises(RuntimeError):parse_table(p)


@unittest.skipUnless(shutil.which('ngspice'),'ngspice is required for the workbench integration checks')
class SimulatorIntegration(unittest.TestCase):
    def config(self,root):
        (root/'inverter.cir').write_text(inverter())
        config={'netlist':'inverter.cir','analysis':['op'],'vectors':['v(out)'],
                'points':[{'id':'low','commands':['alter VIN dc=0']},
                          {'id':'high','commands':['alter VIN dc=1.8']}]}
        path=root/'campaign.json';path.write_text(json.dumps(config));return path,config

    def test_campaign_resume_skips_verified_completed_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,_=self.config(root)
            first=run_campaign(path,root/'run',workers=2)
            second=run_campaign(path,root/'run',resume=True)
            self.assertEqual(first['passed'],2);self.assertEqual(second['executed_this_invocation'],0)

    def test_resume_rejects_changed_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,config=self.config(root)
            run_campaign(path,root/'run');config['analysis']=['dc VIN 0 1.8 .1'];path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):run_campaign(path,root/'run',resume=True)

    def test_resume_rejects_changed_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path,_=self.config(root);run_campaign(path,root/'run')
            (root/'run/points/low/result.tsv').write_text('corrupted')
            with self.assertRaises(ValueError):run_campaign(path,root/'run',resume=True)

    def test_unloaded_truth_table_can_hide_loaded_failure(self):
        bare=run_spice(xor_gate(),['alter VA dc=1.8','alter VB dc=0','op'],['v(out)'])
        loaded=run_spice(xor_gate(10000),['alter VA dc=1.8','alter VB dc=0','op'],['v(out)'])
        self.assertGreater(bare['vectors']['v(out)'][0],1.26)
        self.assertLess(loaded['vectors']['v(out)'][0],1.26)

    def test_input_terminal_supplies_loaded_output_current(self):
        r=run_spice(xor_gate(10000),['alter VA dc=0','alter VB dc=1.8','op'],['v(out)','i(VB)'])
        v=r['vectors'];self.assertAlmostEqual(-v['i(VB)'][0],v['v(out)'][0]/10000,delta=1e-10)

    def test_latch_has_distinct_operating_points(self):
        low=run_spice(latch().replace('.end','.nodeset v(q)=0 v(qb)=1.8\n.end'),['op'],['v(q)'])
        high=run_spice(latch().replace('.end','.nodeset v(q)=1.8 v(qb)=0\n.end'),['op'],['v(q)'])
        self.assertGreater(high['vectors']['v(q)'][0]-low['vectors']['v(q)'][0],1.7)
