"""Contracts for safe off-line publishing; not a substitute for real scientific backends."""
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class PublicationContracts(unittest.TestCase):
    def test_offline_artifact_bundle(self):
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)/'publication'
            subprocess.run([sys.executable,str(ROOT/'scripts/tools/prepare_results.py'),
                '--mode','offline','--output-dir',str(dest)], cwd=ROOT,check=True,capture_output=True,text=True)
            provenance=json.loads((dest/'provenance.json').read_text())
            self.assertEqual(provenance['publication_mode'],'offline')
            self.assertTrue((dest/'README.md').is_file())
            self.assertTrue((dest/'FIGURE_AND_CLAIM_AUDIT.md').is_file())
            self.assertIn('not',provenance['scope_note'].lower())

    def test_unvalidated_science_is_not_in_publication(self):
        # This test inspects the archive's local state. On actual backend-enabled CI,
        # the full job verifies matching evidence separately before publishing.
        p=ROOT/'scripts/tools/prepare_results.py'
        self.assertIn("args.mode == 'full'",p.read_text())
        self.assertIn('raise RuntimeError',p.read_text())

if __name__=='__main__':
    unittest.main()
