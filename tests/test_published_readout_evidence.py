import copy
import json
import tempfile
from pathlib import Path
import unittest
from ftqc_resource_estimator.published_readout_evidence import DATA, summarize, validate_source_record, write_report
from ftqc_resource_estimator.device_calibration import audit_device_calibration

class MeasuredEvidenceTests(unittest.TestCase):
    def test_reported_durations_and_relative_change(self):
        s=summarize()
        self.assertAlmostEqual(s['readout_saved_us'],.8)
        self.assertAlmostEqual(s['readout_relative_reduction_percent'],100*.8/1.94)

    def test_logical_error_contrasts_are_per_round(self):
        s=summarize()
        self.assertAlmostEqual(s['X_memory']['derived_relative_reduction_percent'],100*(1.67-.98)/1.67)
        self.assertAlmostEqual(s['Z_memory']['derived_relative_reduction_percent'],100*(.82-.63)/.82)

    def test_coherence_only_fails_to_explain_observed_phase(self):
        s=summarize()
        self.assertAlmostEqual(s['phase_associated']['observed_minus_model_percentage_points'],.73)
        self.assertGreater(s['phase_associated']['measured_to_model_ratio'],4)
        self.assertAlmostEqual(s['bit_flip_associated']['observed_minus_model_percentage_points'],-.01)

    def test_source_numbers_immutable_without_review(self):
        edited=copy.deepcopy(DATA)
        edited['readout_duration_us']['short']=.45
        with self.assertRaises(ValueError): validate_source_record(edited)
        edited=copy.deepcopy(DATA)
        edited['device']='Google Willow'
        with self.assertRaises(ValueError): validate_source_record(edited)

    def test_report_and_provenance_files(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); write_report(p)
            self.assertEqual(json.loads((p/'SOURCE_RECORD.json').read_text()),DATA)
            self.assertIn('not new experiments', (p/'PUBLISHED_READOUT_AUDIT.md').read_text())
            self.assertEqual(len((p/'published_readout_comparison.csv').read_text().splitlines()),3)

class CalibrationGuardTests(unittest.TestCase):
    def test_missing_calibration_blocks_claim(self):
        template=Path(__file__).resolve().parents[1]/'examples/device_calibration_template.json'
        result=audit_device_calibration(json.loads(template.read_text()))
        self.assertFalse(result['calibration_metadata_complete'])
        self.assertFalse(result['actual_device_calibration_verified'])
        self.assertGreaterEqual(len(result['missing_or_invalid']),9)

    def test_cpmg_does_not_count_as_free_idle_t2(self):
        record={k:123 for k in ('t1_us','t2_ramsey_us','readout_short_us','readout_standard_us')}
        record.update(coherence_method='cpmg',device_identifier='Willow',
                      parameter_device_identifier='IBM')
        r=audit_device_calibration(record)
        self.assertTrue(any('CPMG' in x for x in r['missing_or_invalid']))
        self.assertTrue(any('MIXED_DEVICES' in x for x in r['missing_or_invalid']))

    def test_complete_metadata_still_not_authenticated(self):
        v=dict(device_identifier='processor',parameter_device_identifier='processor',schedule_device_identifier='processor',
               calibration_timestamp_utc='2026-10-20T00:00:00Z',primary_source_url='https://example.org/device',
               coherence_method='ramsey_free_induction',t1_us=99,t2_ramsey_us=70,
               readout_short_us=1.1,readout_standard_us=1.9,concurrent_readout_capacity=32,
               schedule_source_url='https://example.org/schedule',idle_placement='during readout',
               noise_correlation_source='https://example.org/correlations')
        result=audit_device_calibration(v)
        self.assertTrue(result['calibration_metadata_complete'])
        self.assertFalse(result['actual_device_calibration_verified'])

if __name__=='__main__': unittest.main()
