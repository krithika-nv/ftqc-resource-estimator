import unittest
import random
from dataclasses import replace
from ftqc_resource_estimator.architecture import Architecture, ResourceSupply, Workload
from ftqc_resource_estimator.model import Scenario
from ftqc_resource_estimator.queue_simulation import sample_latency,sample_statistics

def fixture(rate=2.0):
    noise=Scenario('toy',.001,.01,.1,cycle_microseconds=1,decode_microseconds=1)
    return Architecture('toy',noise,ResourceSupply(1,rate,.6,(.9,)))

class QueueTests(unittest.TestCase):
    def test_repeatability(self):
        w=Workload(3,40,.1)
        a=sample_statistics(fixture(),3,w,trials=50,seed=55)
        b=sample_statistics(fixture(),3,w,trials=50,seed=55)
        self.assertEqual(a,b)

    def test_cannot_finish_faster_than_computation(self):
        w=Workload(3,20,.1)
        a=fixture()
        total=sample_latency(a,3,w,random.Random(44))
        self.assertGreaterEqual(total,20*(3*1+1))

    def test_faster_supply_reduces_mean_under_supply_limitation(self):
        w=Workload(3,50,.1)
        slow=sample_statistics(fixture(.1),3,w,trials=70,seed=22)
        fast=sample_statistics(fixture(10),3,w,trials=70,seed=22)
        self.assertGreater(slow.mean_us,fast.mean_us)

    def test_startup_penalty_in_mean(self):
        w=Workload(2,30,.1)
        x=sample_statistics(fixture(5),3,w,trials=150,seed=123)
        self.assertGreater(x.mean_us,x.ideal_envelope_us)

    def test_rejects_fractional_resource_bundle(self):
        w=Workload(2,4,.1,resources_per_qubit_layer=.6)
        with self.assertRaises(ValueError):sample_latency(fixture(),3,w,random.Random(1))
