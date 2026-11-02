"""Fail-closed evidence intake for *future* same-device idle-noise calibration.

No values here are supplied by imagination; this module never infers T2_Ramsey
from T2_CPMG or T2_echo. Missing controls imply NOT_DEVICE_CALIBRATED.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

REQUIRED = {
    'device_identifier': 'ID of the actual quantum processor for all parameters',
    'calibration_timestamp_utc': 'Timestamp for the relevant experimental calibration',
    'primary_source_url': 'Primary source or public device metadata',
    'coherence_method': 'Must be Ramsey/free induction for an unprotected idle',
    't1_us': 'Measured T1 for the same data qubit set',
    't2_ramsey_us': 'Measured free-induction Ramsey T2* for the same data qubit set',
    'readout_short_us': 'Measured readout-slot time for this processor and schedule',
    'readout_standard_us': 'Measured standard readout-slot time for this processor and schedule',
    'concurrent_readout_capacity': 'Measured actual concurrent readout capacity under the chosen schedule',
    'schedule_source_url': 'Proof of measurement group/parallel readout capacity',
    'idle_placement': 'Timing location of the idle interval in actual syndrome circuit',
    'noise_correlation_source': 'Measurements or detector data testing correlated phase/ZZ error',
}
NUMERIC = {'t1_us','t2_ramsey_us','readout_short_us','readout_standard_us','concurrent_readout_capacity'}


def audit_device_calibration(record:dict)->dict:
    problems=[]
    for key,description in REQUIRED.items():
        value=record.get(key)
        if value is None or value=='' or value==[]:
            problems.append(f'MISSING {key}: {description}')
            continue
        if key in NUMERIC:
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
                problems.append(f'INVALID {key}: expected positive finite measured number')
            if key=='concurrent_readout_capacity' and (type(value) is not int or value<=0):
                problems.append('INVALID concurrent_readout_capacity: expected a measured integer')
    if record.get('coherence_method') not in (None,'ramsey_free_induction'):
        problems.append('INVALID coherence_method: CPMG/Hahn echo is not a Ramsey free-idle measurement')
    for key in ('primary_source_url','schedule_source_url','noise_correlation_source'):
        v=record.get(key)
        if v is not None and (not isinstance(v,str) or not v.startswith(('https://','http://'))):
            problems.append(f'INVALID {key}: public primary URL required')
    if ('readout_standard_us' in record and 'readout_short_us' in record and
        isinstance(record['readout_standard_us'],(int,float)) and
        isinstance(record['readout_short_us'],(int,float)) and
        record['readout_standard_us']<=record['readout_short_us']):
        problems.append('INVALID durations: standard must exceed short readout')
    if record.get('device_identifier') and record.get('parameter_device_identifier') and (record['device_identifier']!=record['parameter_device_identifier']):
        problems.append('MIXED_DEVICES: measurements must refer to the same device')
    if record.get('device_identifier') and record.get('schedule_device_identifier') and (record['device_identifier']!=record['schedule_device_identifier']):
        problems.append('MIXED_DEVICES: schedule must refer to the same device')
    # Even complete metadata here does NOT verify the authenticity of supplied records.
    return {'calibration_metadata_complete':not problems,
            'actual_device_calibration_verified':False,
            'missing_or_invalid':problems,
            'interpretation': ('Metadata completeness only; authenticity, timestamp matching, pulse-level '
                               'scheduling, joint noise, qubit distribution, and experimental validation '
                               'must be independently audited before claiming calibrated hardware predictions.')}


def main():
    parser=argparse.ArgumentParser(description='Check published/measured evidence needed for a genuinely calibrated idle study')
    parser.add_argument('--input',type=Path,default=Path('examples/device_calibration_template.json'))
    args=parser.parse_args()
    print(json.dumps(audit_device_calibration(json.loads(args.input.read_text())),indent=2))

if __name__=='__main__':main()
