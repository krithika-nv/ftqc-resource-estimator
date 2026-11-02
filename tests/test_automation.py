"""Offline guards for the runner and checksum-aware Zenodo manifests."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'/'automation'))
from run_pipeline import safe_id, pipeline_plan, SOURCES
from acceptance_gate_report import report as gate_report
from zenodo_neutral_atom import summarize
from source_updates import SOURCES as GIT_SOURCES

class AutomationTests(unittest.TestCase):

    def test_gate_report_never_upgrades_inventory_to_paper_validation(self):
        result=gate_report({'run_id':'a','execution_passed':True,'all_external_inputs_available':True,
            'steps':[{'step':'helios_inventory','status':'passed'}, {'step':'aurora_reproduction','status':'passed'}]})
        self.assertFalse(result['four_platform_paper_reproduction_completed'])
        self.assertFalse(result['families']['trapped_ion']['paper_protocol_reproduced'])
        self.assertEqual(result['families']['photonic']['checks']['figure_reproduction'],'passed')

    def test_all_four_platforms_present_in_evidence_plan(self):
        plan=pipeline_plan('evidence',True)
        families={s['family'] for s in plan}
        self.assertGreaterEqual(len(plan),16)
        self.assertEqual(families-{'all'},{'superconducting','photonic','trapped_ion','neutral_atom'})
        self.assertIn('all', families)  # Cross-platform workload and review reports
        names={s['step'] for s in plan}
        for item in ('download_ibm_fez','fetch_aurora','fetch_gkp','fetch_helios',
                     'fetch_ion_specs','fetch_neutral_qec','ibm_raw_decode',
                     'aurora_workbook','helios_inventory','neutral_source_inventory'):
            self.assertIn(item,names)

    def test_download_destinations_are_per_family_and_rooted(self):
        self.assertEqual(SOURCES['ibm_fez'].name,'ibm_fez.tar.gz')
        self.assertEqual(SOURCES['aurora'].name,'xanadu_aurora')
        self.assertEqual(SOURCES['gkp'].name,'xanadu_gkp')
        self.assertEqual(SOURCES['helios'].name,'quantinuum_helios')
        self.assertEqual(SOURCES['ion_specs'].name,'quantinuum_specifications')
        self.assertEqual(SOURCES['neutral_qec'].name,'neutral_atom_qec')
        self.assertTrue(all(p.is_absolute() for p in SOURCES.values()))

    def test_local_no_data_four_family_manifest(self):
        import tempfile
        import contextlib
        import io
        import run_pipeline
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            # Ensure hermeticity even when a contributor has downloaded real
            # 600 MB experimental datasets into the working checkout.
            no_sources={k:Path(tmp)/'absent'/k for k in run_pipeline.SOURCES}
            with patch.object(run_pipeline,'SOURCES',no_sources), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_pipeline.main(['--profile','evidence','--run-id','offline-test','--base-dir',tmp]),0)
            report=json.loads((Path(tmp)/'offline-test'/'run_manifest.json').read_text())
            self.assertEqual(len(report['platforms']),4)
            self.assertFalse(report['hardware_validation_completed'])
            self.assertTrue((Path(tmp)/'offline-test'/'SUMMARY.md').is_file())
            self.assertEqual(report['profile'],'evidence')
            progress=json.loads((run_pipeline.RESULTS/'COMPONENT_PROGRESS.json').read_text())
            self.assertEqual(progress['latest_run_id'],'offline-test')
            self.assertEqual(progress['strict_acceptance_summary']['gates_total'],34)
            self.assertFalse(progress['strict_acceptance_summary']['hardware_validated_end_to_end'])

    def test_review_bundle_does_not_include_original_raw_data(self):
        import tempfile
        from package_platform_review import generate
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'review.zip'
            status=generate(path,Path(tmp))
            import zipfile
            with zipfile.ZipFile(path) as z:
                names=z.namelist()
                self.assertIn('REVIEW_INDEX.json',names)
                self.assertFalse(any('ibm_fez.tar.gz' in n or 'quadratures.npy' in n for n in names))

    def test_run_id_guard(self):
        self.assertEqual(safe_id('20261031-github-42'),'20261031-github-42')
        for value in ('../escape','.', 'x/y','abc; rm -rf .','', 'x'*101):
            with self.assertRaises(ValueError):safe_id(value)

    def test_allowlist_git_urls(self):
        self.assertEqual(len(GIT_SOURCES),5)
        self.assertTrue(all(u.startswith('https://github.com/') and u.endswith('.git') for u in GIT_SOURCES.values()))

    def test_zenodo_checksum_and_metadata(self):
        item={'id':15685795,'metadata':{'title':'Mock surface QEC'},'files':[{'key':'subdir/records.csv',
              'size':42,'checksum':'md5:abcd','links':{'self':'https://zenodo.org/api/records/15685795/files/records/content'}}]}
        result=summarize(item)
        self.assertEqual(result['files'][0]['size_bytes'],42)
        self.assertEqual(result['files'][0]['filename'],'subdir/records.csv')

    def test_zenodo_does_not_accept_path_traversal(self):
        for bad in ('../secret','/tmp/fake','data/../../secret'):
            item={'id':15685795,'files':[{'key':bad,'size':3,'checksum':'md5:abc',
              'links':{'self':'https://zenodo.org/small'}}]}
            with self.assertRaises(RuntimeError):summarize(item)
