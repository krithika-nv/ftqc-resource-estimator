"""These genuinely execute external backends only when scientifically installed.

CI installs them; local machines lacking Stim skip rather than fake a result.
"""
import importlib.util
import unittest

@unittest.skipUnless(importlib.util.find_spec("stim") and importlib.util.find_spec("pymatching"),
                     "real Stim/PyMatching required, never substitute synthetic fixture")
class RealStimIntegrationTests(unittest.TestCase):
    def test_noiseless_rotated_memory_x(self):
        import stim
        import pymatching
        from ftqc_resource_estimator.stim_memory import simulate_memory
        r=simulate_memory(stim,pymatching,distance=3,rounds=5,physical_error=0,shots=100,seed=99,basis='X')
        self.assertEqual(r['failures'],0)
        self.assertEqual(r['trivial_decoder_failures'],0)

    def test_seeded_real_noisy_memory_has_consistent_count(self):
        import stim
        import pymatching
        from ftqc_resource_estimator.stim_memory import simulate_memory
        x=simulate_memory(stim,pymatching,distance=3,rounds=5,physical_error=.02,shots=150,seed=100,basis='Z')
        y=simulate_memory(stim,pymatching,distance=3,rounds=5,physical_error=.02,shots=150,seed=100,basis='Z')
        self.assertEqual(x['failures'],y['failures'])
        self.assertEqual(x['circuit_sha256'],y['circuit_sha256'])

if __name__ == '__main__':unittest.main()
