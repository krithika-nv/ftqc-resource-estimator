"""A self-reported verified status never substitutes for raw evidence."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('audit_contract',ROOT/'scripts/automation/audit_ftqc_end_to_end.py')
M=importlib.util.module_from_spec(S); S.loader.exec_module(M)

class AuditTests(unittest.TestCase):
    def test_missing_all_never_certifies(self):
        r=M.audit({'schema':'ftqc.four-family-evidence.v1','families':{}})
        self.assertEqual(set(r['families']),set(M.REQUIRED))
        self.assertFalse(r['independently_validated_end_to_end_ftqc'])
        self.assertFalse(r['all_evidence_file_contracts_met'])
        self.assertEqual(r['total_required_gates'],34)
        self.assertEqual(r['submitted_gate_dossiers'],0)
        self.assertIn('not mean 34 experiments failed',r['zero_dossiers_explanation'])
    def test_hashes_are_checked(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path=Path(temp)/'raw.json'; path.write_text('example')
            rel=path.relative_to(ROOT).as_posix()
            item={'status':'verified','evidence':[{'artifact':rel,'sha256':'0'*64}]}
            r=M.audit({'schema':'ftqc.four-family-evidence.v1','families':{
                'superconducting':{'gates':{'device_calibration':item}}}})
            self.assertEqual(r['families']['superconducting']['gates']['device_calibration']['status'],'invalid_evidence')
            item['evidence'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            r=M.audit({'schema':'ftqc.four-family-evidence.v1','families':{
                'superconducting':{'gates':{'device_calibration':item}}}})
            self.assertEqual(r['families']['superconducting']['gates']['device_calibration']['status'],'evidence_file_hash_matched')
            self.assertFalse(r['independently_validated_end_to_end_ftqc'])
    def test_invalid_schema(self):
        with self.assertRaises(ValueError):M.audit({'schema':'wrong'})
if __name__=='__main__':unittest.main()
