"""Artificial input fixtures check logic; none are actual simulator measurements."""
import copy
import math
import unittest
import tempfile
from pathlib import Path
from ftqc_resource_estimator.memory_analysis import (MemoryScenario, MemoryWorkload, validate_stim_manifest, write_comparison,
                    compare_memory, nondominated)
from ftqc_resource_estimator.stim_memory import SCHEMA, NOISE_PROFILE, EXPERIMENT, DECODER


def synthetic_fixture():
    return {
        'schema': SCHEMA,'generator':'ftqc_resource_estimator.stim_memory',
        'software':{'stim':'TEST-FAKE','pymatching':'TEST-FAKE','numpy':'TEST-FAKE','python':'TEST-FAKE'},
        'methods':{'experiment':EXPERIMENT,'basis':'X','noise_profile':NOISE_PROFILE,'decoder':DECODER,
           'rounds':9,'rounds_rule':'fixed number of syndrome rounds across all distances; no interpolation',
           'seed_rule':'seed_base + enumeration index; RNG streams may differ across platforms',
           'noise_knobs':['after_clifford_depolarization','before_round_data_depolarization',
                           'before_measure_flip_probability','after_reset_flip_probability']},
        'observations': [dict(code_family='rotated_surface',experiment=EXPERIMENT,
              observable_basis='X',physical_error=.003,distance=d,rounds=9,shots=10000,
              failures=n,trivial_decoder_failures=100,seed=100+d,noise_profile=NOISE_PROFILE,decoder=DECODER,observables=1,
              detectors=10,circuit_sha256='a'*64,detector_model_sha256='b'*64,
              batch_single_agreement_checked_shots=16) for d,n in [(3,70),(5,15),(7,2)]]
    }

class MatchingAndAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.obj=synthetic_fixture()
    def test_exact_experiment_and_distance(self):
        self.assertEqual(set(validate_stim_manifest(self.obj,physical_error=.003,rounds=9,distances=(3,5,7))),{3,5,7})
        with self.assertRaisesRegex(ValueError,'missing EXACT'):
            validate_stim_manifest(self.obj,physical_error=.003,rounds=9,distances=(3,5,9))
        with self.assertRaisesRegex(ValueError,'missing EXACT'):
            validate_stim_manifest(self.obj,physical_error=.005,rounds=9,distances=(3,))
    def test_refuses_memory_data_used_as_logical_gate(self):
        broken=copy.deepcopy(self.obj)
        broken['observations'][0]['experiment']='logical_layer'
        with self.assertRaisesRegex(ValueError,'not match'):
            validate_stim_manifest(broken,physical_error=.003,rounds=9,distances=(3,5,7))
    def test_refuses_mismatched_syndrome_rounds(self):
        broken=copy.deepcopy(self.obj)
        broken['observations'][0]['rounds']=8
        with self.assertRaises(ValueError):validate_stim_manifest(broken,physical_error=.003,rounds=9,distances=(3,))
    def test_refuses_duplicate_or_missing_decoder_and_noise(self):
        dup=copy.deepcopy(self.obj)
        dup['observations'].append(dup['observations'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):
            validate_stim_manifest(dup,physical_error=.003,rounds=9,distances=(3,))
        for key in ('noise_profile','decoder'):
            bad=copy.deepcopy(self.obj)
            bad['observations'][0][key]='not_matched'
            with self.assertRaises(ValueError):validate_stim_manifest(bad,physical_error=.003,rounds=9,distances=(3,))
    def test_refuses_noiseless_observation_with_failures(self):
        fake=copy.deepcopy(self.obj)
        fake['observations'][0]['physical_error']=0
        with self.assertRaises(ValueError):validate_stim_manifest(fake,physical_error=0,rounds=9,distances=(3,))
    def test_costs_and_uncertainty(self):
        scenarios=[MemoryScenario('fast',.5,1,0),MemoryScenario('slow',1.0,3,.1)]
        work=MemoryWorkload(2,10,.5)
        rows=compare_memory(self.obj,scenarios,work,basis='X',physical_error=.003,rounds=9,distances=(3,5,7))
        self.assertEqual(len(rows),6)
        fast3=rows[0]; slow3=rows[1]
        self.assertEqual(fast3['patch_site_equivalents'],2*(2*3*3-1))
        self.assertAlmostEqual(fast3['storage_runtime_us'],10*(9*.5+1))
        self.assertGreater(slow3['total_site_equivalents'],fast3['total_site_equivalents'])
        self.assertGreater(slow3['storage_runtime_us'],fast3['storage_runtime_us'])
        self.assertGreater(fast3['logical_error_upper95'],fast3['logical_error_per_memory_window'])
        self.assertAlmostEqual(fast3['workload_failure_mean'],1-(1-70/10000)**(2*10))
        self.assertFalse(any(math.isnan(x['workload_failure_upper95']) for x in rows))
        self.assertTrue(all(r['architecture']=='fast' for r in nondominated(rows)))
    def test_zero_failures_still_has_upper_bound(self):
        fake=copy.deepcopy(self.obj)
        fake['observations'][0]['failures']=0
        rows=compare_memory(fake,[MemoryScenario('one',1,1,0)],MemoryWorkload(1,1,.001),
                            basis='X',physical_error=.003,rounds=9,distances=(3,))
        self.assertEqual(rows[0]['logical_error_per_memory_window'],0)
        self.assertGreater(rows[0]['logical_error_upper95'],0)
    def test_writes_analysis_csv_and_report_from_explicit_synthetic_fixture(self):
        # Files live only in a temporary TEST directory; never publish as observed results.
        scenario=MemoryScenario('test_case',.5,0.2,0)
        workload=MemoryWorkload(1,3,.5)
        rows=compare_memory(self.obj,[scenario],workload,basis='X',physical_error=.003,
                            rounds=9,distances=(3,5))
        with tempfile.TemporaryDirectory() as td:
            write_comparison(rows,self.obj,workload,Path(td),basis='X',p=.003,rounds=9)
            csv_file=Path(td)/'memory_tradeoffs.csv'
            report=Path(td)/'MEMORY_REPORT.md'
            self.assertTrue(csv_file.is_file())
            self.assertIn('logical_error_per_memory_window',csv_file.read_text())
            self.assertIn('9-round',report.read_text())
            self.assertIn('trivial fail/shots',report.read_text())

    def test_reject_bad_scenarios(self):
        with self.assertRaises(ValueError):MemoryScenario('bad',0,1,0)
        with self.assertRaises(ValueError):MemoryWorkload(1,0,.1)

if __name__=='__main__':unittest.main()
