"""These are exact mathematical checks, not simulator observations."""
import math
import unittest
from ftqc_resource_estimator.sample_planning import (allowed_memory_error, zero_failures_upper95,minimum_shots_if_zero_failures,plan)

class SampleBudgetTests(unittest.TestCase):
    def test_total_budget_exact_independence(self):
        p=allowed_memory_error(.1,4,10)
        self.assertAlmostEqual(1-(1-p)**40,.1)
    def test_zero_wilson(self):
        self.assertAlmostEqual(zero_failures_upper95(1000),3.841458820694124/(1000+3.841458820694124))
        self.assertGreater(zero_failures_upper95(100),zero_failures_upper95(1000))
    def test_minimality(self):
        for budget in [.1,.01,.001,1e-5]:
            n=minimum_shots_if_zero_failures(budget)
            self.assertLessEqual(zero_failures_upper95(n),budget)
            self.assertGreater(zero_failures_upper95(n-1),budget)
    def test_report_is_explicit(self):
        x=plan(.001,4,10,20_000)
        self.assertFalse(x['zero_failures_could_pass_nominal_budget'])
        self.assertIn('NOT a hardware threshold',x['limitations'])
    def test_reject_invalid(self):
        for p in (0,1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):allowed_memory_error(p,1,1)
        for n in (0,-1,False):
            with self.assertRaises(ValueError):zero_failures_upper95(n)
        with self.assertRaises(ValueError):allowed_memory_error(.5,True,3)

if __name__=='__main__':unittest.main()
