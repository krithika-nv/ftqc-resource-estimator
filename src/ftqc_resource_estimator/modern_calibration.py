"""Versioned, fail-closed importer for *dated real device calibrations*.

A dated calibration record is a measured hardware CHARACTERIZATION, not a
measurement of logical failure. Output contains no inferred device-specific
QEC failure prediction. 2026 Zenodo data remain external downloads; never
substitute a fabricated record on failed download or parse.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
import tarfile

from .platform_boundaries import backend_family, check_calibration_use

SOURCE = 'https://doi.org/10.5281/zenodo.20768087'


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing device calibration timestamp; cannot establish freshness')
    try:
        t = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except ValueError as e:
        raise ValueError(f'invalid calibration timestamp: {value!r}') from e
    if t.tzinfo is None:
        raise ValueError('calibration timestamp has no UTC offset: cannot verify freshness')
    return t.astimezone(timezone.utc)


def check_age(measured: datetime, *, as_of: datetime | None = None, max_age_days: int = 180) -> float:
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('as_of needs timezone')
    if max_age_days <= 0:
        raise ValueError('max_age_days must be positive')
    days = (now - measured).total_seconds() / 86400
    if days < -1: raise ValueError('calibration timestamp is in the future')
    if days > max_age_days: raise ValueError(f'calibration stale: {days:.1f} days > {max_age_days}')
    return max(0, days)


def value_number(value, name: str, *, positive=False, probability=False):
    if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite number')
    if (positive and value <= 0) or (probability and not 0 <= value <= 1):
        raise ValueError(f'invalid {name} value {value}')
    return float(value)


def _convert(entry:dict, target:str):
    val=value_number(entry['value'], target, positive=target in ('T1','T2','readout_length'), probability=target in ('readout_error','prob_meas0_prep1','prob_meas1_prep0','gate_error'))
    unit=entry.get('unit', '')
    if target in ('T1','T2','readout_length','gate_length'):
        units={'s':1e6, 'us':1, 'µs':1, 'ns':.001}
        if unit not in units:raise ValueError(f'unsupported {target} unit {unit!r}')
        return val*units[unit]
    if unit not in ('','unitless',None):raise ValueError(f'unexpected {target} unit {unit!r}')
    return val


def _named_parameter(items, name):
    if isinstance(items, dict):
        v=items.get(name)
        if isinstance(v,dict):return v
        if v is None:return None
        # A bare scalar has unknown physical units: reject for times.
        return {'name':name, 'value':v, 'unit': ''}
    if not isinstance(items,list):return None
    vals=[v for v in items if isinstance(v,dict) and v.get('name')==name]
    if len(vals)>1: raise ValueError(f'duplicate {name}')
    return vals[0] if vals else None


def _extract_properties(raw:dict):
    if not isinstance(raw,dict):raise ValueError('calibration JSON must be an object')
    # Dataset documentation says backend_properties; different exporter wrappers
    # exist. Do not infer a layout not explicitly recognized here.
    for k in ('backend_properties','properties','calibration'):
        if isinstance(raw.get(k),dict) and 'qubits' in raw[k]: return raw[k]
    if 'qubits' in raw: return raw
    raise ValueError('unrecognized calibration JSON: expected qubits array or backend_properties wrapper')


def normalize_backend_properties(raw:dict, *, backend_override:str | None = None) -> dict:
    props=_extract_properties(raw)
    ts=props.get('last_update_date') or raw.get('last_update_date')
    when=parse_timestamp(ts)
    backend=props.get('backend_name') or raw.get('backend_name') or backend_override
    if not isinstance(backend,str) or not re.fullmatch(r'ibm(q)?_[a-z0-9_]+',backend):
        raise ValueError('IBM device ID missing or inconsistent')
    if backend_override and backend != backend_override:
        raise ValueError('device mismatch between dataset index and calibration')
    if not isinstance(props['qubits'],list) or not props['qubits']:
        raise ValueError('missing per-qubit hardware calibration')
    qubits=[]
    for index, entries in enumerate(props['qubits']):
        item={'qubit':index}
        for key, dest in [('T1','t1_us'),('T2','t2_echo_us'),('readout_error','readout_error'),('readout_length','readout_length_us'),('prob_meas0_prep1','prob_meas0_prep1'),('prob_meas1_prep0','prob_meas1_prep0')]:
            entry=_named_parameter(entries,key)
            if entry is not None:item[dest]=_convert(entry,key)
        if not all(k in item for k in ('t1_us','t2_echo_us','readout_error')):
            raise ValueError(f'qubit {index} missing T1 / T2 / readout_error; refuse incomplete device')
        if item['t2_echo_us']>2.01*item['t1_us']:
            raise ValueError(f'qubit {index} T2 exceeds 2*T1 beyond rounding')
        qubits.append(item)
    gates=[]
    for g in props.get('gates',[]):
        if not isinstance(g,dict):continue
        edge=g.get('qubits')
        if not isinstance(edge,list) or len(edge)!=2:continue
        params=g.get('parameters',[])
        e=_named_parameter(params,'gate_error')
        l=_named_parameter(params,'gate_length')
        if e is None:continue
        if any(type(q)!=int or q<0 or q>=len(qubits) for q in edge):
            raise ValueError('invalid two-qubit gate index')
        row={'gate':g.get('gate'),'qubits':edge,'gate_error':_convert(e,'gate_error')}
        if l is not None:row['gate_length_us']=_convert(l,'gate_length')
        gates.append(row)
    return {'backend_name':backend,'hardware_family':backend_family(backend),
            'calibration_timestamp_utc':when.isoformat(),
            'qubits':qubits,'two_qubit_gates':gates,
            'data_classification':'MEASURED_DEVICE_CHARACTERIZATION_ONLY',
            'free_idle_ramsey_t2star_measured':False,
            'logical_error_hardware_prediction_validated':False}


def _read_member(archive:tarfile.TarFile, path:str, *, max_bytes=8_000_000)->bytes:
    member=archive.getmember(path)
    if not member.isfile() or member.size>max_bytes:raise ValueError('archive member too large or nonfile')
    with archive.extractfile(member) as fd:return fd.read()


def import_zenodo_archive(path: Path, backend: str, *, max_age_days=365,
                          as_of: datetime | None = None, max_snapshots: int | None = None):
    """Select only dated, eligible records; prefer newest, never silently relax recency.

    A published archive can include old measurements. Inspect *all* its matched
    calibration snapshots before enforcing a freshness-based selection. Preserve
    a count of excluded stale records in every returned entry's provenance.
    """
    if backend not in ('ibm_fez', 'ibm_kingston', 'ibm_pittsburgh'):
        raise ValueError('backend must be a published Zenodo 2026 device')
    if max_snapshots is not None and max_snapshots <= 0:
        raise ValueError('max_snapshots must be positive')
    if max_age_days <= 0:
        raise ValueError('max_age_days must be positive')
    now = as_of or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('as_of needs timezone')
    candidates = []
    stale = []
    with tarfile.open(path, 'r:gz') as tar:
        names = {m.name for m in tar.getmembers() if m.isfile()}
        calibrations = sorted(n for n in names
                              if n.endswith('/calibration.json') and backend in n.split('/'))
        if not calibrations:
            raise ValueError('no calibration.json files found for requested device')
        for name in calibrations:
            info_name = name[:-len('calibration.json')] + 'info.json'
            if info_name not in names:
                raise ValueError('missing paired info.json for ' + name)
            info = json.loads(_read_member(tar, info_name))
            if info.get('backend', info.get('device')) not in (None, backend):
                raise ValueError('info.json device mismatch')
            raw = _read_member(tar, name)
            model = normalize_backend_properties(json.loads(raw), backend_override=backend)
            measured = parse_timestamp(model['calibration_timestamp_utc'])
            age_days = (now - measured).total_seconds() / 86400
            if age_days < -1:
                raise ValueError(f'future calibration timestamp: {name}')
            if age_days > max_age_days:
                stale.append((measured, name, age_days))
                continue
            candidates.append((measured, {'path': name, 'info_path': info_name,
                'backend': backend, 'distance': info.get('d', info.get('distance')),
                'rounds': info.get('rounds'), 'basis': info.get('basis'),
                'age_days_at_import': round(max(0, age_days), 2),
                'raw_calibration_sha256': sha256(raw).hexdigest(),
                'normalized': model, 'logical_hardware_shots_ingested': False}))
    if not candidates:
        if stale:
            newest, _, youngest_age = max(stale, key=lambda item: item[0])
            raise ValueError(
                f'no {backend} calibration meets {max_age_days}-day cutoff; '
                f'newest archive measurement was {newest.isoformat()} '
                f'({youngest_age:.1f} days old). '
                'The dataset publication date is not the calibration date. '
                'Use a newer authenticated IBM backend snapshot for current work; '
                'do not label this archived data as current.')
        raise ValueError('archive contains no valid dated calibration records')
    candidates.sort(key=lambda pair: (pair[0], pair[1]['path']), reverse=True)
    selected = candidates[:max_snapshots] if max_snapshots is not None else candidates
    provenance = {
        'archive_matching_snapshots': len(candidates) + len(stale),
        'excluded_stale_snapshots': len(stale),
        'eligible_snapshots': len(candidates),
        'selected_snapshots': len(selected),
        'newest_archive_calibration_utc': max(
            [date for date, _ in candidates] + [date for date, _, _ in stale]
        ).isoformat(),
        'selection_policy': 'newest eligible first, by actual calibration timestamp',
    }
    return [{**entry, 'import_selection': provenance} for _, entry in selected]


def publish_import(data:list, output:Path, *, source:str, raw_sha:str, criteria:dict):
    if not data:raise ValueError('zero normalized calibrations')
    output.mkdir(parents=True,exist_ok=True)
    if len({entry['backend'] for entry in data}) != 1 or len({entry['normalized']['backend_name'] for entry in data}) != 1:
        raise ValueError('mixed-device calibration export rejected; select a single backend')
    scopes=[check_calibration_use(entry['normalized'], target_family='superconducting',
                purpose='characterization') for entry in data]
    # The export is intentionally platform-specific, not a generic FTQC calibration.
    rows=[]
    for i,entry in enumerate(data):
        for q in entry['normalized']['qubits']:
            rows.append({'snapshot':i,'backend':entry['backend'],
                'timestamp_utc':entry['normalized']['calibration_timestamp_utc'],
                'qubit':q['qubit'],'t1_us':q['t1_us'],'t2_echo_us':q['t2_echo_us'],
                'readout_error':q['readout_error'],
                'readout_length_us':q.get('readout_length_us','')})
    with (output/'measured_qubits.csv').open('w',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    manifest={'source':source,'source_sha256':raw_sha,'criteria':criteria,
       'snapshot_count':len(data),'measured_qubit_rows':len(rows),
       'newest_calibration_timestamp_utc':max(d['normalized']['calibration_timestamp_utc'] for d in data),
       'oldest_calibration_timestamp_utc':min(d['normalized']['calibration_timestamp_utc'] for d in data),
       'hardware_logical_error_validation_completed':False,
       'has_matched_hardware_qec_shots':False,
       'is_current_hardware_prediction':False,
       'archive_selection':data[0].get('import_selection', {}),
       'note':'Source measured characterization only; separate held-out hardware bitstrings required.'}
    (output/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (output/'snapshots.json').write_text(json.dumps(data,indent=2)+'\n')
    (output/'ADAPTER_SCOPE.json').write_text(json.dumps({
       'adapter_family':'superconducting', 'source_device':data[0]['backend'],
       'source_kind':'measured_device_characterization',
       'snapshot_scopes':scopes,
       'status':'NOT_HARDWARE_VALIDATED',
       'cross_platform_reuse_prohibited':True,
       'logical_error_hardware_prediction_validated':False
    },indent=2)+'\n')
    (output/'IMPORT_REPORT.md').write_text('# Dated IBM hardware calibration import\n\n'
       +f"- Device: `{data[0]['backend']}`; **{len(data)} real calibration snapshots**, {len(rows)} per-qubit records.\n"
       +f"- Calibration timestamps: {manifest['oldest_calibration_timestamp_utc']} to {manifest['newest_calibration_timestamp_utc']}.\n"
       +f"- Source: {source}; SHA-256: `{raw_sha}`.\n"
       +'\nArchive selection: '+json.dumps(manifest['archive_selection'],sort_keys=True)+'\n\n'
       +'**Hardware boundary:** **superconducting IBM only**, not photonic or trapped-ion hardware. '
       +'Not validated device logical-failure prediction. Neither the QEC bitstrings nor a matched decoder comparison is ingested in this step. '
       +'Hahn-echo T2 cannot substitute for Ramsey T2*. Readout concurrency and correlated error rates remain unknown.\n')
    return manifest


def main():
    ap=argparse.ArgumentParser(description='Import dated public IBM calibration records, no hypothetical substitution')
    ap.add_argument('--zenodo-archive',type=Path)
    ap.add_argument('--ibm-properties',type=Path,help='authenticated IBM JSON previously exported locally')
    ap.add_argument('--backend',required=True)
    ap.add_argument('--max-age-days',type=int,default=365)
    ap.add_argument('--max-snapshots',type=int)
    ap.add_argument('--output-dir',type=Path,default=Path('outputs/modern_calibration'))
    args=ap.parse_args()
    if bool(args.zenodo_archive)==bool(args.ibm_properties):ap.error('choose exactly one input')
    if args.zenodo_archive:
        path=args.zenodo_archive
        entries=import_zenodo_archive(path,args.backend,max_age_days=args.max_age_days,max_snapshots=args.max_snapshots)
        source=SOURCE
    else:
        path=args.ibm_properties
        raw=path.read_bytes(); model=normalize_backend_properties(json.loads(raw),backend_override=args.backend)
        age=check_age(parse_timestamp(model['calibration_timestamp_utc']),max_age_days=args.max_age_days)
        entries=[{'path':str(path),'backend':args.backend,'age_days_at_import':age,
                  'raw_calibration_sha256':sha256(raw).hexdigest(),'normalized':model,
                  'logical_hardware_shots_ingested':False}]
        source='IBM Quantum authenticated backend properties, user-exported'
    rawsha=sha256(path.read_bytes()).hexdigest()
    manifest=publish_import(entries,args.output_dir,source=source,raw_sha=rawsha,
               criteria={'backend':args.backend,'max_age_days':args.max_age_days})
    print(f"IMPORTED measured calibrations: {manifest['snapshot_count']} snapshot(s), {manifest['measured_qubit_rows']} qubit records")
    print(f"Actual calibration timestamp newest: {manifest['newest_calibration_timestamp_utc']}")
    print('NOT a validated QEC hardware logical-error prediction')

if __name__=='__main__':main()
