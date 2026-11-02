"""Documentation integrity checks: active links, citation IDs, safety status.

Current documentation is categorized and checked recursively.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = [ROOT / 'README.md', ROOT / 'ROADMAP.md', *sorted((ROOT / 'docs').rglob('*.md'))]


class DocumentationIntegrityTests(unittest.TestCase):
    def test_canonical_document_links_exist(self):
        missing = []
        for doc in ACTIVE:
            for url in re.findall(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', doc.read_text()):
                if url.startswith(('http:', 'https:', 'mailto:', '#')):
                    continue
                target = (doc.parent / url.split('#')[0])
                if not target.exists():
                    missing.append((str(doc.relative_to(ROOT)), url))
        self.assertEqual(missing, [])

    def test_all_reference_ids_declared(self):
        refs = (ROOT / 'docs' / 'reference' / 'REFERENCES.md').read_text()
        present = set(re.findall(r'\*\*R(\d+)\*\*', refs))
        self.assertEqual(present, {str(x) for x in range(1, 18)})
        used = set()
        for p in ACTIVE:
            if p.name == 'REFERENCES.md':
                continue
            used.update(re.findall(r'\bR([1-9]\d*)\b', p.read_text()))
        self.assertFalse(used - present, f'Undeclared citation IDs: {used - present}')
        self.assertIn('Sparse Blossom', refs)
        self.assertIn('Wilson, E. B.', refs)
        self.assertEqual(refs.count('https://doi.org/10.5281/zenodo.20768087'), 1)
        self.assertIn('**R17**',refs)
        self.assertIn('Track A', (ROOT / 'README.md').read_text())
        self.assertIn('Track B', (ROOT / 'README.md').read_text())

    def test_current_bibliography_has_no_obsolete_duplicate_entries(self):
        refs = (ROOT / 'docs' / 'reference' / 'REFERENCES.md').read_text()
        self.assertEqual(refs.count('https://doi.org/10.5281/zenodo.20768087'), 1)
        self.assertEqual(refs.count('https://doi.org/10.22331/q-2025-01-20-1600'), 1)
        self.assertEqual(refs.count('https://doi.org/10.1080/01621459.1927.10502953'), 1)
        self.assertTrue((ROOT / 'docs' / 'reference' / 'PROVENANCE_AND_CLAIMS.md').is_file())
        for path in ACTIVE:
            if path.name == 'REFERENCES.md':
                continue
            text = path.read_text()
            self.assertNotRegex(text, r'\bR21\b', str(path))

    def test_current_status_is_explicit(self):
        readme = (ROOT / 'README.md').read_text().lower()
        limitations = (ROOT / 'docs' / 'validation' / 'LIMITATIONS.md').read_text()
        self.assertIn('not hardware-calibrated', readme)
        self.assertIn('400,000-shot literature-aligned experiment', readme)
        self.assertIn('240,000-shot controller-induced idle-noise experiment', readme)
        self.assertIn('L21', limitations)
        self.assertTrue((ROOT / 'references' / 'kan2026_nighthawk.ris').is_file())

    def test_current_docs_are_categorized_without_legacy_snapshots(self):
        self.assertEqual(sorted(p.name for p in (ROOT / 'docs').glob('*.md')), ['README.md'])
        self.assertFalse((ROOT / 'docs' / 'archive').exists())
        self.assertFalse((ROOT / 'HISTORICAL_ARCHITECTURE_HANDOFF.md').exists())
        for area in ('guides', 'methods', 'hardware', 'validation', 'reference'):
            self.assertTrue(any((ROOT / 'docs' / area).glob('*.md')), area)


if __name__ == '__main__':
    unittest.main()
