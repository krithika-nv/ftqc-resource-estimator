"""Audit a separately produced, *matched* set of simulated and hardware logical-error rates.

This module does NOT synthesize measurements or infer a decoder result from a
calibration; the user must supply independently computed, protocol-matched
held-out hardware counts and simulation predictions with SHA provenance.
"""
from __future__ import annotations
import argparse
import csv
from hashlib import sha256
import json
# no extra dependencies
from pathlib import Path
from .reliability import wilson


def audit(predictions:Path, inventory:Path, output:Path)->dict:
    with inventory.open(newline='') as f:
        catalog={r['snapshot_id']:r for r in csv.DictReader(f)}
    if not catalog:raise ValueError('no paired experimental inventory')
    manifest_path=inventory.parent/'EVIDENCE_MANIFEST.json'
    if not manifest_path.exists():raise ValueError('paired evidence manifest required')
    manifest=json.loads(manifest_path.read_text())
    split=manifest.get('heldout_plan',{})
    if split.get('status')!='SPLIT_PLAN_ONLY_NO_PREDICTIONS' or not split.get('holdout'):
        raise ValueError('no independent chronological holdout established')
    approved=set(split['holdout'])
    with predictions.open(newline='') as f:
        rows=list(csv.DictReader(f))
    if not rows:raise ValueError('empty hardware prediction comparison')
    evaluated=[];seen=set()
    for row in rows:
        key=row.get('snapshot_id')
        if key not in catalog or key in seen:raise ValueError('unpaired or duplicate snapshot')
        seen.add(key)
        meta=catalog[key]
        for f in ['backend','code_family','basis','calibration_sha256']:
            if row.get(f)!=meta[f]:raise ValueError('protocol or calibration mismatch: '+f)
        for f in ('distance','rounds'):
            if int(row[f])!=int(meta[f]):raise ValueError('protocol mismatch: '+f)
        if not row.get('model_source_sha256') or len(row['model_source_sha256'])!=64 or any(c not in '0123456789abcdef' for c in row['model_source_sha256'].lower()):
            raise ValueError('missing independent model provenance digest')
        if row.get('observed_source_sha256')!=meta['bitstrings_sha256']:
            raise ValueError('hardware outcome digest mismatch')
        if row.get('evidence_split')!='holdout' or key not in approved:
            raise ValueError('only independent held-out evaluation permitted')
        shots=int(row['observed_trials']);fails=int(row['observed_failures']);prediction=float(row['predicted_failure'])
        if not(0<=fails<=shots and shots>0 and 0<=prediction<=1):
            raise ValueError('invalid probability/count')
        # Statistical interval around observed hardware *counts*; note not hardware predictive coverage.
        interval=wilson(fails,shots);lo,hi=interval.lower,interval.upper
        observed=fails/shots
        evaluated.append({'snapshot_id':key,'observed':observed,'predicted':prediction,
                          'absolute_error':abs(observed-prediction),'bias':prediction-observed,
                          'wilson_95_low':lo,'wilson_95_high':hi,
                          'predicted_within_observation_wilson_interval':lo<=prediction<=hi,
                          'observed_trials':shots,'observed_failures':fails})
    # Bare per-snapshot summary, not a claim of statistically independent observations.
    mae=sum(x['absolute_error'] for x in evaluated)/len(evaluated)
    b=sum(x['bias'] for x in evaluated)/len(evaluated)
    result={'evidence_status':'HELDOUT_COMPARISON_FROM_USER_PROVIDED_REAL_HARDWARE_COUNTS_AND_MODEL',
            'evaluated':len(evaluated),'mean_absolute_error':mae,'mean_bias':b,
            'prediction_csv_sha256':sha256(predictions.read_bytes()).hexdigest(),
            'inventory_csv_sha256':sha256(inventory.read_bytes()).hexdigest(),
            'caveats':['source data and decoding provenance must be independently reviewed',
                       'no causal hardware calibration established',
                       'Wilson intervals are marginal, not simultaneous coverage',
                       'do not extrapolate repetition-code results to surface-code logical gates']}
    output.mkdir(parents=True,exist_ok=True)
    (output/'MATCHED_PREDICTION_AUDIT.json').write_text(json.dumps({'summary':result,'rows':evaluated},indent=2)+'\n')
    return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description='Compare *independently generated* held-out hardware counts and matched model predictions')
    a.add_argument('--predictions',type=Path,required=True)
    a.add_argument('--evidence-inventory',type=Path,required=True)
    a.add_argument('--output-dir',type=Path,required=True)
    v=a.parse_args();print(json.dumps(audit(v.predictions,v.evidence_inventory,v.output_dir),indent=2))
