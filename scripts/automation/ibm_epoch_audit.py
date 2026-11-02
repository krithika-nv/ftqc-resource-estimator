#!/usr/bin/env python3
"""Audit *actual* calibration snapshots and decoded/excluded job coverage.

A different calibration timestamp is NOT necessarily a distinct experiment
execution time. No statistical holdout is invented from same-epoch shot IDs.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib,json,tarfile
from pathlib import Path
from ftqc_resource_estimator.modern_calibration import normalize_backend_properties


def audit(archive:Path, decode_summary:Path|None=None)->dict:
    status={}
    if decode_summary and decode_summary.is_file():
        summary=json.loads(decode_summary.read_text())
        status.update({j['snapshot_id'].rstrip('/'): 'decoded' for j in summary.get('jobs',[])})
        status.update({j['snapshot_id'].rstrip('/'): 'excluded' for j in summary.get('skipped_jobs',[])})
    # Stream once through compressed TAR; random extraction repeatedly
    # decompresses hundreds of MB of shots and is needlessly quadratic.
    fragments=defaultdict(dict)
    with tarfile.open(archive,'r|gz') as tf:
        for member in tf:
            if not member.isfile() or not member.name.endswith(('/info.json','/calibration.json')):
                continue
            if member.size>8_000_000:raise ValueError('unexpectedly large metadata member')
            prefix,name=member.name.rsplit('/',1)
            b=tf.extractfile(member).read()
            fragments[prefix][name]=b
    rows=[]
    for prefix,record in sorted(fragments.items()):
        if set(record)!={'info.json','calibration.json'}:raise ValueError('incomplete paired calibration: '+prefix)
        info=json.loads(record['info.json']);cbytes=record['calibration.json']
        backend=info.get('backend')
        normalized=normalize_backend_properties(json.loads(cbytes),backend_override=backend)
        rows.append({'snapshot_id':prefix,'backend':backend,'distance':info.get('d'),
                     'rounds':info.get('rounds'),'basis':info.get('basis'),
                     'calibration_utc':normalized['calibration_timestamp_utc'],
                     'calibration_sha256':hashlib.sha256(cbytes).hexdigest(),
                     'decoding_status':status.get(prefix,'unreviewed')})
    epochs=Counter((r['backend'],r['calibration_utc']) for r in rows)
    # Identify like-for-like protocol pairs before any model fitting.
    by_protocol=defaultdict(list)
    for r in rows:by_protocol[(r['backend'],r['distance'],r['rounds'],r['basis'])].append(r)
    candidates=[]
    for key,records in sorted(by_protocol.items()):
        distinct=sorted({r['calibration_utc'] for r in records})
        if len(distinct)>1:
            candidates.append({'backend':key[0],'distance':key[1],'rounds':key[2],'basis':key[3],
                               'calibration_times':distinct,
                               'jobs':[{'snapshot_id':r['snapshot_id'],'calibration_utc':r['calibration_utc'],
                                        'decoding_status':r['decoding_status']} for r in records],
                               'all_epochs_decoded':all(any(r['decoding_status']=='decoded' and r['calibration_utc']==e
                                                          for r in records) for e in distinct)})
    return {'schema':'ftqc.ibm.calibration-coverage.v1','source_archive':archive.name,
            'source_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'job_count':len(rows),
            'epochs':[{'backend':backend,'calibration_utc':epoch,'jobs':count}
                      for (backend,epoch),count in sorted(epochs.items())],
            'matched_protocol_candidate_pairs':candidates,
            'decoded_job_count':sum(r['decoding_status']=='decoded' for r in rows),
            'excluded_job_count':sum(r['decoding_status']=='excluded' for r in rows),
            'caveat':'Calibration timestamps must not be used as job execution timestamps without source audit. A matched pair with excluded shots does not establish an independent predictive holdout; distinct processors cannot be treated as one hardware calibration.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,default=Path('data/public_calibrations/2026/ibm_fez.tar.gz'))
    p.add_argument('--decode-summary',type=Path,default=Path('outputs/external_validation/ibm_raw_decode_summary.json'))
    p.add_argument('--output',type=Path,default=Path('outputs/external_validation/IBM_CALIBRATION_EPOCHS.json'))
    a=p.parse_args()
    result=audit(a.archive,a.decode_summary)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'job_count':result['job_count'],'epochs':result['epochs'],
                      'candidate_pairs':result['matched_protocol_candidate_pairs'],
                      'decoded_jobs':result['decoded_job_count']},indent=2))
if __name__=='__main__':main()
