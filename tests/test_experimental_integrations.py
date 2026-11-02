import hashlib,importlib.util,json,pickle,tempfile,unittest,zipfile
from pathlib import Path
from external_validation.ibm_readout_prediction import majority_error,data_map,extract_readout
from external_validation.quantinuum_json_counts import extract
from external_validation.helios_static_counts import parse
from external_validation.neutral_source_survey import survey
from scripts.automation.generate_native_scenarios import generate
from scripts.automation.review_dossiers import build
from scripts.automation.audit_ftqc_end_to_end import REQUIRED
from scripts.automation.run_pipeline import pipeline_plan
from scripts.automation.zenodo_neutral_atom import download

ROOT=Path(__file__).resolve().parents[1]
class ReleaseV13Tests(unittest.TestCase):
 def test_native_scenarios_distinct_and_explicit(self):
    original=json.loads((ROOT/'examples/ILLUSTRATIVE_ONLY_four_family_profiles.json').read_text())
    generated=generate(original)
    assert len(set(x['physical_resource_assumptions']['native_unit'] for x in generated['families'].values()))==4
    assert len(set(x['operation_durations_us']['clifford_2q'] for x in generated['families'].values()))==4
    assert all(x['input_evidence_class']=='illustrative_assumptions_unvalidated' for x in generated['families'].values())
 def test_readout_poisson_binomial(self):
    self.assertAlmostEqual(majority_error([.1,.1,.1]),3*.1**2*.9+.1**3)
    qasm='bit[3] c_data_0_1_2; c_data_0_1_2[0] = measure $5; c_data_0_1_2[1] = measure $7; c_data_0_1_2[2] = measure $9;'
    self.assertEqual(data_map(qasm)['c_data_0_1_2'],[5,7,9])
    cal={'qubits':[[{'name':'prob_meas1_prep0','value':.2}] for i in range(10)]}
    self.assertEqual(extract_readout(cal,0,[5,7,9]),[.2]*3)
 def test_public_hardware_counts_from_numbers(self):
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'H2-2/2025_08_28/SPAM.json';p.parent.mkdir(parents=True)
        p.write_text(json.dumps({'shots':100,'survival':{'0':{'0':99,'1':98}}}))
        report=extract(p);self.assertEqual(report['device'],'H2-2')
        self.assertEqual(sum(x['successes'] for x in report['rows']),197)
        self.assertNotIn('Helios',report['device'])
 def test_pickle_static_decoder_never_executes_constructor(self):
    data=pickle.dumps({'survival':{'0':999},'meta':[1,2,3]},protocol=4)
    self.assertEqual(parse(data)['survival']['0'],999)
 def test_dossiers_do_not_accept_files(self):
    with tempfile.TemporaryDirectory() as tmp:
        r=build(Path(tmp));self.assertEqual(r['automatically_accepted'],0)
        self.assertEqual(sum(map(len,r['families'].values())),sum(map(len,REQUIRED.values())))
        self.assertFalse(any(g['accepted'] for f in r['families'].values() for g in f.values()))
 def test_neutral_schema_preview_no_execution(self):
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'untrusted.zip';o=Path(tmp)/'out.json'
        with zipfile.ZipFile(p,'w') as z:z.writestr('measurements.csv','d,rounds,error,loss\n3,3,0,1\n')
        r=survey(p,o,verify_hash=False);self.assertEqual(r['inspected'][0]['csv_header'],'d,rounds,error,loss')
        self.assertFalse(r['loss_aware_decoder_verified'])
 def test_existing_neutral_archive_is_checksum_verified_not_blindly_skipped(self):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);source=root/'source.zip';source.write_bytes(b'correct verified bytes')
        record={'filename':'source.zip','size_bytes':len(source.read_bytes()),
                'checksum':'md5:'+hashlib.md5(source.read_bytes()).hexdigest(),
                'url':'https://zenodo.org/this-is-not-fetched'}
        # Existing hash-correct file is reused without a network call.
        download(record,root,1024)
        source.write_bytes(b'corrupt corrupt bytes')
        with self.assertRaises(RuntimeError):download(record,root,1024)
 def test_pipeline_plans_four_families(self):
    plan=pipeline_plan('evidence',True)
    names={x['step'] for x in plan}
    for name in ('ibm_calibration_readout_prediction','helios_raw_counts','neutral_source_survey','aurora_reproduction'):
        self.assertIn(name,names)
if __name__=='__main__':unittest.main()
