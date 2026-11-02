"""Component reporting must never weaken scientific gates or invent experiment passes."""
import hashlib
import json
import sys
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/automation'))
from component_progress import build_report, load_run_manifest, as_markdown, COMPONENTS, FAMILIES
from audit_ftqc_end_to_end import audit

class ComponentProgressTests(unittest.TestCase):
    def setUp(self):
        self.acceptance=audit({'schema':'ftqc.four-family-evidence.v1','families':{}})

    def test_count_matches_all_strict_gates_without_certification(self):
        r=build_report(self.acceptance)
        self.assertEqual(r['strict_acceptance_summary']['gates_total'],34)
        self.assertEqual(r['strict_acceptance_summary']['registered_dossiers'],0)
        self.assertFalse(r['strict_acceptance_summary']['hardware_validated_end_to_end'])
        self.assertEqual(set(r['families']),set(FAMILIES))
        self.assertEqual(len(r['track_a']['studies']),6)
        self.assertEqual(len(r['shared_conditional_models']),2)
        self.assertEqual(r['latest_run_id'],None)
        self.assertTrue(all(x['recent_step_status'] in ('not_checked','not_applicable') for x in r['families']['photonic']['components']))
        self.assertIn('0/34',as_markdown(r))

    def test_manifest_pass_does_not_promote_sci_acceptance(self):
        run={'run_id':'real-run','profile':'evidence','steps':[
            {'step':'aurora_reproduction','status':'passed'},
            {'step':'ibm_raw_decode','status':'passed'},
            {'step':'helios_counts','status':'blocked_missing_input'}]}
        r=build_report(self.acceptance,run)
        self.assertEqual(r['families']['photonic']['components'][0]['recent_step_status'],'passed')
        self.assertEqual(r['families']['trapped_ion']['components'][1]['recent_step_status'],'blocked_missing_input')
        self.assertFalse(r['families']['photonic']['components'][0]['scientific_acceptance_inferred'])
        self.assertEqual(r['strict_acceptance_summary']['hash_matched_dossiers'],0)
        self.assertIn('published figure data replot',as_markdown(r))

    def test_accepted_file_hash_alone_is_not_scientific_certification(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            file=Path(d)/'proof.json';file.write_text('not a validated result')
            manifest={'schema':'ftqc.four-family-evidence.v1','families':{
                'superconducting':{'gates':{'device_calibration':{'status':'verified','evidence':[
                    {'artifact':file.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}]}}}}}
            r=build_report(audit(manifest))
            self.assertEqual(r['families']['superconducting']['scientific_acceptance']['gate_dossier_files_hash_matched'],1)
            self.assertFalse(r['strict_acceptance_summary']['hardware_validated_end_to_end'])

    def test_review_archive_manifest_read_without_arbitrary_execution(self):
        with tempfile.TemporaryDirectory() as d:
            z=Path(d)/'bundle.zip'
            with zipfile.ZipFile(z,'w') as f:
                f.writestr('logs/run-a/run_manifest.json',json.dumps({'run_id':'run-a','steps':[]}))
            self.assertEqual(load_run_manifest(review_bundle=z)['run_id'],'run-a')

    def test_component_catalog_covers_each_family_with_narrow_evidence(self):
        self.assertEqual(set(COMPONENTS),set(FAMILIES))
        for records in COMPONENTS.values():
            for key,title,source,test,artifact,scope,step in records:
                if scope=='planned_not_implemented':
                    # These can become implemented without making the catalog test fail.
                    self.assertTrue(source.startswith('src/'),source)
                else:
                    self.assertTrue((ROOT/source).is_file(),source)
                    self.assertTrue((ROOT/test).is_file(),test)
                self.assertNotEqual(scope,'four_platform_hardware_validated')

if __name__=='__main__': unittest.main()
