"""Math, source provenance and fail-closed generator-layout tests.

Does not replace the integration tests requiring *real* Stim and PyMatching.
"""
import csv
import json
import math
from pathlib import Path
import tempfile
import unittest

from ftqc_resource_estimator.idle_coherence import (
    BASE_NOISE, CoherenceParameters, DEFAULT_DISTANCES, EXPECTED_SCENARIOS,
    SchedulingHypothesis, _insert_idle_after_round_start, load_hypotheses,
    scenario_schedule, save_parameter_preview, twirled_idle_paulis, validate_manifest,
    analyze_rows, build_idle_circuit)

CONFIG=Path('examples/idle_coherence_study.json')

class CoherenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coh,cls.ctrl,cls.patches,cls.windows,cls.target=load_hypotheses(CONFIG)

    def test_referenced_inputs_are_locked(self):
        self.assertEqual(self.coh.t1_us,68)
        self.assertEqual(self.coh.t2_proxy_us,89)
        self.assertEqual(self.coh.published_cycle_us,1.1)
        self.assertEqual(tuple(c.name for c in self.ctrl),EXPECTED_SCENARIOS)

    def test_zero_idle_identity_channel(self):
        self.assertEqual(twirled_idle_paulis(0,self.coh),(0,0,0))

    def test_pauli_channel_probabilities(self):
        px,py,pz=twirled_idle_paulis(1.0,self.coh)
        a=math.exp(-1/68);b=math.exp(-1/89)
        self.assertAlmostEqual(px,(1-a)/4)
        self.assertAlmostEqual(py,px)
        self.assertAlmostEqual(pz,(1+a-2*b)/4)
        self.assertTrue(0<px+py+pz<1)

    def test_no_dephasing_limit(self):
        # For T2=2*T1, pure dephasing rate vanishes; amplitude damping
        # still produces (tiny) Z component under a Pauli twirl.
        c=CoherenceParameters(t1_us=68,t2_proxy_us=136)
        x,y,z=twirled_idle_paulis(.7,c)
        self.assertGreaterEqual(z,0)
        self.assertLess(z,x)

    def test_reject_invalid_coherence_and_durations(self):
        with self.assertRaises(ValueError):CoherenceParameters(t1_us=1,t2_proxy_us=3)
        for time in (-.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):twirled_idle_paulis(time,self.coh)

    def test_registered_readout_batches(self):
        wide=scenario_schedule(9,self.ctrl[0],self.coh,4)
        mid=scenario_schedule(9,self.ctrl[1],self.coh,4)
        small=scenario_schedule(9,self.ctrl[2],self.coh,4)
        self.assertEqual([x['batches_per_round'] for x in (wide,mid,small)],[2,3,10])
        self.assertAlmostEqual(wide['extra_data_idle_per_round_us'],0)
        self.assertAlmostEqual(mid['extra_data_idle_per_round_us'],.25)
        self.assertAlmostEqual(small['extra_data_idle_per_round_us'],3.4)
        self.assertEqual(wide['patch_physical_qubits'],4*(2*81-1))

    def test_schedule_rejects_bad_distance(self):
        with self.assertRaises(ValueError):scenario_schedule(4,self.ctrl[0],self.coh)

    def test_repeat_injection_preserves_textual_detectors(self):
        base='QUBIT_COORDS(1, 1) 1\nRX 1 3 5\nTICK\nH 2\nMR 2\nDETECTOR rec[-1]\nREPEAT 2 {\n    TICK\n    H 2\n    MR 2\n    DETECTOR rec[-1] rec[-2]\n}\nMX 1 3 5\nOBSERVABLE_INCLUDE(0) rec[-1]\n'
        res=_insert_idle_after_round_start(base,[1,3,5],(.001,.001,.002),3)
        self.assertEqual(res.count('PAULI_CHANNEL_1('),2)
        self.assertEqual(res.count('DETECTOR'),2)
        self.assertIn('REPEAT 2 {\n    TICK\n    PAULI_CHANNEL_1(',res)
        self.assertIn('RX 1 3 5\nTICK\nPAULI_CHANNEL_1(',res)
        self.assertEqual(res.count('OBSERVABLE_INCLUDE'),1)

    def test_reject_unknown_generated_repeat_layout(self):
        with self.assertRaises(RuntimeError):
            _insert_idle_after_round_start('RX 1\nTICK\nREPEAT 3 {\nTICK\n}\n',[1],(.001,.001,.001),3)
        with self.assertRaises(RuntimeError):
            _insert_idle_after_round_start('RX 1\nTICK\n',[1],(.001,.001,.001),4)

    def test_default_no_extra_noise_returns_unmodified_baseline(self):
        class Fake:
            class Circuit:
                @staticmethod
                def generated(*args,**kwargs):return 'ORIGINAL'
        c=build_idle_circuit(Fake,distance=3,rounds=3,base_p=.003,
            schedule={'idle_pauli_x':0,'idle_pauli_y':0,'idle_pauli_z':0})
        self.assertEqual(c,'ORIGINAL')

    def test_fake_manifest_math_and_feasibility(self):
        rows=[]
        for i,(d,c) in enumerate((d,c) for d in DEFAULT_DISTANCES for c in self.ctrl):
            row=scenario_schedule(d,c,self.coh,self.patches)
            row.update(physical_error=.003,shots=20000,failures=10,seed=20261029+i,
                       circuit_sha256='ab',detector_model_sha256='cd',num_detectors=8,
                       num_observables=1,decoder='pymatching_mwpm_from_full_modified_circuit_dem')
            rows.append(row)
        manifest={'schema':'ftqc.controller_idle_coherence.v1',
            'source_doi':self.coh.reference,
            'coherence':self.coh.__dict__,
            'protocol':{'shots_per_case':20000,'seed_base':20261029,'physical_error':BASE_NOISE,
                        'rounds_rule':'rounds=distance','patches':self.patches,
                        'windows':self.windows,'target_total_failure':self.target},
            'observations':rows}
        self.assertEqual(len(validate_manifest(manifest,self.coh,self.ctrl,self.patches,self.windows,self.target)),12)
        derived=analyze_rows(manifest,self.coh,self.ctrl,self.patches,self.windows,self.target)
        self.assertTrue(all(r['conservatively_feasible'] for r in derived))
        self.assertTrue(all(r['wilson_upper95']>0 for r in derived))
        bad=json.loads(json.dumps(manifest))
        bad['observations'][0]['idle_pauli_x']+=.01
        with self.assertRaisesRegex(ValueError,'altered'):
            validate_manifest(bad,self.coh,self.ctrl,self.patches,self.windows,self.target)
        bad=json.loads(json.dumps(manifest))
        bad['observations'][0]['failures']=20001
        with self.assertRaises(ValueError):validate_manifest(bad,self.coh,self.ctrl,self.patches,self.windows,self.target)

    def test_preview_not_fake_results(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)
            save_parameter_preview(path,CONFIG)
            csvpath=path/'idle_channel_inputs_ONLY.csv'
            self.assertTrue(csvpath.is_file())
            self.assertFalse((path/'observations.json').exists())
            self.assertNotIn('conservatively_feasible',csvpath.read_text())
            self.assertIn('NOT a decoded QEC result',(path/'README_INPUTS_ONLY.md').read_text())
            self.assertEqual(len(list(csv.DictReader(csvpath.read_text().splitlines()))),12)

if __name__=='__main__':unittest.main()
