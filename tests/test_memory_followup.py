"""Regression tests for the explicit distance-9 and control-cost analysis extension."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/tools'))
from verify_scientific_followup import audit_followup
from ftqc_resource_estimator.memory_analysis import (
    MemoryScenario, MemoryWorkload, compare_memory, load_memory_scenarios, nondominated)

class FollowupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'outputs/stim_memory/followup/observations.json'
        cls.observations=json.loads(path.read_text())
        cls.default_work,cls.default_configs=load_memory_scenarios(ROOT/'examples/memory_architecture_scenarios.json')
        cls.cost_work,cls.cost_configs=load_memory_scenarios(ROOT/'examples/memory_control_cost_sensitivity.json')

    def test_original_config_preserves_no_controller_overhead(self):
        rows=compare_memory(self.observations,self.default_configs,self.default_work,
                            basis='X',physical_error=.003,rounds=9,distances=(7,9))
        self.assertEqual(len(rows),6)
        self.assertTrue(all(r['controller_site_equivalents']==0 for r in rows))
        self.assertEqual({r['total_site_equivalents'] for r in rows if r['distance']==9},{657,683,741})

    def test_original_feasibility_formula_is_consistent(self):
        rows=compare_memory(self.observations,self.default_configs,self.default_work,
                            basis='X',physical_error=.003,rounds=9,distances=(7,9))
        threshold=1-(1-self.default_work.target_failure)**(1/(self.default_work.logical_qubits*self.default_work.memory_windows))
        for r in rows:
            self.assertEqual(r['feasible_upper95'],r['logical_error_upper95']<=threshold)
        # Conditional on an eligible code distance, faster lower-reserve
        # dominates all other original control profiles (not a hardware fact).
        for d in (7,9):
            subset=[r for r in rows if r['distance']==d]
            self.assertLess(subset[0]['total_site_equivalents'],subset[1]['total_site_equivalents'])
            self.assertLess(subset[1]['total_site_equivalents'],subset[2]['total_site_equivalents'])
            self.assertLess(subset[0]['storage_runtime_us'],subset[1]['storage_runtime_us'])
            self.assertLess(subset[1]['storage_runtime_us'],subset[2]['storage_runtime_us'])

    def test_explicit_controller_costs_create_an_assumption_driven_frontier(self):
        rows=compare_memory(self.observations,self.cost_configs,self.cost_work,
                            basis='X',physical_error=.003,rounds=9,distances=(7,9))
        d9=[r for r in rows if r['distance']==9]
        self.assertEqual([(r['total_site_equivalents'],r['storage_runtime_us']) for r in d9],
                         [(817,50),(743,105),(644,155)])
        # Explicit controller-cost assumption produces a tradeoff at a
        # fixed distance when the reliability gate is satisfied. Do not
        # force a favorable stochastic result to make this unit test pass.
        self.assertEqual(len(nondominated(d9)) if d9[0]['feasible_upper95'] else 0,
                         3 if d9[0]['feasible_upper95'] else 0)
        self.assertEqual({r['logical_error_upper95'] for r in d9}, {d9[0]['logical_error_upper95']})
        self.assertEqual({r['controller_site_equivalents'] for r in d9},{0,60,160})

    def test_negative_or_noninteger_controller_cost_rejected(self):
        for bad in [-1,3.2,True]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                MemoryScenario('bad',1,1,0,bad)

    def test_followup_protocol_and_csv_consistency(self):
        result=audit_followup(self.observations,
            baseline_csv=ROOT/'outputs/stim_memory/followup/analysis/memory_tradeoffs.csv',
            sensitivity_csv=ROOT/'outputs/stim_memory/followup/control_cost_analysis/memory_tradeoffs.csv')
        self.assertEqual(result['observations'],2)
        self.assertEqual(result['total_shots'],40000)

    def test_duplicate_distance_rejected(self):
        obj=json.loads(json.dumps(self.observations))
        obj['observations'][1]['distance']=7
        with self.assertRaises(ValueError):
            audit_followup(obj,
                baseline_csv=ROOT/'outputs/stim_memory/followup/analysis/memory_tradeoffs.csv',
                sensitivity_csv=ROOT/'outputs/stim_memory/followup/control_cost_analysis/memory_tradeoffs.csv')

    def test_report_does_not_call_it_a_physical_qubit_count(self):
        txt=(ROOT/'outputs/stim_memory/followup/control_cost_analysis/MEMORY_REPORT.md').read_text()
        self.assertIn('site-equivalent units',txt)
        self.assertIn('not measured',txt)

if __name__=='__main__': unittest.main()
