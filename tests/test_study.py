import tempfile
import unittest
from pathlib import Path
from ftqc_resource_estimator.study import load_configuration, sensitivity,main

ROOT=Path(__file__).resolve().parents[1]
class StudyTests(unittest.TestCase):
    def test_configuration_and_sensitivity(self):
        w,designs,dist=load_configuration(ROOT/'examples/architecture_scenarios.json')
        self.assertEqual(len(designs),3)
        self.assertEqual(len(dist),7)
        r=sensitivity(designs[0],w,11,[.6,.8,.99])
        self.assertGreater(r[0]['supply_us'],r[-1]['supply_us'])
        self.assertTrue(all(row['distance']==11 for row in r))

    def test_study_generates_outputs(self):
        with tempfile.TemporaryDirectory() as path:
            out=Path(path)
            rc=main(['--config',str(ROOT/'examples/architecture_scenarios.json'),'--output-dir',str(out)])
            self.assertEqual(rc,0)
            self.assertIn('fast_control_supply_limited',(out/'distance_sweep.csv').read_text())
            self.assertIn('not an estimation of Xanadu hardware',(out/'ARCHITECTURE_REPORT.md').read_text())
            self.assertTrue((out/'transmission_sensitivity.csv').is_file())

class AdditionalSensitivityTests(unittest.TestCase):
    def test_factory_sweep_reduces_supply_time_at_site_cost(self):
        from ftqc_resource_estimator.study import factory_sweep
        w,ds,_=load_configuration(ROOT/'examples/architecture_scenarios.json')
        r=factory_sweep(ds[0],w,11,[1,2,4])
        self.assertGreater(r[0]['supply_us'],r[2]['supply_us'])
        self.assertLess(r[0]['total_site_equivalents'],r[2]['total_site_equivalents'])

    def test_reliability_sensitivity_requires_distance_as_noise_grows(self):
        from ftqc_resource_estimator.study import reliability_sweep
        w,ds,d=load_configuration(ROOT/'examples/architecture_scenarios.json')
        r=reliability_sweep(ds[0],w,d,[.0005,.001,.0015,.002])
        self.assertTrue(all(i['chosen_distance']!='none' for i in r[:3]))
        self.assertLessEqual(r[0]['chosen_distance'],r[1]['chosen_distance'])
        self.assertLessEqual(r[1]['chosen_distance'],r[2]['chosen_distance'])
        self.assertEqual(r[3]['chosen_distance'],'none')
