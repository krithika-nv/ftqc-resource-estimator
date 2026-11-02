import unittest
from ftqc_resource_estimator.model import Scenario,estimate,choose_distance,logical_error_heuristic
S=Scenario('test',.001,.01,.1,1.0,5.0)
class ModelTests(unittest.TestCase):
    def test_monotonic_logical_error(self):
        self.assertGreater(logical_error_heuristic(3,S),logical_error_heuristic(5,S))
    def test_correct_accounting(self):
        e=estimate(3,S,2,100,.01)
        self.assertEqual(e.physical_sites,34)
        self.assertEqual(e.latency_microseconds,800)
        self.assertAlmostEqual(e.site_microseconds,27200)
    def test_search(self):
        best=choose_distance(S,1,10,.01)
        self.assertIsNotNone(best)
        self.assertTrue(best.target_satisfied)
    def test_bad_inputs(self):
        with self.assertRaises(ValueError):logical_error_heuristic(2,S)
        with self.assertRaises(ValueError):estimate(3,S,2,0,.1)
        with self.assertRaises(ValueError):logical_error_heuristic(3,Scenario('invalid',.2,.1,.1,1,1))
if __name__=='__main__':unittest.main()
