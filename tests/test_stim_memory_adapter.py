"""Unit-test the integration protocol without claiming Stim was available."""
import unittest
try:
    import numpy as np
except ImportError:
    np = None  # the standard-library-only CI job may not have NumPy
from ftqc_resource_estimator.stim_memory import simulate_memory, _parse_distances, _parse_errors

class FakeCircuit:
    num_detectors=2
    num_observables=1
    def detector_error_model(self,**kwargs):
        assert kwargs=={'decompose_errors': True}
        return 'a fake detector model'
    def compile_detector_sampler(self,**kwargs):
        assert 'seed' in kwargs
        return self
    def sample(self,**kwargs):
        assert kwargs['separate_observables']
        assert kwargs['shots']==3
        return np.array([[0,0],[1,0],[0,1]],dtype=bool),np.array([[0],[1],[1]],dtype=bool)
    def __str__(self):return 'fake-circuit'

class FakeStim:
    class Circuit:
        @staticmethod
        def generated(*args,**kwargs):
            assert args[0]=='surface_code:rotated_memory_x'
            assert kwargs['distance']==3 and kwargs['rounds']==9
            assert kwargs['before_measure_flip_probability']==kwargs['after_clifford_depolarization']
            return FakeCircuit()

class FakeMatching:
    @staticmethod
    def from_detector_error_model(model):
        assert model=='a fake detector model'
        return FakeMatching()
    def decode_batch(self,detectors):
        return np.array([[0],[0],[1]],dtype=bool)
    def decode(self,detectors):
        return np.array([bool(detectors[1])],dtype=bool)
class FakePyMatching:
    Matching=FakeMatching

@unittest.skipUnless(np is not None, "NumPy is optional for the base standard-library test matrix")
class AdapterTests(unittest.TestCase):
    def test_fake_backend_proves_pipeline_counts_disagreements(self):
        obs=simulate_memory(FakeStim,FakePyMatching,distance=3,physical_error=.003,shots=3,seed=123)
        self.assertEqual(obs['failures'],1)
        self.assertEqual(obs['trivial_decoder_failures'],2)
        self.assertEqual(obs['experiment'],'memory_fixed_rounds')
        self.assertEqual(obs['rounds'],9)
        self.assertEqual(obs['batch_single_agreement_checked_shots'],3)
        self.assertEqual(len(obs['circuit_sha256']),64)
        self.assertEqual(obs['noise_profile'],'stim_uniform_circuit_noise_v1')
        self.assertEqual(obs['decoder'],'pymatching_mwpm_from_decomposed_dem')
    def test_noiseless_control_must_be_zero(self):
        with self.assertRaisesRegex(RuntimeError,'noiseless'):
            simulate_memory(FakeStim,FakePyMatching,distance=3,physical_error=0,shots=3,seed=123)
    def test_reject_unphysical_parameters(self):
        with self.assertRaises(ValueError):_parse_distances('3,4,7')
        with self.assertRaises(ValueError):_parse_errors('0.001,0.001')
        with self.assertRaises(ValueError):simulate_memory(FakeStim,FakePyMatching,distance=2,physical_error=.001,shots=3,seed=1)

if __name__=='__main__':unittest.main()
