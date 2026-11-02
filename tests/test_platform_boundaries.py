"""Explicit proof that imported IBM data cannot become a generic-platform claim."""
import json
from pathlib import Path
import tempfile
import unittest

from ftqc_resource_estimator.platform_boundaries import (
    backend_family, check_calibration_use, scenario_scope, main
)
from ftqc_resource_estimator.modern_calibration import (
    normalize_backend_properties, publish_import
)


def parameter(name, value, unit=""):
    return {"name": name, "value": value, "unit": unit}


def sample():
    return normalize_backend_properties({
        "backend_name": "ibm_fez", "last_update_date": "2026-10-01T00:00:00+00:00",
        "qubits": [[parameter("T1", 80, "us"), parameter("T2", 70, "us"),
                     parameter("readout_error", .03)]]
    })


class PlatformBoundaryTests(unittest.TestCase):
    def test_ibm_is_superconducting_characterization_only(self):
        data=sample()
        self.assertEqual(data['hardware_family'], 'superconducting')
        result=check_calibration_use(data,target_family='superconducting')
        self.assertFalse(result['hardware_logical_error_prediction_validated'])
        self.assertEqual(result['evidence_class'],'measured_device_characterization')

    def test_reject_ibm_data_as_photonic_calibration(self):
        with self.assertRaisesRegex(ValueError,'cross-platform'):
            check_calibration_use(sample(),target_family='photonic')

    def test_reject_ibm_data_as_ion_calibration(self):
        with self.assertRaisesRegex(ValueError,'cross-platform'):
            check_calibration_use(sample(),target_family='trapped_ion')

    def test_reject_any_claim_of_validated_hardware_logical_error(self):
        with self.assertRaisesRegex(ValueError,'separate matched'):
            check_calibration_use(sample(),target_family='superconducting',
                                  purpose='hardware_logical_error_prediction')

    def test_reject_missing_timestamp_or_unknown_source(self):
        obj=sample();del obj['calibration_timestamp_utc']
        with self.assertRaisesRegex(ValueError,'timestamp'):
            check_calibration_use(obj,target_family='superconducting')
        with self.assertRaisesRegex(ValueError,'unrecognized backend'):
            backend_family('acme_model_alpha')

    def test_reject_falsely_marked_validated(self):
        obj=sample();obj['logical_error_hardware_prediction_validated']=True
        with self.assertRaisesRegex(ValueError,'validation field'):
            check_calibration_use(obj,target_family='superconducting')

    def test_hypothetical_profiles_have_separate_units(self):
        for family in ['photonic','superconducting','trapped_ion']:
            scope=scenario_scope(family)
            self.assertFalse(scope['device_calibration_used'])
            self.assertFalse(scope['can_rank_against_other_families'])

    def test_import_outputs_explicit_adapter_scope(self):
        model=sample()
        with tempfile.TemporaryDirectory() as tmp:
            publish_import([{'backend':'ibm_fez','normalized':model}],Path(tmp),
                           source='test synthetic schema fixture', raw_sha='0'*64,
                           criteria={'max_age_days':365})
            scope=json.loads((Path(tmp)/'ADAPTER_SCOPE.json').read_text())
            self.assertEqual(scope['adapter_family'],'superconducting')
            self.assertTrue(scope['cross_platform_reuse_prohibited'])
            self.assertFalse(scope['logical_error_hardware_prediction_validated'])



    def test_import_refuses_mixing_different_backends(self):
        first=sample();second={**sample(),'backend_name':'ibm_kingston'}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'mixed-device'):
                publish_import([{'backend':'ibm_fez','normalized':first},
                                {'backend':'ibm_kingston','normalized':second}],Path(tmp),
                               source='test synthetic schema fixture', raw_sha='0'*64,
                               criteria={'max_age_days':365})

    def test_hardware_study_writes_uncalibrated_per_family_manifest(self):
        from ftqc_resource_estimator.hardware_study import run
        source=Path(__file__).resolve().parents[1] / 'examples/hardware_profiles.json'
        with tempfile.TemporaryDirectory() as tmp:
            run(source,Path(tmp))
            report=json.loads((Path(tmp)/'PLATFORM_SCOPES.json').read_text())
            self.assertEqual(set(report),{'photonic','superconducting','trapped_ion'})
            self.assertTrue(all(not record['can_rank_against_other_families']
                                for record in report.values()))
            self.assertTrue(all(record['scenario_model_status']=='HYPOTHETICAL_UNCALIBRATED'
                                for record in report.values()))

    def test_cli_audits_real_normalized_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'calibration.json';path.write_text(json.dumps(sample()))
            self.assertEqual(main(['--calibration',str(path), '--target-family','superconducting']),0)
            with self.assertRaisesRegex(ValueError,'cross-platform'):
                main(['--calibration',str(path),'--target-family','photonic'])

if __name__=='__main__':unittest.main()
