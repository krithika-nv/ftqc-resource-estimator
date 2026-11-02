import unittest
from ftqc_resource_estimator.model import Scenario
from ftqc_resource_estimator.pareto import frontier

class FrontierTest(unittest.TestCase):
    def test_tradeoffs_not_false_winner(self):
        fast=Scenario('fast',.001,.01,.01,.3,.05)
        slow=Scenario('slow',.001,.01,.01,2.0,.05)
        r=frontier([fast,slow],[3,5],1,10,.1)
        self.assertTrue(r)
        self.assertNotIn('slow',[e.scenario for e in r])
    def test_infeasible_is_empty(self):
        slow=Scenario('slow',.009,.01,.2,2.0,.05)
        self.assertEqual(frontier([slow],[3],10,100,.00000001),[])
