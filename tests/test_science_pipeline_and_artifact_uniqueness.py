"""Track A orchestration and unique evidence/output location contracts."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/automation'))
from run_pipeline import pipeline_plan
from package_platform_review import generate

class ScientificPipelineAndArtifactUniqueness(unittest.TestCase):
    def test_science_and_all_run_original_pareto_before_simulator(self):
        for profile in ('science','all'):
            with self.subTest(profile=profile):
                tasks=[p['step'] for p in pipeline_plan(profile,False)]
                self.assertEqual(tasks.count('unit_tests'),1)
                self.assertEqual(tasks.count('architecture_study'),1)
                self.assertEqual(tasks.count('real_science'),1)
                self.assertLess(tasks.index('architecture_study'), tasks.index('real_science'))
        self.assertEqual([p['step'] for p in pipeline_plan('ci',False)],['unit_tests'])

    def test_dry_run_plan_covers_track_b_analyses_and_reports(self):
        plan=pipeline_plan('all',True)
        tasks={x['step'] for x in plan}
        self.assertEqual(len(plan),len(tasks), 'Dry-run plan must not repeat steps')
        for required in ('ibm_majority_decode','ibm_calibration_readout_prediction',
                         'aurora_reproduction','helios_author_notebook_output',
                         'helios_raw_counts','neutral_source_survey',
                         'conditional_four_family_workload','measured_primitive_ledger',
                         'gate_review_snapshot'):
            self.assertIn(required,tasks)
        ibm={x['step'] for x in pipeline_plan('ibm',True)}
        self.assertIn('ibm_majority_decode',ibm)
        self.assertNotIn('helios_raw_counts',ibm)

    def test_science_workflow_archives_architecture_results(self):
        workflow=(ROOT/'.github/workflows/stim-memory.yml').read_text()
        self.assertIn('--profile science',workflow)
        self.assertIn('outputs/architecture_study/',workflow)
        architecture=(ROOT/'scripts/commands/RUN_ARCHITECTURE_STUDY.sh').read_text()
        self.assertIn('ftqc_resource_estimator.study',architecture)
        self.assertNotIn('unittest discover',architecture)
        self.assertNotIn('unittest discover',(ROOT/'scripts/commands/RUN_STIM_MEMORY.sh').read_text())

    def test_canonical_review_dossiers_not_duplicated_in_outputs(self):
        for family in ('superconducting','photonic','trapped_ion','neutral_atom'):
            self.assertTrue((ROOT/f'evidence/gate_review_candidates/{family}.md').is_file())
            self.assertFalse((ROOT/f'outputs/external_validation/gate_dossiers/{family}.md').exists())
        self.assertFalse((ROOT/'examples/generated/scenarios.csv').exists())
        self.assertTrue((ROOT/'outputs/scenarios.csv').is_file())
        self.assertFalse((ROOT/'outputs/stim_memory/followup/control_cost_analysis/memory_logical_failure.png').exists())
        self.assertTrue((ROOT/'outputs/stim_memory/followup/analysis/memory_logical_failure.png').is_file())

    def test_review_bundle_uses_one_dossier_location(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'review.zip'
            generate(path,Path(tmp))
            with zipfile.ZipFile(path) as z:
                names=z.namelist()
                self.assertIn('evidence/gate_review_candidates/superconducting.md',names)
                self.assertNotIn('outputs/external_validation/gate_dossiers/superconducting.md',names)
                self.assertEqual(len(names),len(set(names)))

    def test_dossier_generator_only_writes_snapshot_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp)/'candidates.json'
            subprocess.run([sys.executable,'scripts/automation/review_dossiers.py',
                            '--output',str(dst),'--source-only'],cwd=ROOT,check=True,capture_output=True)
            result=json.loads(dst.read_text())
            self.assertEqual(result['automatically_accepted'],0)
            self.assertEqual(len(result['families']),4)
            self.assertEqual(list(Path(tmp).rglob('*.md')),[])

    def test_controller_cost_run_removes_stale_shared_plot(self):
        from ftqc_resource_estimator.memory_analysis import main
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            out=tmp/'controller_cost'
            out.mkdir()
            (out/'memory_logical_failure.png').write_bytes(b'stale')
            self.assertEqual(main([
                '--observations',str(ROOT/'outputs/stim_memory/followup/observations.json'),
                '--config',str(ROOT/'examples/memory_control_cost_sensitivity.json'),
                '--distances','7,9','--physical-error','0.003','--rounds','9',
                '--output-dir',str(out),'--no-logical-failure-plot']),0)
            self.assertTrue((out/'memory_tradeoffs.csv').is_file())
            self.assertFalse((out/'memory_logical_failure.png').exists())

if __name__=='__main__':
    unittest.main()
