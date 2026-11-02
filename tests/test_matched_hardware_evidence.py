import csv
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from hashlib import sha256
from ftqc_resource_estimator.matched_hardware_evidence import inventory,write_inventory,chronological_split
from ftqc_resource_estimator.evidence_catalog import validate_catalog
from ftqc_resource_estimator.hardware_prediction_comparison import audit


def archive(path,dates=('2026-09-15T00:00:00+00:00','2025-01-10T00:00:00+00:00'),missing=None):
    with tarfile.open(path,'w:gz') as tf:
        for i,date in enumerate(dates):
            prefix=f'ibm_fez/d3_r3/job_{i}/'
            props={'backend_properties':{'backend_name':'ibm_fez','last_update_date':date,
                 'qubits':[[{'name':'T1','value':100e-6,'unit':'s'},
                            {'name':'T2','value':50e-6,'unit':'s'},
                            {'name':'readout_error','value':0.02,'unit':''}] for _ in range(3)],'gates':[]}}
            info={'backend':'ibm_fez','d':3,'rounds':3,'basis':'X','shots':200,'n_chains':1}
            files={'calibration.json':json.dumps(props).encode(), 'info.json':json.dumps(info).encode(),
                   'bitstrings.json':b'{"c_data_0_1_2": [[0,0,0]]}',
                   'circuit_state0.qasm':b'OPENQASM 2.0; // state0',
                   'circuit_state1.qasm':b'OPENQASM 2.0; // state1'}
            for name,data in files.items():
                if (i,name)==missing:continue
                t=tarfile.TarInfo(prefix+name);t.size=len(data)
                tf.addfile(t,io.BytesIO(data))


class PairedEvidence(unittest.TestCase):
    def test_inspect_real_pair_layout_without_claiming_logical_validation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'analysis.tar.gz';archive(p)
            rows=inventory(p,'ibm_fez',as_of=datetime(2026,10,30,tzinfo=timezone.utc))
            self.assertEqual(len(rows),2)
            self.assertEqual(sum(r['within_freshness_cutoff'] for r in rows),1)
            self.assertEqual(rows[0]['distance'],3)
            self.assertEqual(rows[0]['code_family'],'repetition')
            out=Path(d)/'out'
            result=write_inventory(p,'ibm_fez',out,as_of=datetime(2026,10,30,tzinfo=timezone.utc))
            self.assertTrue(result['measurements']['real_raw_bitstrings_paired'])
            self.assertFalse(result['measurements']['hardware_logical_error_comparison_completed'])
            self.assertTrue((out/'MATCHED_EVIDENCE_INVENTORY.csv').exists())
            self.assertEqual(len(result['heldout_plan']['holdout']),1)
    def test_missing_pair_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.tar.gz';archive(p,missing=(0,'bitstrings.json'))
            with self.assertRaisesRegex(ValueError,'incomplete paired'):
                inventory(p,'ibm_fez')
    def test_same_calibration_epoch_refuses_holdout(self):
        r=[{'calibration_utc':'2026-09-15T00:00:00+00:00','snapshot_id':str(i)} for i in range(3)]
        self.assertEqual(chronological_split(r)['status'],'INSUFFICIENT_INDEPENDENT_CALIBRATION_TIMESTAMPS')
    def test_prediction_audit_rejects_unmatched_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.tar.gz';archive(p)
            inv=Path(d)/'inv';write_inventory(p,'ibm_fez',inv,as_of=datetime(2026,10,30,tzinfo=timezone.utc))
            with (inv/'MATCHED_EVIDENCE_INVENTORY.csv').open() as f:
                candidates=list(csv.DictReader(f))
            approved=json.loads((inv/'EVIDENCE_MANIFEST.json').read_text())['heldout_plan']['holdout']
            row=next(r for r in candidates if r['snapshot_id'] in approved)
            fields=['snapshot_id','backend','code_family','distance','rounds','basis','calibration_sha256','model_source_sha256','observed_source_sha256','evidence_split','observed_trials','observed_failures','predicted_failure']
            prediction={f:row[f] for f in fields if f in row}
            prediction.update(model_source_sha256='a'*64,observed_source_sha256=row['bitstrings_sha256'],evidence_split='holdout',observed_trials='200',observed_failures='10',predicted_failure='0.06')
            csvp=Path(d)/'pred.csv'
            with csvp.open('w',newline='') as fd:
                w=csv.DictWriter(fd,fieldnames=fields);w.writeheader();w.writerow(prediction)
            outcome=audit(csvp,inv/'MATCHED_EVIDENCE_INVENTORY.csv',Path(d)/'audit')
            self.assertEqual(outcome['evaluated'],1)
            prediction['basis']='Z'
            with csvp.open('w',newline='') as fd:
                w=csv.DictWriter(fd,fieldnames=fields);w.writeheader();w.writerow(prediction)
            with self.assertRaisesRegex(ValueError,'mismatch'):
                audit(csvp,inv/'MATCHED_EVIDENCE_INVENTORY.csv',Path(d)/'bad')
    def test_catalog_enforces_hardware_families(self):
        p=Path(__file__).resolve().parents[1]/'data/hardware_evidence_sources.json'
        reg=json.loads(p.read_text())
        sources=validate_catalog(reg)
        self.assertEqual({r['hardware_family'] for r in sources},{'superconducting','photonic','trapped_ion','neutral_atom'})
        reg['sources'][0]['calibrates_surface_code']=True
        with self.assertRaisesRegex(ValueError,'unsupported'):
            validate_catalog(reg)

if __name__=='__main__':unittest.main()
