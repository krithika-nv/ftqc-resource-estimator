"""Measured IBM Manila source subset & importer contract; no fabricated device outcomes."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from ftqc_resource_estimator.public_calibration import (
    validate_calibration, normalize_full_ibm_properties,
    project_calibration, produce_outputs, CURATED_URL, CURATED_DATE,
)

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE/'examples/public_ibmq_manila_2024_subset.json'

class PublicCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.obj=json.loads(SOURCE.read_text())

    def test_real_snapshots_metadata(self):
        validate_calibration(self.obj)
        self.assertEqual(self.obj['backend_name'],'ibmq_manila')
        self.assertEqual(self.obj['last_update_date'], CURATED_DATE)
        self.assertEqual(self.obj['upstream_raw_url'], CURATED_URL)
        self.assertEqual(len(self.obj['qubits']),5)
        self.assertEqual(len(self.obj['two_qubit_gates']),8)

    def test_q2_measured_variability(self):
        q=self.obj['qubits'][2]
        self.assertAlmostEqual(q['t2_echo_us'],25.150897893938303)
        self.assertAlmostEqual(q['readout_error'],0.0964)
        self.assertAlmostEqual(self.obj['qubits'][3]['readout_error'],0.0144)

    def test_five_qubits_does_not_certify_surface_code(self):
        proj=project_calibration(self.obj)
        self.assertFalse(proj['surface_code_hardware_prediction_supported'])
        self.assertTrue(proj['five_qubit_repetition_memory_demo_only'])
        self.assertEqual(proj['t2_ramsey_us'],'NOT_MEASURED_IN_THIS_SNAPSHOT')

    def test_echo_t2_not_used_in_relaxation_derived_proxy(self):
        original=project_calibration(self.obj)
        changed=copy.deepcopy(self.obj)
        for q in changed['qubits']:
            q['t2_echo_us']=q['t1_us']
        out=project_calibration(changed)
        self.assertEqual(original['relaxation_only_pX_per_qubit_approx'],
                         out['relaxation_only_pX_per_qubit_approx'])
        self.assertEqual(original['stim_parameters_ILLUSTRATIVE'],out['stim_parameters_ILLUSTRATIVE'])

    def test_output_provenance_and_no_claim(self):
        with tempfile.TemporaryDirectory() as td:
            produce_outputs(self.obj,Path(td),source_type='CURATED_PUBLISHED_SUBSET',
                            source_sha256=sha256(SOURCE.read_bytes()).hexdigest(),source_url=CURATED_URL)
            p=json.loads((Path(td)/'provenance.json').read_text())
            self.assertFalse(p['raw_file_verified'])
            self.assertFalse(p['hardware_validation_completed'])
            self.assertIn('NOT hardware-validated',(Path(td)/'CALIBRATION_IMPORT_REPORT.md').read_text())
            for file in ('qubit_calibrations.csv','coupling_errors.csv','calibration_projection.json'):
                self.assertTrue((Path(td)/file).is_file())

    def test_raw_original_format_parses_equivalent_metrics(self):
        # Construct a parser test fixture from a verified *known* curated subset.
        # This fixture is NOT presented as an upstream raw original.
        qlist=[]
        for q in self.obj['qubits']:
            pairs=[('T1','us','t1_us'),('T2','us','t2_echo_us'),
                   ('readout_error','','readout_error'),
                   ('prob_meas0_prep1','','prob_meas0_prep1'),
                   ('prob_meas1_prep0','','prob_meas1_prep0'),
                   ('readout_length','ns','readout_length_ns')]
            qlist.append([{'name':name,'unit':unit,'value':q[key]} for name,unit,key in pairs])
        gates=[]
        for g in self.obj['two_qubit_gates']:
            gates.append({'gate':'cx','qubits':g['qubits'],
                         'parameters':[{'name':'gate_error','unit':'','value':g['gate_error']},
                                       {'name':'gate_length','unit':'ns','value':g['gate_length_ns']}]})
        raw={'backend_name':self.obj['backend_name'],
             'backend_version':self.obj['backend_version'],
             'last_update_date':self.obj['last_update_date'],
             'qubits':qlist,'gates':gates}
        derived=normalize_full_ibm_properties(raw)
        self.assertEqual(derived['qubits'],self.obj['qubits'])
        self.assertEqual(derived['two_qubit_gates'],self.obj['two_qubit_gates'])

    def test_missing_t1_fails_closed(self):
        obj=copy.deepcopy(self.obj); obj['qubits'][0].pop('t1_us')
        with self.assertRaises(ValueError):validate_calibration(obj)

    def test_bad_echo_ratio_fails(self):
        obj=copy.deepcopy(self.obj); obj['qubits'][1]['t2_echo_us']=1e5
        with self.assertRaises(ValueError):validate_calibration(obj)

    def test_inconsistent_readout_data_fails(self):
        obj=copy.deepcopy(self.obj); obj['qubits'][0]['readout_error']=0.2
        with self.assertRaises(ValueError):validate_calibration(obj)

    def test_bad_unit_rejected_raw(self):
        obj={'backend_name':'ibmq_test','last_update_date':CURATED_DATE,
             'qubits':[[{'name':'T1','unit':'ms','value':80}]], 'gates':[]}
        with self.assertRaises(ValueError):normalize_full_ibm_properties(obj)

    def test_incomplete_coupling_rejected(self):
        obj=copy.deepcopy(self.obj); obj['two_qubit_gates']=[x for x in obj['two_qubit_gates']
                                            if 2 not in x['qubits']]
        validate_calibration(obj)
        with self.assertRaises(ValueError):project_calibration(obj)

    def test_malformed_timestamp_rejected(self):
        obj=copy.deepcopy(self.obj);obj['last_update_date']='2024-05-27'
        with self.assertRaises(ValueError):validate_calibration(obj)

    def test_no_claim_actual_software_simulator_without_backend(self):
        proj=project_calibration(self.obj)
        self.assertEqual(proj['stim_parameters_ILLUSTRATIVE']['distance'],3)
        self.assertEqual(proj['stim_parameters_ILLUSTRATIVE']['rounds'],3)
        self.assertNotIn('hardware_logical_failure',proj)

if __name__=='__main__': unittest.main()
