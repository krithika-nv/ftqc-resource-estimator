"""Ensure script hierarchy and entry-point references remain deployable."""
from __future__ import annotations
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ROOT/'scripts/commands'
TOOLS = ROOT/'scripts/tools'


class ScriptLayoutTests(unittest.TestCase):
    def test_only_categorized_script_entry_points(self):
        self.assertEqual(list(ROOT.glob('*.sh')), [])
        self.assertEqual(list((ROOT/'scripts').glob('*.sh')), [])
        self.assertEqual(list((ROOT/'scripts').glob('*.py')), [])
        self.assertTrue((ROOT/'scripts/automation/run_pipeline.py').is_file())
        self.assertTrue((COMMANDS/'RUN_ARCHITECTURE_STUDY.sh').is_file())
        self.assertTrue((TOOLS/'prepare_results.py').is_file())

    def test_shell_syntax_and_root_discovery(self):
        for path in sorted(COMMANDS.glob('*.sh')):
            with self.subTest(script=path.name):
                subprocess.run(['bash','-n',str(path)],check=True,capture_output=True)
                self.assertIn('BASH_SOURCE[0]',path.read_text(),
                              'Shell commands must resolve the repository root from their own location')
                self.assertTrue(path.stat().st_mode & 0o111)

    def test_entry_points_work_outside_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            for cmd in (["bash",str(COMMANDS/'RUN_EXTERNAL_VALIDATION.sh'),'--help'],
                        [sys.executable,str(TOOLS/'prepare_results.py'),'--help'],
                        [sys.executable,str(TOOLS/'download_2026_qec_calibration.py'),'--help']):
                with self.subTest(command=cmd[1]):
                    result=subprocess.run(cmd,cwd=tmp,stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT,text=True,timeout=15)
                    self.assertEqual(result.returncode,0,result.stdout[-2000:])

    def test_workflow_referenced_scripts_exist(self):
        for workflow in (ROOT/'.github/workflows').glob('*.yml'):
            content=workflow.read_text()
            import re
            for relative in re.findall(r'(?<![\w/])(scripts/(?:commands|tools|automation)/[\w.-]+\.(?:sh|py))',content):
                with self.subTest(workflow=workflow.name,script=relative):
                    self.assertTrue((ROOT/relative).is_file())


if __name__ == '__main__':
    unittest.main()
