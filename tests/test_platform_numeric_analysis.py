"""Controlled fixtures only: never described as downloaded experimental measurements."""
from __future__ import annotations
import csv, json, math, os, subprocess, sys, tempfile, unittest
from pathlib import Path

from ftqc_resource_estimator.evidence_analysis import wilson
from ftqc_resource_estimator.quera_analysis import estimate_two_copy_kernel
from ftqc_resource_estimator.quantinuum_analysis import analyze_benchmark_csv
from ftqc_resource_estimator.ibm_hardware_analysis import compare_from_verified_flat_table,independent_majority_error
from ftqc_resource_estimator.neutral_atom_schedule import schedule


def csvfile(path,cols,rows):
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(cols);w.writerows(rows)
    return path

class PlatformAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)

    def test_wilson_zero_success_not_zero_certainty(self):
        a,b=wilson(0,100);self.assertEqual(a,0);self.assertGreater(b,0)
    def test_wilson_reject(self):
        with self.assertRaises(ValueError):wilson(11,10)

    def test_quera_ensemble_one_qubit_pure_state(self):
        # Z measurement deterministic 0, X and Y uniform; 3 Pauli bases form qubit local 2-design
        path=csvfile(self.p/'q.csv',['randomization_id','bitstring','count'],
            [('Z','0',10000),('X','0',5000),('X','1',5000),('Y','0',5000),('Y','1',5000)])
        r=estimate_two_copy_kernel(path)
        self.assertAlmostEqual(r['mean_kernel'],1,places=3)
        self.assertFalse(r['entanglement_measurement_claim_authorized'])
    def test_quera_mismatched_bits_reject(self):
        path=csvfile(self.p/'bad.csv',['randomization_id','bitstring','count'],[('z','0',2),('x','01',2)])
        with self.assertRaises(ValueError):estimate_two_copy_kernel(path)
    def test_quera_one_shot_reject(self):
        path=csvfile(self.p/'one.csv',['randomization_id','bitstring','count'],[('z','0',1)])
        with self.assertRaises(ValueError):estimate_two_copy_kernel(path)
    def test_quera_reject_bad_count(self):
        path=csvfile(self.p/'neg.csv',['randomization_id','bitstring','count'],[('z','0','-4')])
        with self.assertRaises(ValueError):estimate_two_copy_kernel(path)

    def test_ion_benchmark_wilson(self):
        path=csvfile(self.p/'h.csv',['source_id','processor','experiment','successes','shots','data_kind','provider'],
            [('paper-1','Helios','gate_test',95,100,'executed_hardware_shots','Quantinuum'),
             ('paper-1','Helios','gate_test',90,100,'executed_hardware_shots','Quantinuum')])
        r=analyze_benchmark_csv(path);m=r['benchmarks'][0]
        self.assertEqual(m['shots'],200);self.assertEqual(m['successes'],185)
        self.assertTrue(m['wilson95'][0]<m['empirical_success_rate']<m['wilson95'][1])
    def test_ion_wrong_provider(self):
        path=csvfile(self.p/'h.csv',['source_id','processor','experiment','successes','shots','data_kind','provider'],
            [('x','Helios','b',1,2,'executed_hardware_shots','IBM')])
        with self.assertRaises(ValueError):analyze_benchmark_csv(path)
    def test_ion_spec_not_heldout_hardware(self):
        path=csvfile(self.p/'h.csv',['source_id','processor','experiment','successes','shots','data_kind','provider'],
            [('spec','Helios','b',9,10,'published_specification','Quantinuum')])
        with self.assertRaises(ValueError):analyze_benchmark_csv(path,heldout_required=True)
    def test_ion_refuses_fractional_shots(self):
        path=csvfile(self.p/'h.csv',['source_id','processor','experiment','successes','shots','data_kind','provider'],
            [('p','Helios','b','0.5','3','executed_hardware_shots','Quantinuum')])
        with self.assertRaises(ValueError):analyze_benchmark_csv(path)

    def test_ibm_majority_exact(self):
        self.assertAlmostEqual(independent_majority_error(3,.1),.028)
    def test_ibm_bad_d(self):
        with self.assertRaises(ValueError):independent_majority_error(4,.1)
    def test_ibm_two_epoch_heldout(self):
        cols=['snapshot_id','backend','calibration_utc','calibration_sha256',
         'executed_qasm_sha256','bitstrings_sha256','code_family','distance','logical_state',
         'final_data_bitstring','count','readout_flip_probability']
        h=['a'*64,'b'*64,'c'*64]
        rows=[['s1','ibm_fez','2026-01-01T00:00:00+00:00',*h,'repetition',3,'0','000',90,.04],
          ['s1','ibm_fez','2026-01-01T00:00:00+00:00',*h,'repetition',3,'0','111',10,.04],
          ['s2','ibm_fez','2026-02-01T00:00:00+00:00',*h,'repetition',3,'0','000',80,.04],
          ['s2','ibm_fez','2026-02-01T00:00:00+00:00',*h,'repetition',3,'0','111',20,.04]]
        path=csvfile(self.p/'i.csv',cols,rows)
        r=compare_from_verified_flat_table(path)
        self.assertEqual([x['split'] for x in r['results']],['train_epoch','heldout_epoch'])
        self.assertAlmostEqual(r['results'][1]['observed_final_bit_majority_failure'],.2)
        self.assertNotEqual(r['results'][1]['observed_final_bit_majority_failure'],r['results'][1]['independent_readout_only_prediction'])
    def test_ibm_1_epoch_fails(self):
        cols=['snapshot_id','backend','calibration_utc','calibration_sha256',
         'executed_qasm_sha256','bitstrings_sha256','code_family','distance','logical_state',
         'final_data_bitstring','count','readout_flip_probability']
        path=csvfile(self.p/'i.csv',cols,[['s1','ibm_fez','2026-01-01T00:00:00Z',*['a'*64]*3,'repetition',3,'0','000',90,.04]])
        with self.assertRaises(ValueError):compare_from_verified_flat_table(path)

    def test_neutral_atom_parallel_geometry(self):
        x={'atoms_um':{'a':[0,0],'b':[1,0],'c':[20,0],'d':[21,0]},
          'two_atom_operations':[['a','b'],['c','d']],
          'exclusion_radius_um':5,'two_atom_gate_duration_us':3}
        r=schedule(x);self.assertEqual(r['layer_count'],1);self.assertEqual(r['modeled_entangling_time_us'],3)
    def test_neutral_atom_blockaded(self):
        x={'atoms_um':{'a':[0,0],'b':[1,0],'c':[2,0],'d':[3,0]},
          'two_atom_operations':[['a','b'],['c','d']],
          'exclusion_radius_um':5,'two_atom_gate_duration_us':3}
        self.assertEqual(schedule(x)['layer_count'],2)
    def test_neutral_atom_gate_precedence(self):
        x={'atoms_um':{'a':[0,0],'b':[1,0],'c':[30,0],'d':[31,0]},
          'two_atom_operations':[['a','b'],['a','c'],['c','d']],
          'exclusion_radius_um':5,'two_atom_gate_duration_us':3}
        r=schedule(x);self.assertGreaterEqual(r['layer_count'],3)
    def test_neutral_invalid_coordinates(self):
        with self.assertRaises(ValueError):schedule({'atoms_um':{'a':[0,0],'b':[float('nan'),1]},'two_atom_operations':[['a','b']],
          'exclusion_radius_um':5,'two_atom_gate_duration_us':3})

    def test_xanadu_numeric_density(self):
        try:import numpy as np
        except ImportError:self.skipTest('numpy optional')
        from ftqc_resource_estimator.xanadu_analysis import analyze_density_matrix
        p=self.p/'rho.npy';np.save(p,np.diag([1.,0.]))
        r=analyze_density_matrix(p)
        self.assertAlmostEqual(r['purity'],1)
        self.assertAlmostEqual(r['wigner_origin_parity_convention'],2/math.pi)
    def test_xanadu_density_reject_nonpositive(self):
        try:import numpy as np
        except ImportError:self.skipTest('numpy optional')
        from ftqc_resource_estimator.xanadu_analysis import analyze_density_matrix
        p=self.p/'rho.npy';np.save(p,np.diag([1.3,-.3]))
        with self.assertRaises(ValueError):analyze_density_matrix(p)
    def test_xanadu_reject_object_pickle(self):
        try:import numpy as np
        except ImportError:self.skipTest('numpy optional')
        from ftqc_resource_estimator.xanadu_analysis import analyze_density_matrix
        p=self.p/'obj.npy';np.save(p,{'unsafe':'object'})
        with self.assertRaises(ValueError):analyze_density_matrix(p)
    def test_aurora_workbook_explicit(self):
        try:from openpyxl import Workbook
        except ImportError:self.skipTest('openpyxl optional')
        from ftqc_resource_estimator.xanadu_analysis import aurora_figure_from_workbook
        w=Workbook();s=w.active;s.title='Demo';s.append(['transmission','count']);s.append([.1,40]);s.append([.2,60]);
        path=self.p/'fig.xlsx';w.save(path)
        r=aurora_figure_from_workbook(path,'Demo','transmission','count',unit='shots')
        self.assertEqual(r['point_count'],2)
        self.assertIn('NOT_COMPUTED',r['comparison'])
    def test_aurora_wrong_column(self):
        try:from openpyxl import Workbook
        except ImportError:self.skipTest('openpyxl optional')
        from ftqc_resource_estimator.xanadu_analysis import aurora_figure_from_workbook
        w=Workbook();path=self.p/'fig.xlsx';w.save(path)
        with self.assertRaises(ValueError):aurora_figure_from_workbook(path,'Sheet','unknown','Y',unit='shots')

if __name__=='__main__':unittest.main()
