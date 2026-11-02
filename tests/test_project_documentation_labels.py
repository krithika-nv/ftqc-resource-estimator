"""Keep project release labels out of user-facing documentation."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_LABEL = re.compile(r"(?<![A-Za-z0-9])v(?:0|1)\.\d+(?:\.\d+)?\b", re.I)

class ProjectDocumentationLabelsTests(unittest.TestCase):
    def test_no_project_release_labels_in_markdown(self):
        offenders = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*.md")
                     if PROJECT_LABEL.search(p.read_text(encoding="utf-8"))]
        self.assertFalse(offenders, f"Unexpected project release labels: {offenders}")

    def test_no_project_release_labels_in_filenames(self):
        offenders = [str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                     if PROJECT_LABEL.search(p.name)]
        self.assertFalse(offenders, f"Unexpected project release filenames: {offenders}")
