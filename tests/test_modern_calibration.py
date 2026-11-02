"""Synthetic schema fixtures only; NOT hardware data or device validation."""
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from ftqc_resource_estimator.modern_calibration import (
    normalize_backend_properties, parse_timestamp, check_age,
    import_zenodo_archive, publish_import,
)

T='2026-10-01T11:20:00+00:00'

def p(name,unit,val):return {'name':name,'unit':unit,'value':val}

def props():
    return {'backend_name':'ibm_fez','last_update_date':T,
            'qubits':[[p('T1','us',70+i),p('T2','us',80+i),
                        p('readout_error','',0.01+i/1000),
                        p('readout_length','ns',1150)] for i in range(3)],
            'gates':[{'gate':'cz','qubits':[0,1],
                       'parameters':[p('gate_error','',0.004),p('gate_length','ns',180)]}]}

class ModernImportTests(unittest.TestCase):
    def test_real_2026_property_schema_fixture(self):
        r=normalize_backend_properties(props(),backend_override='ibm_fez')
        self.assertEqual(len(r['qubits']),3)
        self.assertEqual(r['qubits'][0]['t1_us'],70)
        self.assertAlmostEqual(r['qubits'][0]['readout_length_us'],1.15)
        self.assertEqual(r['two_qubit_gates'][0]['gate'],'cz')
        self.assertAlmostEqual(r['two_qubit_gates'][0]['gate_length_us'],.18)
        self.assertFalse(r['logical_error_hardware_prediction_validated'])

    def test_reject_2024_snapshot_for_recent_use(self):
        t=parse_timestamp('2024-05-27T15:27:23-03:00')
        with self.assertRaisesRegex(ValueError,'stale'):
            check_age(t,as_of=datetime(2026,10,28,tzinfo=timezone.utc),max_age_days=180)

    def test_no_timestamp_rejected(self):
        r=props();r.pop('last_update_date')
        with self.assertRaisesRegex(ValueError,'timestamp'):normalize_backend_properties(r)

    def test_no_timezone_rejected(self):
        with self.assertRaisesRegex(ValueError,'UTC offset'):parse_timestamp('2026-10-01T11:20:00')

    def test_wrong_device_rejected(self):
        with self.assertRaisesRegex(ValueError,'mismatch'):normalize_backend_properties(props(),backend_override='ibm_kingston')

    def test_no_readout_error_rejected(self):
        r=props();r['qubits'][0]=r['qubits'][0][:-2]+r['qubits'][0][-1:]
        with self.assertRaisesRegex(ValueError,'missing'):normalize_backend_properties(r)

    def test_no_fictitious_projection(self):
        r=normalize_backend_properties(props())
        self.assertNotIn('logical_failure_probability',r)
        self.assertNotIn('stim_parameters_ILLUSTRATIVE',r)
        self.assertFalse(r['free_idle_ramsey_t2star_measured'])

    def test_zenodo_pairing_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'calibration.tar.gz'
            base='ibm_fez/d3_r3/job_2/'
            with tarfile.open(archive,'w:gz') as t:
                for name,data in [('info.json',{'backend':'ibm_fez','d':3,'rounds':3,'basis':'X'}),('calibration.json',props())]:
                    content=json.dumps(data).encode()
                    info=tarfile.TarInfo(base+name);info.size=len(content)
                    t.addfile(info,io.BytesIO(content))
            rows=import_zenodo_archive(archive,'ibm_fez',max_age_days=365,as_of=datetime(2026,10,28,tzinfo=timezone.utc))
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['distance'],3)
            self.assertEqual(rows[0]['rounds'],3)
            self.assertEqual(rows[0]['backend'],'ibm_fez')
            out=Path(tmp)/'out'
            manifest=publish_import(rows,out,source='test fixture, not real data',raw_sha=sha256(archive.read_bytes()).hexdigest(),criteria={'test':True})
            self.assertFalse(manifest['hardware_logical_error_validation_completed'])
            self.assertEqual(manifest['measured_qubit_rows'],3)
            self.assertTrue((out/'measured_qubits.csv').exists())

    def test_archive_skips_stale_snapshot_and_selects_newest(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'mixed.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                for job, stamp in [('job_1','2025-10-01T11:20:00+00:00'),
                                   ('job_2','2026-09-20T11:20:00+00:00'),
                                   ('job_3','2026-10-01T11:20:00+00:00')]:
                    base='ibm_fez/d3_r3/'+job+'/'
                    item=props();item['last_update_date']=stamp
                    for name, data in [('info.json',{'backend':'ibm_fez','d':3,'rounds':3}),
                                       ('calibration.json',item)]:
                        content=json.dumps(data).encode()
                        info=tarfile.TarInfo(base+name);info.size=len(content)
                        tar.addfile(info,io.BytesIO(content))
            data=import_zenodo_archive(archive,'ibm_fez',max_age_days=365,
                 as_of=datetime(2026,10,30,tzinfo=timezone.utc),max_snapshots=1)
            self.assertEqual(len(data),1)
            self.assertIn('job_3',data[0]['path'])
            self.assertEqual(data[0]['import_selection']['excluded_stale_snapshots'],1)
            self.assertEqual(data[0]['import_selection']['eligible_snapshots'],2)
            self.assertEqual(data[0]['import_selection']['archive_matching_snapshots'],3)
            out=Path(tmp)/'out'
            manifest=publish_import(data,out,source='synthetic test only',raw_sha='test',criteria={})
            self.assertEqual(manifest['archive_selection']['excluded_stale_snapshots'],1)

    def test_stale_only_archive_reports_newest_date_and_does_not_fake_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'old.tar.gz'
            with tarfile.open(archive,'w:gz') as tar:
                base='ibm_fez/d3_r3/job_1/'
                item=props();item['last_update_date']='2025-09-01T00:00:00+00:00'
                for name, data in [('info.json',{'backend':'ibm_fez'}),('calibration.json',item)]:
                    content=json.dumps(data).encode()
                    info=tarfile.TarInfo(base+name);info.size=len(content)
                    tar.addfile(info,io.BytesIO(content))
            with self.assertRaisesRegex(ValueError,'newest archive measurement'):
                import_zenodo_archive(archive,'ibm_fez',max_age_days=365,
                    as_of=datetime(2026,10,30,tzinfo=timezone.utc))

    def test_missing_pair_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'x.tar.gz'
            with tarfile.open(archive,'w:gz') as t:
                data=json.dumps(props()).encode();i=tarfile.TarInfo('ibm_fez/d3_r3/job_2/calibration.json');i.size=len(data);t.addfile(i,io.BytesIO(data))
            with self.assertRaisesRegex(ValueError,'info.json'):import_zenodo_archive(archive,'ibm_fez')

    def test_empty_wrong_backend_rejected(self):
        with self.assertRaisesRegex(ValueError,'published Zenodo'):import_zenodo_archive(Path('ignored'),'ibmq_manila')

if __name__=='__main__':unittest.main()
