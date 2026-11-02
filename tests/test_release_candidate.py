"""Regression contracts for real IBM QASM3, cached Helios outputs, and toy FTQC envelope."""
import json
import tempfile
import unittest
from pathlib import Path
from external_validation.ibm_raw import _state_objects,_declared_pairs
from external_validation.helios_notebook import extract
from ftqc_resource_estimator.conditional_architecture import run,project

ROOT=Path(__file__).resolve().parents[1]

class ReleaseCandidateTests(unittest.TestCase):
    def test_ibm_real_data_nested_state_identity(self):
        def record(state):return {'circuit_name':f'circuit-{state}', 'metadata':{'logical_state':state},
                                  'per_shot_cregs':{'c_data_1':[[state]*3],'c_syndrome_1':[[0,0]]}}
        data=[record(1),record(0)]
        self.assertEqual(_state_objects(data)[0][0],0)
        self.assertEqual(_state_objects(data)[0][1]['c_data_1'],[[0,0,0]])
    def test_ibm_real_data_requires_metadata(self):
        broken=[{'per_shot_cregs':{'c_data_1':[[0]],'c_syndrome_1':[[0]]}}]*2
        with self.assertRaisesRegex(ValueError,'metadata.logical_state'):_state_objects(broken)
    def test_ibm_openqasm3_physical_register_syndrome_order(self):
        qasm='''OPENQASM 3.0; bit[3] c_data_1_2_3; bit[4] c_syndrome_1_2_3;
        c_syndrome_1_2_3[0] = measure $12; c_syndrome_1_2_3[1] = measure $14;
        c_syndrome_1_2_3[2] = measure $12; c_syndrome_1_2_3[3] = measure $14;
        c_data_1_2_3[0] = measure $1; c_data_1_2_3[1] = measure $2; c_data_1_2_3[2] = measure $3;'''
        self.assertEqual(len(_declared_pairs(qasm,3,2,1)),1)
        with self.assertRaisesRegex(ValueError,'order'):_declared_pairs(qasm.replace('[2] = measure $12','[3] = measure $12').replace('[3] = measure $14','[2] = measure $14'),3,2,1)
    def test_helios_cached_notebook_has_no_executable_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'notebook.ipynb'
            f.write_text(json.dumps({'cells':[{'source':["filename='exp_MCMR_Crosstalk_Helios-1_q[0,2,4,6,8,10,12,14]_2026_01_01.p'"],
              'outputs':[{'output_type':'stream','text':[f'Global per MCMR Crosstalk {k} (1e-4):  0.2 +/- 0.01\n' for k in ('Infidelity','Error Channel p(0|1)','Error Channel p(1|0)','Error Channel p(L|0)','Error Channel p(L|1)')]}]}]}))
            out=extract(f)
            self.assertEqual(out['evidence_level'],'published_author_notebook_output_extraction')
            self.assertFalse(out['independent_reanalysis'])
    def test_four_family_native_units_and_no_calibration_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=run(ROOT/'examples/ILLUSTRATIVE_ONLY_four_family_profiles.json',ROOT/'evidence/validation/reference_workload.json',Path(tmp)/'results.json')
            self.assertEqual(len(out['results']),4)
            self.assertEqual(len({x['native_resource_unit'] for x in out['results'].values()}),4)
            self.assertTrue(all(not x['independent_hardware_validation'] for x in out['results'].values()))
    def test_t_more_operations_less_conditional_success(self):
        p=json.loads((ROOT/'examples/ILLUSTRATIVE_ONLY_four_family_profiles.json').read_text())['families']['photonic']
        w=json.loads((ROOT/'evidence/validation/reference_workload.json').read_text())
        a=project(p,w)
        w['operation_counts']['t_gate']*=3
        b=project(p,w)
        self.assertLess(b['prediction_conditional_on_assumptions']['success_independent_errors'],a['prediction_conditional_on_assumptions']['success_independent_errors'])
        self.assertGreater(b['prediction_conditional_on_assumptions']['expected_magic_state_attempts'],a['prediction_conditional_on_assumptions']['expected_magic_state_attempts'])
    def test_scenario_sensitivity_envelope_is_not_a_confidence_interval(self):
        p=json.loads((ROOT/'examples/ILLUSTRATIVE_ONLY_four_family_profiles.json').read_text())['families']['neutral_atom']
        w=json.loads((ROOT/'evidence/validation/reference_workload.json').read_text())
        result=project(p,w)
        band=result['assumption_sensitivity']
        self.assertIn('NOT_a_confidence_interval',band['type'])
        lo,hi=band['independent_success_range']
        predicted=result['prediction_conditional_on_assumptions']['success_independent_errors']
        self.assertLessEqual(lo,predicted)
        self.assertLessEqual(predicted,hi)

    def test_no_false_calibration_label(self):
        p=json.loads((ROOT/'examples/ILLUSTRATIVE_ONLY_four_family_profiles.json').read_text())['families']['superconducting']
        w=json.loads((ROOT/'evidence/validation/reference_workload.json').read_text())
        p['input_evidence_class']='hardware_calibrated'
        with self.assertRaisesRegex(ValueError,'illustrative'):
            project(p,w)

if __name__=='__main__':unittest.main()
