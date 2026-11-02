import csv
import math
import tempfile
import unittest
from pathlib import Path
from ftqc_resource_estimator.reliability import (ErrorRate,Measurement,EmpiricalTable,
                     cumulative_failure, propagate, repetition_failure_exact,wilson)


class ReliabilityTests(unittest.TestCase):
    def test_wilson_zero_failures_not_zero_uncertainty(self):
        r=wilson(0,100)
        self.assertEqual(r.mean,0)
        self.assertEqual(r.lower,0)
        self.assertGreater(r.upper,.03)
        self.assertLess(r.upper,.04)

    def test_wilson_all_failures_not_certainty(self):
        r=wilson(100,100)
        self.assertEqual(r.mean,1)
        self.assertLess(r.lower,1)
        self.assertEqual(r.upper,1)

    def test_wilson_is_ordered_and_contains_point(self):
        for failures in [0,1,19,50,70,99,100]:
            r=wilson(failures,100)
            self.assertTrue(0<=r.lower<=r.mean<=r.upper<=1)

    def test_wilson_rejects_invalid_samples(self):
        for failures,shots in [(-1,10),(11,10),(0,0),(0,-5),(.5,10)]:
            with self.assertRaises(ValueError):wilson(failures,shots)

    def test_wilson_interval_contracts_with_data(self):
        a=wilson(10,100)
        b=wilson(100,1000)
        self.assertLess(b.upper-b.lower,a.upper-a.lower)

    def test_cumulative_failure_stable_for_tiny_probability(self):
        self.assertAlmostEqual(cumulative_failure(1e-15,1000000),1e-9,delta=1e-14)

    def test_cumulative_failure_ideal_bounds(self):
        self.assertEqual(cumulative_failure(0,100),0)
        self.assertEqual(cumulative_failure(1,0),0)
        self.assertEqual(cumulative_failure(1,100),1)
        self.assertAlmostEqual(cumulative_failure(.1,2),.19)

    def test_propagated_interval_is_monotonic(self):
        r=propagate(ErrorRate(.01,.005,.02,'empirical'),50)
        self.assertTrue(r.lower<r.mean<r.upper)

    def test_repetition_d3_closed_form(self):
        p=.07
        self.assertAlmostEqual(repetition_failure_exact(3,p),3*p*p-2*p**3)

    def test_repetition_distance_one_equals_p(self):
        for p in (0,.01,.5,1):
            self.assertAlmostEqual(repetition_failure_exact(1,p),p)

    def test_repetition_higher_distance_better_below_half(self):
        p=.06
        self.assertGreater(repetition_failure_exact(3,p),repetition_failure_exact(5,p))
        self.assertGreater(repetition_failure_exact(5,p),repetition_failure_exact(7,p))

    def test_repetition_rejects_even_distance(self):
        with self.assertRaises(ValueError):repetition_failure_exact(4,.01)

    def test_empirical_aggregates_same_key(self):
        m=[Measurement('rotated_surface','logical_layer',.001,3,100,1),
           Measurement('rotated_surface','logical_layer',.001,3,100,2)]
        r=EmpiricalTable(m).lookup('rotated_surface','logical_layer',.001,3)
        self.assertEqual((r.failures,r.observations),(3,200))

    def test_empirical_rejects_code_family_mismatch(self):
        e=EmpiricalTable([Measurement('repetition','memory_one_round',.01,3,100,3)])
        for fam,experiment in [('rotated_surface','memory_one_round'),('repetition','logical_layer')]:
            with self.assertRaises(KeyError):e.lookup(fam,experiment,.01,3)

    def test_empirical_rejects_extrapolation(self):
        e=EmpiricalTable([Measurement('rotated_surface','logical_layer',.001,3,100,1)])
        for distance,p in [(5,.001),(3,.002)]:
            with self.assertRaises(KeyError):e.lookup('rotated_surface','logical_layer',p,distance)

    def test_read_csv_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.csv'
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=['code_family','experiment','physical_error','distance','shots','failures'])
                w.writeheader();w.writerow(dict(code_family='rotated_surface',experiment='logical_layer',physical_error=.001,distance=3,shots=10,failures=2))
            r=EmpiricalTable.from_csv(path).lookup('rotated_surface','logical_layer',.001,3)
            self.assertAlmostEqual(r.mean,.2)
