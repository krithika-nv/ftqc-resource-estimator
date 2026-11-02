"""Inventory paired measured QEC experimental evidence without inventing a hardware prediction.

This is *not* a decoder. It validates and indexes the dated calibration,
experiment protocol, raw bitstrings and executed QASM that must be paired
before any future calibration-conditioned prediction comparison is honest.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tarfile

from .modern_calibration import normalize_backend_properties, parse_timestamp, _read_member

ZENODO = 'https://doi.org/10.5281/zenodo.20768087'
REQUIRED = ('calibration.json', 'info.json', 'bitstrings.json', 'circuit_state0.qasm', 'circuit_state1.qasm')
BACKENDS = ('ibm_fez','ibm_kingston','ibm_pittsburgh')


def _positive_int(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(f'{name} must be a positive integer')
    return value


def inventory(archive: Path, backend: str, *, as_of: datetime | None = None,
              max_age_days: int = 365, max_jobs: int | None = None) -> list[dict]:
    """Inspect matching complete records, including stale records (never re-label stale as current)."""
    if backend not in BACKENDS: raise ValueError('unsupported IBM Zenodo backend')
    if max_age_days <= 0: raise ValueError('positive freshness limit required')
    if max_jobs is not None: _positive_int(max_jobs,'max_jobs')
    today=as_of or datetime.now(timezone.utc)
    if today.tzinfo is None: raise ValueError('as_of must have timezone')
    result=[]
    with tarfile.open(archive,'r:gz') as tf:
        members={m.name for m in tf.getmembers() if m.isfile()}
        cal_paths=sorted(n for n in members if n.endswith('/calibration.json') and backend in n.split('/'))
        if not cal_paths: raise ValueError('archive contains no calibrations for backend')
        for cal_path in cal_paths:
            prefix=cal_path[:-len('calibration.json')]
            missing=[n for n in REQUIRED if prefix+n not in members]
            if missing: raise ValueError(f'incomplete paired experimental record {prefix}: {missing}')
            info=json.loads(_read_member(tf,prefix+'info.json'))
            if not isinstance(info,dict): raise ValueError('invalid experimental info')
            if info.get('backend',info.get('device')) != backend:
                raise ValueError('experiment/backend mismatch')
            distance=_positive_int(info.get('d',info.get('distance')),'distance')
            rounds=_positive_int(info.get('rounds'),'rounds')
            shots=_positive_int(info.get('shots'),'shots')
            n_chains=_positive_int(info.get('n_chains'),'n_chains')
            basis=info.get('basis')
            if basis not in ('X','Z'): raise ValueError('unsupported logical basis')
            cal_bytes=_read_member(tf,cal_path)
            props=normalize_backend_properties(json.loads(cal_bytes),backend_override=backend)
            date=parse_timestamp(props['calibration_timestamp_utc'])
            age=(today-date).total_seconds()/86400
            if age < -1: raise ValueError('future-dated calibration record')
            hashes={}
            for filename in REQUIRED:
                raw=cal_bytes if filename=='calibration.json' else _read_member(tf,prefix+filename,max_bytes=80_000_000 if filename=='bitstrings.json' else 8_000_000)
                if len(raw)==0: raise ValueError('empty evidence file: '+prefix+filename)
                if filename=='bitstrings.json':
                    parsed=json.loads(raw)
                    if not isinstance(parsed,(dict,list)) or not parsed:
                        raise ValueError('unrecognized or empty bitstring JSON')
                hashes[filename]=sha256(raw).hexdigest()
            result.append({
                'snapshot_id':prefix.rstrip('/'), 'backend':backend,
                'hardware_family':'superconducting','code_family':'repetition',
                'distance':distance,'rounds':rounds,'basis':basis,
                'shots_per_circuit':shots,'parallel_chains':n_chains,
                'calibration_utc':date.isoformat(), 'age_days':round(max(age,0),2),
                'within_freshness_cutoff':age <= max_age_days,
                'calibration_sha256':hashes['calibration.json'],
                'info_sha256':hashes['info.json'],
                'bitstrings_sha256':hashes['bitstrings.json'],
                'qasm_state0_sha256':hashes['circuit_state0.qasm'],
                'qasm_state1_sha256':hashes['circuit_state1.qasm'],
            })
    if not result: raise ValueError('no matching complete evidence records')
    result.sort(key=lambda x:(x['calibration_utc'],x['snapshot_id']),reverse=True)
    if max_jobs is not None: result=result[:max_jobs]
    return result


def chronological_split(records:list[dict], *, training_fraction:float=.7) -> dict:
    """Only a *plan*: avoids leakage across jobs with the same timestamp."""
    if not 0 < training_fraction < 1: raise ValueError('invalid training fraction')
    dates=sorted({r['calibration_utc'] for r in records})
    if len(dates)<2:
        return {'status':'INSUFFICIENT_INDEPENDENT_CALIBRATION_TIMESTAMPS',
                'train':[],'holdout':[],'note':'At least two distinct calibration epochs required.'}
    n=max(1,min(len(dates)-1,int(len(dates)*training_fraction)))
    cutoff=dates[n-1]
    train=[r['snapshot_id'] for r in records if r['calibration_utc']<=cutoff]
    holdout=[r['snapshot_id'] for r in records if r['calibration_utc']>cutoff]
    return {'status':'SPLIT_PLAN_ONLY_NO_PREDICTIONS', 'cutoff_calibration_utc':cutoff,
            'train':train, 'holdout':holdout,
            'note':'Grouping by calibration epoch prevents same-epoch leakage. Confirm actual execution timing before asserting prospective validation.'}


def write_inventory(archive:Path, backend:str, output:Path, *, max_age_days:int=365,max_jobs:int|None=None,
                    as_of:datetime|None=None) -> dict:
    data=inventory(archive,backend,max_age_days=max_age_days,max_jobs=max_jobs,as_of=as_of)
    output.mkdir(parents=True,exist_ok=True)
    with (output/'MATCHED_EVIDENCE_INVENTORY.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(data[0]))
        writer.writeheader();writer.writerows(data)
    split=chronological_split(data)
    manifest={
        'source':ZENODO,'archive_sha256':sha256(archive.read_bytes()).hexdigest(),
        'archive_file':archive.name,'backend':backend,'hardware_family':'superconducting',
        'actual_records_inspected':len(data),
        'records_passing_freshness_cutoff':sum(r['within_freshness_cutoff'] for r in data),
        'records_exceeding_cutoff':sum(not r['within_freshness_cutoff'] for r in data),
        'max_age_days':max_age_days,
        'calibration_newest_utc':data[0]['calibration_utc'],
        'heldout_plan':split,
        'measurements':{'real_calibration_files_paired':True,'real_raw_bitstrings_paired':True,
            'transpiled_qasm_paired':True,'raw_bitstrings_decoded':False,
            'hardware_logical_error_comparison_completed':False,
            'matched_stim_prediction_completed':False},
        'study_scope':'MEASURED_REPETITION_CODE_INPUT_EVIDENCE_ONLY_NOT_SURFACE_CODE_VALIDATION',
        'note':'An inventory and split are evidence-readiness steps, not prediction/decoder evaluation.'
    }
    (output/'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'EVIDENCE_REPORT.md').write_text(
        '# Paired IBM hardware-QEC evidence audit\n\n'
        +f'- Source: {ZENODO}\n- Backend: `{backend}` (superconducting).\n'
        +f'- **Real paired jobs inspected:** {len(data)}.\n'
        +f'- **Within {max_age_days}-day cutoff:** {manifest["records_passing_freshness_cutoff"]}. '
        +f'Older: {manifest["records_exceeding_cutoff"]}.\n'
        +f'- Newest calibration timestamp: {data[0]["calibration_utc"]}.\n'
        +f'- Chronological evaluation split status: `{split["status"]}`.\n\n'
        +'Each job has same-directory `info.json`, `calibration.json`, actual transpiled QASM and hardware measurement bitstrings; all files are hashed. '
        +'**No hardware logical-error rate has been calculated, and no matched simulator prediction has been validated.** '
        +'Date freshness is a separate requirement from having same-device matched evidence.\n'
    )
    return manifest


def main():
    ap=argparse.ArgumentParser(description='Evidence inventory for real IBM repetition-code archive; no synthetic data')
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--backend',choices=BACKENDS,required=True)
    ap.add_argument('--max-age-days',type=int,default=365)
    ap.add_argument('--max-jobs',type=int)
    ap.add_argument('--output-dir',type=Path,required=True)
    args=ap.parse_args()
    report=write_inventory(args.archive,args.backend,args.output_dir,
                           max_age_days=args.max_age_days,max_jobs=args.max_jobs)
    print(f"Indexed {report['actual_records_inspected']} actual paired QEC jobs; "
          f"{report['records_passing_freshness_cutoff']} recent. "
          'NO device logical-error prediction validated.')

if __name__=='__main__':main()
