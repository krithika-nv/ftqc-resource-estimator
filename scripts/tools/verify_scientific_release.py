"""Refuse analysis-release claims without an actual reproducible Stim/PyMatching run.

This is a same-environment integrity check, not proof that the chosen noise model
corresponds to a physical device, that p-values are calibrated, or that a
nominal interval provides simultaneous coverage for all comparisons.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from ftqc_resource_estimator.stim_memory import SCHEMA, replay_audit
from ftqc_resource_estimator.memory_analysis import validate_stim_manifest


def verify(manifest_file:Path, report_file:Path, output_file:Path)->dict:
    try:
        import stim
        import pymatching
        import numpy
    except ImportError as exc:
        raise RuntimeError('REAL SCIENTIFIC BACKEND MISSING: no validated results generated') from exc
    if not manifest_file.is_file() or not report_file.is_file():
        raise RuntimeError('REAL OBSERVATION/ANALYSIS FILES MISSING: do not publish claims of a successful run')
    raw=manifest_file.read_bytes()
    obj=json.loads(raw)
    if obj.get('schema')!=SCHEMA:
        raise RuntimeError('unexpected experiment schema')
    if obj.get('software',{}).get('stim') != stim.__version__ or obj.get('software',{}).get('pymatching') != pymatching.__version__:
        raise RuntimeError('installed versions do not match observation manifest')
    observations=obj.get('observations',[])
    if len(observations)!=9 or len({(x['distance'],x['physical_error']) for x in observations}) != 9:
        raise RuntimeError('expected 3 distances x 3 physical errors from the recorded protocol')
    for p in (0, .003, .005):
        validate_stim_manifest(obj,basis='X',physical_error=p,rounds=9,distances=(3,5,7))
    if {r['shots'] for r in observations}!={20000}:
        raise RuntimeError('the registered protocol requires exactly 20,000 shots per setting')
    if any(r['failures'] for r in observations if r['physical_error']==0):
        raise RuntimeError('noiseless control failed')
    report=report_file.read_text(encoding='utf-8')
    if 'Surface-code MEMORY study' not in report or 'Simulator provenance' not in report:
        raise RuntimeError('missing or unrecognized matched comparison report')
    replay_audit(obj)
    verified={
        'status':'PASSED real simulator execution and same-environment replay',
        'verified_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'stim_version':stim.__version__,
        'pymatching_version':pymatching.__version__,
        'numpy_version':numpy.__version__,
        'observation_sha256':sha256(raw).hexdigest(),
        'observations':len(observations),
        'total_shots':sum(r['shots'] for r in observations),
        'noise_profile':obj['methods']['noise_profile'],
        'experiment':'rotated surface-code MEMORY (9 fixed syndrome rounds)',
        'scope':'not a hardware-calibrated or logical-gate benchmark',
    }
    output_file.parent.mkdir(parents=True,exist_ok=True)
    output_file.write_text(json.dumps(verified,indent=2)+'\n',encoding='utf-8')
    return verified


if __name__=='__main__':
    try:
        outcome=verify(Path('outputs/stim_memory/observations.json'),Path('outputs/stim_memory/analysis/MEMORY_REPORT.md'),
                       Path('outputs/stim_memory/VALIDATED_RUN.json'))
    except Exception as exc:
        print(f'ANALYSIS RELEASE GATE FAILED: {exc}',file=sys.stderr)
        raise SystemExit(1)
    print('REAL SCIENTIFIC RELEASE GATE PASSED:',outcome['total_shots'],'actual simulator trials')
