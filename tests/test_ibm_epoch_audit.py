"""Tests calibration-epoch coverage without needing vendor archives."""
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.automation.ibm_epoch_audit import audit


class EpochAuditTests(unittest.TestCase):
    def test_source_calibrations_and_exclusion_status(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ibm_sample.tar.gz'
            jobs = [('ibm_fez/d3_r3/job_2', '2025-08-26T00:03:11+00:00'),
                    ('ibm_fez/d3_r3/job_3', '2025-10-03T15:00:39+00:00')]
            with tarfile.open(path, 'w:gz') as tf:
                for prefix, stamp in jobs:
                    for fname, payload in [('info.json', {'backend':'ibm_fez','d':3,'rounds':3,'basis':'Z'}),
                                           ('calibration.json', {'stamp':stamp})]:
                        blob = json.dumps(payload).encode()
                        info = tarfile.TarInfo(prefix+'/'+fname)
                        info.size = len(blob)
                        tf.addfile(info, io.BytesIO(blob))
            summary = Path(folder) / 'summary.json'
            summary.write_text(json.dumps({'jobs':[{'snapshot_id':jobs[1][0]}],
                'skipped_jobs':[{'snapshot_id':jobs[0][0],'reason':'unsupported chronology'}]}))
            def normalize(payload, backend_override):
                self.assertEqual(backend_override,'ibm_fez')
                return {'calibration_timestamp_utc':payload['stamp']}
            with patch('scripts.automation.ibm_epoch_audit.normalize_backend_properties',normalize):
                result = audit(path,summary)
            self.assertEqual(result['job_count'],2)
            self.assertEqual(result['decoded_job_count'],1)
            self.assertEqual(result['excluded_job_count'],1)
            self.assertEqual(len(result['matched_protocol_candidate_pairs']),1)
            self.assertFalse(result['matched_protocol_candidate_pairs'][0]['all_epochs_decoded'])
            self.assertEqual([e['jobs'] for e in result['epochs']],[1,1])

if __name__ == '__main__':
    unittest.main()
