"""Measured physical primitive evidence ledger, deliberately separate from logical FTQC model."""
from __future__ import annotations
import argparse,hashlib,json,statistics,tarfile
from pathlib import Path

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def overview(ibm_archive:Path|None,helios_cached:Path|None,public_counts:Path|None,aurora:Path|None,neutral:Path|None,helios_raw:Path|None=None):
    out={'schema':'ftqc.measured-primitive-evidence-ledger.v1', 'family':{},
      'IMPORTANT':'Measured physical primitives are NOT logical-gate probabilities. No fitted physical-to-logical mapping is implied.'}
    for family in ('superconducting','photonic','trapped_ion','neutral_atom'):
        out['family'][family]={'status':'no_matched_ftqc_calibration','physical_evidence':[],'mapped_to_logical_workload':False}
    if ibm_archive and ibm_archive.is_file():
        calibrations={};
        with tarfile.open(ibm_archive,'r:gz') as tf:
            for m in tf:
                if m.isfile() and m.name.endswith('/calibration.json') and m.name.startswith('ibm_fez/'):
                    obj=json.load(tf.extractfile(m));stamp=obj.get('last_update_date')
                    if stamp not in calibrations:calibrations[stamp]=obj
        for stamp,obj in sorted(calibrations.items()):
            stats={}
            for name in ('T1','T2','readout_error','prob_meas0_prep1','prob_meas1_prep0'):
                vals=[float(e['value']) for qubit in obj.get('qubits',[]) for e in qubit
                    if e.get('name')==name and isinstance(e.get('value'),(float,int))]
                if vals:stats[name]={'count':len(vals),'mean':statistics.fmean(vals),'min':min(vals),'max':max(vals),
                                     'unit':'microseconds' if name in ('T1','T2') else 'probability'}
            out['family']['superconducting']['physical_evidence'].append({'source_sha256':digest(ibm_archive),
                 'calibration_timestamp':stamp,'backend':'ibm_fez','per_qubit_characterization':stats,
                 'scope':'measured_device_characterization_NOT_logical_calibration'})
    for path,family,kind in ((helios_cached,'trapped_ion','Helios saved notebook'),
                             (helios_raw,'trapped_ion','Helios independently reanalyzed raw MCMR histograms'),
                             (public_counts,'trapped_ion','H-series/REIMEI public trial-count reanalysis'),
                             (aurora,'photonic','Aurora numerical figure-data reproduction'),
                             (neutral,'neutral_atom','Neutral atom Zenodo source metadata')):
        if path and path.is_file():
            obj=json.loads(path.read_text());out['family'][family]['physical_evidence'].append({
               'source_sha256':digest(path),'type':kind,
               'description':'Source-traceable measured-data record; not a native FTQC calibration fit',
               'metadata_schema':obj.get('schema'),'hardware_identity':obj.get('hardware',obj.get('device','source-specific'))})
    for fam in out['family']:
        if out['family'][fam]['physical_evidence']:
            out['family'][fam]['status']='measured_characterization_available_but_unmapped_to_ftqc'
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--ibm',type=Path);p.add_argument('--helios',type=Path);p.add_argument('--quantinuum',type=Path);p.add_argument('--aurora',type=Path);p.add_argument('--neutral',type=Path)
    p.add_argument('--helios-raw',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=overview(a.ibm,a.helios,a.quantinuum,a.aurora,a.neutral,a.helios_raw)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Measured source ledger:',a.output)
if __name__=='__main__':main()
