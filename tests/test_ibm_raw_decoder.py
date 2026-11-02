import csv
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
import sys
import types
from pathlib import Path
from unittest.mock import patch

from external_validation.ibm_raw import (_detection_events, _declared_pairs,
    _bits, _state_objects, inspect_archive, process, qasm_registers)


def fixture(path, *, malformed=False):
    with tarfile.open(path,'w:gz') as tf:
        for job,day in enumerate((10,20)):
            prefix=f'ibm_fez/d3_r2/job_{job}/'
            props={'backend_properties':{'backend_name':'ibm_fez',
                 'last_update_date':f'2026-10-{day}T00:00:00+00:00',
                 'qubits':[[{'name':'T1','value':100e-6,'unit':'s'},{'name':'T2','value':80e-6,'unit':'s'},
                            {'name':'readout_error','value':.02,'unit':''}] for _ in range(3)],'gates':[]}}
            info=dict(backend='ibm_fez',d=3,rounds=2,basis='Z',shots=3,n_chains=1)
            qasm='''OPENQASM 2.0;
qreg q[5];
creg c_data_0_2_4[3];
creg c_syndrome_1_3[4];
measure q[1] -> c_syndrome_1_3[0];
measure q[3] -> c_syndrome_1_3[1];
measure q[1] -> c_syndrome_1_3[2];
measure q[3] -> c_syndrome_1_3[3];
measure q[0] -> c_data_0_2_4[0];
measure q[2] -> c_data_0_2_4[1];
measure q[4] -> c_data_0_2_4[2];
'''
            state0={'c_data_0_2_4': [[0,0,0],[0,1,0],[1,0,0]],
                    'c_syndrome_1_3':[[0,0,0,0],[1,1,1,1],[1,0,1,0]]}
            state1={'c_data_0_2_4': [[1,1,1],[1,0,1],[0,1,1]],
                    'c_syndrome_1_3':[[0,0,0,0],[1,1,1,1],[1,0,1,0]]}
            if malformed:state0['c_syndrome_1_3'][0]=[0,0]
            contents={'info.json':json.dumps(info).encode(),'calibration.json':json.dumps(props).encode(),
                'circuit_state0.qasm':qasm.encode(),'circuit_state1.qasm':qasm.encode(),
                'bitstrings.json':json.dumps({'state0':state0,'state1':state1}).encode()}
            for name,b in contents.items():
                m=tarfile.TarInfo(prefix+name);m.size=len(b);tf.addfile(m,io.BytesIO(b))

class TestIBMRaw(unittest.TestCase):
    def test_qasm_measured_register_pairs(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'test.tar.gz';fixture(f)
            v=inspect_archive(f,'ibm_fez',max_jobs=1)
            self.assertEqual(v['jobs'][0]['qasm_state0_registers']['c_syndrome_1_3'],4)
            self.assertEqual(v['jobs'][0]['register_shapes']['0']['c_data_0_2_4']['rows'],3)
    def test_known_syndrome_events(self):
        self.assertEqual(_detection_events((0,0,0),(0,0,0,0),3,2),[0]*6)
        self.assertEqual(_detection_events((1,0,0),(0,0,0,0),3,2),[0,0,0,0,1,0])
        self.assertEqual(_detection_events((0,0,0),(1,0,0,0),3,2),[1,0,1,0,0,0])
    def test_reject_ambiguous_packed_value(self):
        with self.assertRaisesRegex(ValueError,'ambiguous packed'):_bits('101',3,'data')
    def test_reject_missing_state_partition(self):
        with self.assertRaisesRegex(ValueError,'unrecognized state'):_state_objects({'c_data_0':[[0]]})
    def test_list_root_archive_fixture_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            old=Path(d)/'old.tar.gz';fixture(old)
            source=Path(d)/'list.tar.gz'
            with tarfile.open(old,'r:gz') as original, tarfile.open(source,'w:gz') as upgraded:
                for member in original:
                    payload=original.extractfile(member).read()
                    if member.name.endswith('/info.json'):
                        obj=json.loads(payload);obj['logical_states']='0;1';payload=json.dumps(obj).encode()
                    if member.name.endswith('/bitstrings.json'):
                        obj=json.loads(payload);payload=json.dumps([obj['state0'],obj['state1']]).encode()
                    tar=tarfile.TarInfo(member.name);tar.size=len(payload)
                    upgraded.addfile(tar,io.BytesIO(payload))
            with patch.dict('external_validation.ibm_raw.MD5',{'ibm_fez':hashlib.md5(source.read_bytes()).hexdigest()}):
                result=process(source,'ibm_fez',Path(d)/'shots.csv',Path(d)/'summary.json',decoder='majority')
            self.assertTrue(result['indexed_state_order_assumed'])
            self.assertEqual(result['total_decoded_chain_shots'],12)
            self.assertFalse((Path(d)/'shots.csv.partial').exists())
    def test_paired_list_root_is_recognized(self):
        first={'c_data_0_2_4':[[0,0,0]],'c_syndrome_0_2_4':[[0,0,0,0]]}
        second={'c_data_0_2_4':[[1,1,1]],'c_syndrome_0_2_4':[[0,0,0,0]]}
        self.assertEqual(_state_objects([first,second]),[(0,first),(1,second)])
    def test_state_list_needs_exact_two_unambiguous_states(self):
        with self.assertRaisesRegex(ValueError,'unrecognized state'):
            _state_objects([{'data':[]}, {'data':[]}])
    def test_real_csv_pipeline_majority(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'test.tar.gz';fixture(f)
            md5=hashlib.md5(f.read_bytes()).hexdigest()
            with patch.dict('external_validation.ibm_raw.MD5',{'ibm_fez':md5}):
                out=process(f,'ibm_fez',Path(d)/'result.csv',Path(d)/'report.json',decoder='majority')
            self.assertEqual(out['total_decoded_chain_shots'],12)
            self.assertEqual(len(out['jobs']),2)
            with (Path(d)/'result.csv').open() as fp:
                rows=list(csv.DictReader(fp))
            self.assertEqual(len(rows),12)
            self.assertTrue(set(r['epoch'] for r in rows).__len__()==2)
            self.assertIn('predicted_logical',rows[0])
    def test_mwpm_graph_and_zero_syndrome_baseline(self):
        # Minimal PyMatching-compatible fake isolates graph construction without
        # pretending to validate the actual PyMatching package in this runtime.
        class FakeMatching:
            def __init__(self):self.spatial=[];self.time=[]
            def add_edge(self,a,b,**kw):self.spatial.append((a,b,kw))
            def add_boundary_edge(self,a,**kw):self.time.append((a,kw))
            def decode(self,syndrome):
                if any(syndrome):return [0]
                return [0]
        mod=types.SimpleNamespace(Matching=FakeMatching)
        from external_validation.ibm_raw import _matching,_logical
        with patch.dict(sys.modules,{'pymatching':mod}):
            m=_matching(3,2,.01,.02)
            self.assertEqual(len(m.spatial),3+2*2)
            self.assertEqual(len(m.time),2*(2+1))
            self.assertEqual(_logical(m,(1,1,1),(0,0,0,0),3,2,'mwpm'),1)
            self.assertEqual(_logical(m,(0,0,0),(0,0,0,0),3,2,'mwpm'),0)

    def test_fail_on_malformed_real_shots(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'test.tar.gz';fixture(f,malformed=True)
            with patch.dict('external_validation.ibm_raw.MD5',{'ibm_fez':hashlib.md5(f.read_bytes()).hexdigest()}):
                with self.assertRaisesRegex(ValueError,'expected explicit'):
                    process(f,'ibm_fez',Path(d)/'r.csv',Path(d)/'s.json',decoder='majority')
    def test_reject_mismatched_qasm(self):
        with self.assertRaisesRegex(ValueError,'widths'):
            _declared_pairs('OPENQASM 2.0; creg c_data_0[2]; creg c_syndrome_1[4];',3,2,1)

if __name__=='__main__':unittest.main()
