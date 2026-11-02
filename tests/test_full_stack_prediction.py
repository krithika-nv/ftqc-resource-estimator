"""Tests for the strict conditional logical-primitives model (synthetic inputs)."""
from __future__ import annotations
import copy
from datetime import datetime, timezone, timedelta
import unittest
from ftqc_resource_estimator.full_stack_prediction import evaluate,wilson,OPERATIONS


def fake_inputs():
    workload={'schema':'ftqc.logical-workload.v1','id':'unit_fixture',
              'operation_counts':{'prepare':2,'memory_cycle':10,'clifford_1q':4,'clifford_2q':3,'t_gate':2,'measure':2}}
    records=[]
    for op in OPERATIONS:
        for split,tick in [('train',1),('holdout',2)]:
            records.append({'operation':op,'split':split,'device_id':'synthetic_device',
            'code_family':'synthetic_code','protocol_id':op+'_fixture','run_id':f'{op}-{split}',
            'observed_utc':f'2026-10-0{tick}T12:00:00+00:00',
            'duration_us':2.0,'trials':1000,'failures':2 if split=='train' else 3})
    model={'schema':'ftqc.logical-primitives.v1','hardware_family':'trapped_ion',
           'device_id':'synthetic_device','code_family':'synthetic_code','observations':records}
    return model,workload

class FullStackPrimitiveTests(unittest.TestCase):
    def test_wilson_zero_not_certain(self):
        self.assertGreater(wilson(0,100)[1],0)
    def test_simple_matched_heldout(self):
        m,w=fake_inputs();r=evaluate(m,w)
        self.assertAlmostEqual(r['predicted_success_independent_primitives'], (1-0.002)**23)
        self.assertEqual(r['sum_of_serial_primitive_durations_us_no_overlap_assumed'],46)
        self.assertIn('NOT an end-to-end',r['claim_scope'])
    def test_no_missing_t_gate(self):
        m,w=fake_inputs();m['observations']=[x for x in m['observations'] if x['operation']!='t_gate']
        with self.assertRaisesRegex(ValueError,'t_gate'): evaluate(m,w)
    def test_leakage_rejected(self):
        m,w=fake_inputs();m['observations'][1]['run_id']=m['observations'][0]['run_id']
        with self.assertRaisesRegex(ValueError,'leakage'): evaluate(m,w)
    def test_mixed_devices_rejected(self):
        m,w=fake_inputs();m['observations'][0]['device_id']='other'
        with self.assertRaisesRegex(ValueError,'mixed devices'):evaluate(m,w)
    def test_reversed_epochs_rejected(self):
        m,w=fake_inputs();m['observations'][0]['observed_utc']='2026-10-05T12:00:00+00:00'
        with self.assertRaisesRegex(ValueError,'later'):evaluate(m,w)
    def test_protocol_mismatch_rejected(self):
        m,w=fake_inputs();m['observations'][1]['protocol_id']='different'
        with self.assertRaisesRegex(ValueError,'same operation protocol'):evaluate(m,w)
    def test_no_universal_workload_without_t(self):
        m,w=fake_inputs();w['operation_counts']['t_gate']=0
        with self.assertRaisesRegex(ValueError,'non-Clifford'):evaluate(m,w)
    def test_invalid_failures(self):
        m,w=fake_inputs();m['observations'][1]['failures']=2000
        with self.assertRaisesRegex(ValueError,'trial counts'):evaluate(m,w)
    def test_reject_naive_cross_protocol_pooling(self):
        m,w=fake_inputs();m['observations'][0]['protocol_id']='new_version'
        with self.assertRaisesRegex(ValueError,'same operation protocol'):evaluate(m,w)

if __name__=='__main__':unittest.main()
