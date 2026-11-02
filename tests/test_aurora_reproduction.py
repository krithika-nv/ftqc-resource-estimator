import tempfile,unittest
from pathlib import Path
from external_validation.aurora_reproduce import reproduce

class AuroraReproductionTests(unittest.TestCase):
    def test_real_matrix_layout_reconstructed(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as td:
            wb=Workbook();wb.remove(wb.active)
            for name in ('Fig 3c','Fig 3d'):
                sh=wb.create_sheet(name)
                sh.append(['matrix component',None,'experimental',None,'simulated'])
                sh.append(['row','column','X-measurement','Z-measurement','X-measurement','Z-measurement'])
                for r in range(3):
                    for c in range(3):sh.append([r,c,r+c,r-c,r+c+1,r-c-1])
            workbook=Path(td)/'source.xlsx';wb.save(workbook)
            report=reproduce(workbook,Path(td)/'out',plot=False)
            self.assertEqual(report['reproductions']['Fig 3c']['entries'],9)
            self.assertAlmostEqual(report['reproductions']['Fig 3d']['experiment_vs_simulation']['panel_1_experiment_vs_simulation']['rmse'],1.)
            self.assertTrue((Path(td)/'out'/'REPORT.json').exists())
    def test_reject_duplicate_or_incomplete_coordinates(self):
        from openpyxl import Workbook
        with tempfile.TemporaryDirectory() as td:
            wb=Workbook();sh=wb.active;sh.title='Fig 3c'
            sh.append(['matrix component',None,'experimental',None,'simulated'])
            sh.append(['row','column','a','b','c','d'])
            sh.append([0,0,1,2,3,4]);sh.append([1,1,1,2,3,4]);p=Path(td)/'a.xlsx';wb.save(p)
            with self.assertRaisesRegex(ValueError,'incomplete'):reproduce(p,Path(td)/'out','Fig 3c',plot=False)
