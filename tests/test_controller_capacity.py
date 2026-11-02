import unittest
from ftqc_resource_estimator.controller_capacity import ReadoutController,evaluate_controller,capacity_pareto

class ControllerCapacityTests(unittest.TestCase):
    def setUp(self):
        self.fast=ReadoutController('wide',256,.45,.55,.8,.35)
        self.slow=ReadoutController('narrow',32,.45,.55,2.5,.35)
        # TEST FIXTURE ONLY, not a scientific observation.
        self.source=[dict(distance=9,rounds=9,shots=20000,failures=10)]
    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):ReadoutController('bad',0,.45,.55,.8,.35)
    def test_invalid_power(self):
        with self.assertRaises(ValueError):ReadoutController('bad',32,.45,.55,.8,-.1)
    def test_channel_capacity_increases_batches(self):
        a,b=evaluate_controller(self.source,[self.fast,self.slow])
        self.assertGreater(b['readout_batches_per_round'],a['readout_batches_per_round'])
        self.assertGreater(b['total_memory_time_us'],a['total_memory_time_us'])
    def test_electronics_not_added_to_physical_qubits(self):
        a,b=evaluate_controller(self.source,[self.fast,self.slow])
        self.assertEqual(a['data_and_ancilla_qubits'],b['data_and_ancilla_qubits'])
        self.assertNotEqual(a['controller_power_proxy_w'],b['controller_power_proxy_w'])
        self.assertEqual(a['data_and_ancilla_qubits'],4*(2*81-1))
    def test_reliability_does_not_change_with_controller(self):
        a,b=evaluate_controller(self.source,[self.fast,self.slow])
        self.assertEqual(a['logical_error_upper95'],b['logical_error_upper95'])
        self.assertTrue(a['reliability_feasible'])
    def test_risk_budget_blocks_failed_memory(self):
        rows=evaluate_controller([dict(distance=7,rounds=9,shots=20000,failures=57)],[self.fast])
        self.assertFalse(rows[0]['reliability_feasible'])
        self.assertEqual(capacity_pareto(rows),[])
    def test_power_latency_frontier(self):
        rows=evaluate_controller(self.source,[self.fast,self.slow])
        self.assertEqual(len(capacity_pareto(rows)),2)
    def test_abstract_rounds_scale_time_not_error(self):
        a=evaluate_controller(self.source,[self.fast])[0]
        b=evaluate_controller([dict(distance=9,rounds=11,shots=20000,failures=10)],[self.fast])[0]
        self.assertGreater(b['total_memory_time_us'],a['total_memory_time_us'])
        self.assertEqual(a['logical_error_upper95'],b['logical_error_upper95'])
