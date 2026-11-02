import json,tempfile,unittest,zipfile
from pathlib import Path
from external_validation.neutral_archive import inspect

class NeutralSourceTests(unittest.TestCase):
    def test_inspect_does_not_run_or_extract(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'sample.zip';out=Path(d)/'report.json'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('code/analysis.ipynb','NOT EXECUTED')
                z.writestr('data/shots.csv','header\n1\n')
                z.writestr('data/caution.pickle','DANGEROUS')
            r=inspect(path,out,require_published_hash=False)
            self.assertEqual(r['member_count'],3)
            self.assertEqual({x['category'] for x in r['members']},{'potential_sample_data','analysis_code','executable_serialization_unsafe'})
            self.assertFalse((Path(d)/'code').exists())
            self.assertFalse(r['paper_target']['verified_against_local_data'])
    def test_reject_path_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'sample.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('../escape.csv','x')
            with self.assertRaisesRegex(ValueError,'unsafe path'):inspect(path,Path(d)/'out.json',require_published_hash=False)
