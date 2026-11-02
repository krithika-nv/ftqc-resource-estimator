import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
from ftqc_resource_estimator.hardware_profiles import (
    ReferenceWorkload,PhotonicScenario,SuperconductingScenario,TrappedIonScenario,from_record)
from ftqc_resource_estimator.hardware_study import run

W=ReferenceWorkload(distance=5,logical_qubits=2,syndrome_rounds_per_window=3,memory_windows=4)
P=PhotonicScenario('optical',2,10,.5,(.8,.9),2.0,.5,.5)
S=SuperconductingScenario('sc',.025,.20,.5,1.0,2,4)
I=TrappedIonScenario('ion',10,8,40,10,4,2,2,2)

class ProfilesTests(unittest.TestCase):
    def test_workload_validation(self):
        for kw in ({'distance':4},{'logical_qubits':0},{'memory_windows':0}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):replace(W,**kw)
        self.assertEqual(W.surface_patch_sites,2*(2*5*5-1))
    def test_photonic_supply_improves_with_more_sources(self):
        slow=P.evaluate(W);fast=replace(P,sources=4).evaluate(W)
        self.assertAlmostEqual(slow['delivery_probability'],.5*.8*.9)
        self.assertAlmostEqual(slow['supply_us']/2,fast['supply_us'])
        self.assertEqual(slow['resource_unit'],'heralded_resource_state_equivalent')
    def test_photonic_loss_makes_delivery_worse(self):
        base=P.evaluate(W);worse=replace(P,path_transmission=(.8,.6)).evaluate(W)
        self.assertLess(worse['delivery_probability'],base['delivery_probability'])
        self.assertGreater(worse['expected_attempts'],base['expected_attempts'])
    def test_photonic_latency_floor(self):
        abundant=replace(P,sources=1000).evaluate(W)
        self.assertAlmostEqual(abundant['runtime_us'],W.total_rounds*(P.measurement_us_per_round+P.feedforward_us_per_round))
    def test_superconducting_readout_sensitivity(self):
        base=S.evaluate(W);slow=replace(S,readout_reset_us=1.5).evaluate(W)
        self.assertAlmostEqual(slow['runtime_us']-base['runtime_us'],W.total_rounds)
        self.assertEqual(base['nominal_patch_qubits'],W.surface_patch_sites)
    def test_superconducting_routing_penalty(self):
        base=S.evaluate(W);routed=replace(S,extra_routing_layers_per_round=3).evaluate(W)
        self.assertAlmostEqual(routed['runtime_us']-base['runtime_us'],W.total_rounds*3*S.two_qubit_us)
    def test_ions_parallel_gates_reduce_runtime(self):
        base=I.evaluate(W);parallel=replace(I,parallel_gate_zones=4).evaluate(W)
        self.assertLess(parallel['runtime_us'],base['runtime_us'])
        self.assertEqual(base['nominal_patch_ions'],W.surface_patch_sites)
    def test_ions_parallel_transport(self):
        base=I.evaluate(W);parallel=replace(I,parallel_transport_zones=4).evaluate(W)
        self.assertLessEqual(parallel['runtime_us'],base['runtime_us'])
    def test_ions_no_zero_parallelism(self):
        with self.assertRaises(ValueError):replace(I,parallel_gate_zones=0)
    def test_invalid_physical_inputs_rejected(self):
        with self.assertRaises(ValueError):replace(P,heralding_success=1.1)
        with self.assertRaises(ValueError):replace(P,path_transmission=(.8,0))
        with self.assertRaises(ValueError):replace(S,one_qubit_us=-1)
        with self.assertRaises(ValueError):replace(I,gates_per_patch_round=0)
    def test_strict_platform_parser(self):
        self.assertIsInstance(from_record(dict(profile='photonic',name='x',sources=2,source_attempts_per_us=10,heralding_success=.5,path_transmission=[.8,.9],state_equivalents_per_patch_round=2,measurement_us_per_round=.5,feedforward_us_per_round=.5)),PhotonicScenario)
        with self.assertRaises(ValueError):from_record(dict(profile='unrecognized',name='x'))
        with self.assertRaises(TypeError):from_record(dict(profile='photonic',name='x',unknown_parameter=7))
    def test_repeatable_scenario_outputs(self):
        settings=Path(__file__).resolve().parents[1]/'examples/hardware_profiles.json'
        with tempfile.TemporaryDirectory() as tmp:
            rows=run(settings,Path(tmp))
            self.assertEqual(len(rows),6)
            self.assertTrue((Path(tmp)/'photonic_scenarios.csv').exists())
            self.assertTrue((Path(tmp)/'superconducting_scenarios.csv').exists())
            self.assertTrue((Path(tmp)/'trapped_ion_scenarios.csv').exists())
            report=(Path(tmp)/'HARDWARE_STUDY.md').read_text()
            self.assertIn('NOT a scientific ranking',report)
            self.assertNotIn('photonic platform is better',report)
            self.assertEqual(json.loads(settings.read_text())['reference_workload']['distance'],5)

if __name__ == '__main__':unittest.main()
