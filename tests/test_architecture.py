import unittest
from dataclasses import replace
from ftqc_resource_estimator.model import Scenario
from ftqc_resource_estimator.architecture import (Architecture,ArchitectureResult,ResourceSupply,
                         Workload,evaluate,pareto)
from ftqc_resource_estimator.reliability import EmpiricalTable,Measurement


def arch(**kw):
    noise=Scenario('base',physical_error=.001,threshold_assumption=.01,prefactor=.1,
                   cycle_microseconds=1.0,decode_microseconds=2.0)
    supply=ResourceSupply(2,10,.8,(.9,.8),factory_site_equivalents=100)
    return Architecture('test',noise,supply,**kw)

class ArchitectureTests(unittest.TestCase):
    def test_delivery_multiplies_segment_transmissions(self):
        self.assertAlmostEqual(arch().supply.delivery_probability,.8*.9*.8)

    def test_correct_site_bookkeeping(self):
        e=evaluate(arch(extra_patch_fraction=.1),3,Workload(2,10,.9))
        self.assertEqual(e.data_sites,18)
        self.assertEqual(e.syndrome_sites,16)
        self.assertEqual(e.reserve_sites,4)
        self.assertEqual(e.factory_site_equivalents,200)
        self.assertEqual(e.total_site_equivalents,238)

    def test_supply_expected_attempts(self):
        e=evaluate(arch(),3,Workload(2,10,.9))
        self.assertAlmostEqual(e.expected_preparation_attempts,20/(.8*.9*.8))

    def test_latency_is_pipeline_envelope_not_sum(self):
        e=evaluate(arch(),3,Workload(2,10,.9))
        self.assertAlmostEqual(e.compute_us,50)
        self.assertAlmostEqual(e.supply_us,20/(2*10*.8*.9*.8))
        self.assertEqual(e.latency_us,50)
        self.assertEqual(e.bottleneck,'compute')

    def test_slower_supplier_switches_bottleneck(self):
        a=arch()
        slow=replace(a,supply=replace(a.supply,attempts_per_factory_per_us=.01))
        e=evaluate(slow,3,Workload(2,10,.9))
        self.assertEqual(e.bottleneck,'supply')
        self.assertEqual(e.latency_us,e.supply_us)

    def test_more_factories_cost_more_but_can_reduce_latency(self):
        a=arch()
        low=replace(a,supply=replace(a.supply,factories=1,attempts_per_factory_per_us=.2))
        high=replace(a,supply=replace(a.supply,factories=4,attempts_per_factory_per_us=.2))
        w=Workload(2,100,.9)
        l=evaluate(low,3,w)
        h=evaluate(high,3,w)
        self.assertLess(h.supply_us,l.supply_us)
        self.assertGreater(h.total_site_equivalents,l.total_site_equivalents)

    def test_higher_transmission_reduces_supply_time(self):
        a=arch()
        b=replace(a,supply=replace(a.supply,path_transmissions=(.99,.99)))
        w=Workload(2,10,.9)
        self.assertLess(evaluate(b,3,w).supply_us,evaluate(a,3,w).supply_us)

    def test_empirical_interval_propogates_and_upper_is_stricter(self):
        e=EmpiricalTable([Measurement('rotated_surface','logical_layer',.001,3,1000,0)])
        r=evaluate(arch(),3,Workload(2,10,.02),e)
        self.assertEqual(r.mean_failure,0)
        self.assertTrue(r.model_feasible_mean)
        self.assertFalse(r.model_feasible_upper)
        self.assertGreater(r.upper_failure,0)

    def test_refuses_repetition_data_as_surface(self):
        e=EmpiricalTable([Measurement('repetition','logical_layer',.001,3,1000,0)])
        with self.assertRaises(KeyError):evaluate(arch(),3,Workload(2,10,.1),e)

    def test_refuses_memory_data_as_logical_layer(self):
        e=EmpiricalTable([Measurement('rotated_surface','memory_d_rounds',.001,3,1000,0)])
        with self.assertRaises(KeyError):evaluate(arch(),3,Workload(2,10,.1),e)

    def test_reliability_reused_but_latency_changes(self):
        a=arch()
        b=replace(a,noise=replace(a.noise,cycle_microseconds=4.0))
        r=evaluate(a,5,Workload(2,10,.9))
        s=evaluate(b,5,Workload(2,10,.9))
        self.assertEqual(r.mean_failure,s.mean_failure)
        self.assertLess(r.compute_us,s.compute_us)

    def test_pareto_excludes_dominated_and_infeasible(self):
        a=arch()
        b=replace(a,name='slow',noise=replace(a.noise,cycle_microseconds=3.0))
        w=Workload(2,10,.9)
        r=pareto([evaluate(a,3,w),evaluate(b,3,w)])
        self.assertEqual([i.architecture for i in r],['test'])
        self.assertEqual(pareto([evaluate(a,3,Workload(2,100000,.0000001))]),[])

    def test_bad_supply_probability(self):
        with self.assertRaises(ValueError):ResourceSupply(1,10,.5,(1.05,))
        with self.assertRaises(ValueError):ResourceSupply(1,10,.5,(0,))

    def test_bad_workload_inputs(self):
        with self.assertRaises(ValueError):Workload(0,10,.1)
        with self.assertRaises(ValueError):Workload(1,10,.1,resources_per_qubit_layer=-1)

    def test_reject_even_distance(self):
        with self.assertRaises(ValueError):evaluate(arch(),4,Workload(2,10,.9))

