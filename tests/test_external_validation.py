import csv, json, tempfile, unittest
from pathlib import Path
from argparse import Namespace
from external_validation.core import wilson
from external_validation.runner import ibm,helios,neutral

class ValidationTests(unittest.TestCase):
    def test_wilson(self):
        x=wilson(3,10);self.assertEqual(x['rate'],.3)
        self.assertTrue(x['ci95'][0]<.3<x['ci95'][1])
        with self.assertRaises(ValueError):wilson(12,10)
    def write(self,path,rows):
        with open(path,'w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    def test_ibm_holdout(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.csv'; o=Path(td)/'o.json'
            self.write(p,[{'epoch':e,'shot_id':s,'distance':3,'observed_logical':(e+s)%2,'predicted_logical':0} for e in (1,2,3,4) for s in (1,2)])
            ibm(Namespace(input=str(p),output=str(o),holdout_fraction=.25))
            data=json.loads(o.read_text());self.assertEqual(data['held_out_epochs'],[4]);self.assertEqual(sum(x['trials'] for x in data['by_epoch_distance']),8)
    def test_ibm_single_epoch_descriptive_and_authentic_cross_chain_holdout(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'shots.csv';o=Path(td)/'analysis.json'
            rows=[]
            for state in (0,1):
                for chain in range(3):
                    for shot in range(9):
                        rows.append({'epoch':123,'shot_id':f's{state}-c{chain}-{shot}',
                            'distance':3,'rounds':3,'basis':'Z','initial_state':state,
                            'snapshot_id':'ibm_fez/d3_r3/job_1','chain':chain,'decoder':'mwpm',
                            'observed_logical':state,'predicted_logical':state ^ int(shot==0 and chain==2)})
            self.write(p,rows)
            ibm(Namespace(input=str(p),output=str(o),holdout_fraction=.25))
            result=json.loads(o.read_text())
            self.assertEqual(result['temporal_holdout']['status'],'unavailable_single_decoded_calibration_epoch')
            self.assertEqual(result['cross_chain_holdout']['status'],'evaluated')
            self.assertEqual(result['cross_chain_holdout']['evaluated_conditions'],2)
            self.assertTrue(all(x['holdout_chain']==2 and x['train_chains']==[0,1]
                                for x in result['cross_chain_holdout']['evaluations']))
            self.assertEqual(sum(x['holdout']['trials'] for x in result['cross_chain_holdout']['evaluations']),18)
            self.assertEqual(result['total_rows'],54)
            self.assertEqual(result['cross_chain_holdout']['evaluations'][0]['protocol']['basis'],'Z')
            self.assertEqual(result['cross_chain_holdout']['evaluations'][0]['protocol']['decoder'],'mwpm')

    def test_ibm_temporal_requires_matching_protocol(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'shots.csv';o=Path(td)/'analysis.json'
            rows=[]
            for epoch,basis in [(10,'X'),(20,'Z')]:
                for chain in range(2):
                    rows.append({'epoch':epoch,'shot_id':f'{epoch}-{chain}',
                        'distance':5,'rounds':5,'basis':basis,'initial_state':0,
                        'snapshot_id':f'job{epoch}','chain':chain,'decoder':'mwpm',
                        'observed_logical':0,'predicted_logical':0})
            self.write(p,rows)
            ibm(Namespace(input=str(p),output=str(o),holdout_fraction=.25))
            data=json.loads(o.read_text())
            self.assertEqual(data['held_out_epochs'],[20])
            self.assertEqual(data['temporal_holdout']['status'],'unavailable_no_matched_decoded_protocol_across_epochs')
            self.assertEqual(len(data['temporal_holdout']['matched_protocol_evaluations']),0)

    def test_ibm_temporal_matched_protocol_without_shot_leakage(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'shots.csv';o=Path(td)/'analysis.json';rows=[]
            for epoch,shots in [(10,8),(20,10)]:
                for chain in range(2):
                    for shot in range(shots):
                        rows.append({'epoch':epoch,'shot_id':f'{epoch}-{chain}-{shot}',
                            'distance':3,'rounds':3,'basis':'Z','initial_state':0,
                            'snapshot_id':f'job{epoch}','chain':chain,'decoder':'mwpm',
                            'observed_logical':0,'predicted_logical':int(shot==0)})
            self.write(p,rows)
            ibm(Namespace(input=str(p),output=str(o),holdout_fraction=.25))
            x=json.loads(o.read_text());matches=x['temporal_holdout']['matched_protocol_evaluations']
            self.assertEqual(len(matches),1)
            self.assertEqual(matches[0]['training']['trials'],16)
            self.assertEqual(matches[0]['holdout']['trials'],20)
            self.assertEqual(matches[0]['holdout_epoch'],20)
            self.assertEqual(x['temporal_holdout']['status'],'matched_protocol_evaluation_available')

    def test_helios(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'h.csv';o=Path(td)/'o.json'
            self.write(p,[{'benchmark':'x','condition':'A','successes':9,'trials':10,'source_file':'paper.csv','source_key':'row1'}])
            helios(Namespace(input=str(p),output=str(o)))
            self.assertEqual(json.loads(o.read_text())['groups'][0]['successes'],9)
    def test_neutral_strata(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'n.csv';o=Path(td)/'o.json'
            self.write(p,[{'shot_id':str(i),'distance':3,'rounds':3,'logical_failure':i%2,'atom_loss':i%2,'decoder':'source'} for i in range(6)])
            neutral(Namespace(input=str(p),output=str(o)))
            self.assertEqual(len(json.loads(o.read_text())['groups']),2)
if __name__=='__main__':unittest.main()
