"""Pure-Python validation tests use EXPLICIT FIXTURES, never claimed Stim measurements."""
import copy
import tempfile
import unittest
from pathlib import Path
from ftqc_resource_estimator import literature_benchmark as b


def fixture():
    rows=[]
    for i,(p,d) in enumerate((p,d) for p in b.DEFAULT_ERRORS for d in b.DEFAULT_DISTANCES):
        rows.append(dict(distance=d,rounds=d,observable_basis='X',code_family='rotated_surface',experiment='memory_distance_scaled_rounds',
                         physical_error=p,noise_profile=b.NOISE_PROFILE,shots=20000,
                         failures=0 if p==0 else 100,decoder=b.DECODER if p>0 else 'noiseless_identity_control',
                         observables=1,detectors=d,seed=20261028+i,circuit_sha256='fixture',
                         detector_model_sha256='fixture',trivial_decoder_failures=0,
                         batch_single_agreement_checked_shots=16 if p>0 else 0))
    return {'schema':b.SCHEMA,'software':{'stim':'FAKE','pymatching':'FAKE'},
            'protocol':{'reference_url':b.REFERENCE,'code':'surface_code:rotated_memory_x',
            'rounds_rule':'rounds=distance','noise_profile':b.NOISE_PROFILE,
            'decoder':b.DECODER,'noise_knobs':['after_clifford_depolarization',
            'before_round_data_depolarization','before_measure_flip_probability',
            'after_reset_flip_probability'],'distances':list(b.DEFAULT_DISTANCES),
            'physical_errors':list(b.DEFAULT_ERRORS),'shots_per_point':20000,'seed_base':20261028},
            'observations':rows}

class LiteratureBenchTests(unittest.TestCase):
    def test_fixture_protocol_is_valid(self):self.assertEqual(len(b.validate_benchmark(fixture())),20)
    def test_requires_all_twenty_points(self):
        x=fixture();x['observations'].pop()
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_rejects_wrong_rounds(self):
        x=fixture();x['observations'][1]['rounds']=9
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_rejects_wrong_noise_knobs(self):
        x=fixture();x['protocol']['noise_knobs'].pop()
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_rejects_wrong_seeded_decoder_controls(self):
        x=fixture();x['observations'][4]['batch_single_agreement_checked_shots']=0
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_zero_noise_cannot_fail(self):
        x=fixture();x['observations'][0]['failures']=1
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_rejects_wrong_shots(self):
        x=fixture();x['observations'][3]['shots']=19999
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_report_from_explicit_fixture_not_a_real_result(self):
        x=fixture()
        with tempfile.TemporaryDirectory() as t:
            b.report_benchmark(x,Path(t))
            self.assertIn('protocol-matched subset',(Path(t)/'LITERATURE_COMPARISON.md').read_text())
            self.assertEqual(len((Path(t)/'round_scaled_results.csv').read_text().splitlines()),21)
    def test_rejects_changed_seed(self):
        x=fixture();x['observations'][3]['seed']+=1
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_rejects_fixed_rounds_experiment_label(self):
        x=fixture();x['observations'][3]['experiment']='memory_fixed_rounds'
        with self.assertRaises(ValueError):b.validate_benchmark(x)
    def test_pairwise_diagnostics_are_cautious(self):
        self.assertEqual(len(b.crossover_diagnostics(fixture()['observations'])),4)
