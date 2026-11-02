"""Fixture-backed provenance validation; no synthetic fixture promoted to hardware data."""
import csv
import json
import tempfile
from pathlib import Path
import unittest
import zipfile
from ftqc_resource_estimator.hardware_dataset_adapters import inspect, write_report, classify
from ftqc_resource_estimator.evidence_catalog import validate_catalog

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/hardware_evidence_sources.json'

class SourceAdapters(unittest.TestCase):
    def test_registry_covers_all_four_families(self):
        rows=validate_catalog(json.loads(CAT.read_text()))
        self.assertEqual({s['hardware_family'] for s in rows}, {'photonic','superconducting','trapped_ion','neutral_atom'})
        self.assertEqual(len({s['id'] for s in rows}),len(rows))
        self.assertTrue(all(s['calibrates_surface_code'] is False for s in rows))

    def test_optical_aurora_numpy_quadratures(self):
        with tempfile.TemporaryDirectory() as d:
            import numpy as np
            p=Path(d)/'quadratures_batch_0.npy';np.save(p,np.zeros((12,4)))
            r=inspect('xanadu_aurora',p,catalog_path=CAT)
            self.assertEqual(r['files'][0]['shape'],[12,4])
            self.assertEqual(r['hardware_family'],'photonic')
            self.assertEqual(r['files'][0]['kind'],'measured_optical_quadratures')
            self.assertFalse('logical_error' in str(r))

    def test_gkp_analysis_results(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'analysis_results.npy';np.save(p,np.eye(2))
            x=inspect('xanadu_gkp',p,catalog_path=CAT)
            self.assertEqual(x['files'][0]['kind'],'reconstructed_gkp_state_analysis')
            self.assertEqual(x['files'][0]['inspection'],'npy_header')

    def test_no_pickle_execution_helios(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'exp_TQRB_Helios-1_2025-09-27.p';p.write_bytes(b'evil pickle not executed')
            x=inspect('quantinuum_helios',p,catalog_path=CAT)
            self.assertEqual(x['files'][0]['inspection'],'opaque_unsafe_pickle_do_not_load')
            self.assertIsNotNone(x['files'][0]['sha256'])

    def test_quantinuum_specs_separated_from_helios(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'H2-1';p.mkdir();f=p/'readout.csv';f.write_text('timestamp,error\n2026-01-01,0.001\n')
            x=inspect('quantinuum_specifications',p,catalog_path=CAT)
            self.assertEqual(x['hardware_family'],'trapped_ion')
            self.assertIn('not_calibration',x['files'][0]['kind'])

    def test_quera_task_and_archive_index(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'task_123.json').write_text('{"device":"Aquila","basis":"Z"}')
            with zipfile.ZipFile(p/'data.zip','w') as z:z.writestr('paper/measurement.json','{}')
            x=inspect('quera_aquila_2026',p,catalog_path=CAT)
            self.assertEqual(x['hardware_family'],'neutral_atom')
            self.assertEqual(len(x['files']),2)
            self.assertTrue(any(row['kind']=='neutral_atom_experiment_task' for row in x['files']))
            self.assertTrue(any(row['inspection']=='archive_directory_only_no_extraction' for row in x['files']))

    def test_unknown_source_fails(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'measured.json';f.write_text('{}')
            with self.assertRaisesRegex(ValueError,'Unknown source ID'):inspect('fake_photonic',f,catalog_path=CAT)

    def test_empty_and_invalid_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'no supported dataset files'):inspect('xanadu_aurora',Path(d),catalog_path=CAT)

    def test_pickle_like_numpy_object_not_loaded(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'analysis_results.npy';np.save(f,np.array([{'a':1}],dtype=object))
            x=inspect('xanadu_gkp',f,catalog_path=CAT)
            self.assertEqual(x['files'][0]['inspection'],'unsupported_numpy_array_safely_rejected')

    def test_reports_are_explicit_and_scope_safe(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'task_4.json';p.write_text('{"device":"QuEra Aquila"}')
            manifest=inspect('quera_aquila_2026',p,catalog_path=CAT)
            write_report(manifest,Path(d)/'out')
            data=json.loads((Path(d)/'out'/'DATASET_EVIDENCE_MANIFEST.json').read_text())
            self.assertIn('NOT_HARDWARE_CALIBRATED',data['status'])
            self.assertTrue((Path(d)/'out'/'DATASET_FILES.csv').exists())

    def test_large_files_not_hashed_by_default(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'analysis_results.npy';p.write_bytes(b'X'*1024)
            with patch('ftqc_resource_estimator.hardware_dataset_adapters.MAX_HASH_BYTES',512):
                x=inspect('xanadu_gkp',p,catalog_path=CAT)
            self.assertIsNone(x['files'][0]['sha256'])

    def test_source_no_mixed_family(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'some.csv';p.write_text('x\n1\n')
            ion=inspect('quantinuum_specifications',p,catalog_path=CAT)
            photo=inspect('xanadu_aurora',p,catalog_path=CAT)
            self.assertNotEqual(ion['hardware_family'],photo['hardware_family'])
            self.assertEqual(ion['files'][0]['sha256'],photo['files'][0]['sha256'])
            self.assertNotEqual(ion['files'][0]['kind'],photo['files'][0]['kind'])

if __name__=='__main__':unittest.main()
