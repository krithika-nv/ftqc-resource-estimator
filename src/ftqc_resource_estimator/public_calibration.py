"""Import IBM's *historical measured backend-properties* snapshots.

The bundled ibmq_manila subset is a transparently cited transcription of
selected 2024 backend fields, not a fake data fixture or a modern calibration.
The separate `--raw` path imports the complete upstream JSON *if the original*
was downloaded, with a SHA-256 that binds the output to exact source bytes.

Physical predictions are explicitly out of scope: backend T2 is echo-based,
readout concurrency and Ramsey T2* are absent, and 5 physical qubits do not
support a rotated surface-code distance-3 memory circuit (17 sites in this
repository's convention). This module never supplies invented missing fields.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median

CURATED_URL = ('https://raw.githubusercontent.com/Qiskit/qiskit-ibm-runtime/main/'
               'qiskit_ibm_runtime/fake_provider/backends/manila/props_manila.json')
CURATED_DATE = '2024-05-27T15:27:23-03:00'


def _float(x, name, *, positive=False, upper=None):
    if isinstance(x, bool) or not isinstance(x, (int,float)) or not math.isfinite(x):
        raise ValueError(f'{name} must be a finite number')
    if positive and x <= 0 or upper is not None and not 0 <= x <= upper:
        raise ValueError(f'{name} outside permitted range')
    return float(x)


def _when(x):
    if not isinstance(x, str):
        raise ValueError('missing dated hardware calibration')
    try: t = datetime.fromisoformat(x)
    except ValueError as e: raise ValueError('invalid calibration ISO timestamp') from e
    if t.tzinfo is None:
        raise ValueError('calibration timestamp must include timezone')
    return x


def _measure(q, name, unit):
    matches = [m for m in q if m.get('name') == name]
    if len(matches)!=1 or matches[0].get('unit') != unit:
        raise ValueError(f'missing/duplicate {name} or unexpected unit {unit}')
    return _float(matches[0]['value'], name, positive=name in ('T1','T2','readout_length'),
                  upper=1 if name in ('readout_error','prob_meas0_prep1','prob_meas1_prep0') else None)


def normalize_full_ibm_properties(raw:dict)->dict:
    """Parse original Qiskit `props_*.json`; no computed parameter is measured."""
    if not isinstance(raw,dict) or not isinstance(raw.get('qubits'),list):
        raise ValueError('expected IBM backend-properties JSON with qubits list')
    qubits=[]
    for i, row in enumerate(raw['qubits']):
        qubits.append({'qubit':i,'t1_us':_measure(row,'T1','us'),
                       't2_echo_us':_measure(row,'T2','us'),
                       'readout_error':_measure(row,'readout_error',''),
                       'prob_meas0_prep1':_measure(row,'prob_meas0_prep1',''),
                       'prob_meas1_prep0':_measure(row,'prob_meas1_prep0',''),
                       'readout_length_ns':_measure(row,'readout_length','ns')})
    gates=[]
    for row in raw.get('gates',[]):
        if row.get('gate') != 'cx' or len(row.get('qubits',[])) != 2:
            continue
        params=row.get('parameters',[])
        gates.append({'gate':'cx','qubits':row['qubits'],
                      'gate_error':_measure(params,'gate_error',''),
                      'gate_length_ns':_measure(params,'gate_length','ns')})
    obj={'schema':'ftqc.ibm_backend_properties_curated_subset.v1',
         'data_classification':'REAL_HISTORICAL_HARDWARE_CALIBRATION__DERIVED_FROM_ORIGINAL',
         'backend_name':raw.get('backend_name'), 'backend_version':raw.get('backend_version'),
         'last_update_date':raw.get('last_update_date'),
         'upstream_raw_url':None,'upstream_browse_url':None,
         'extraction_method':'Parsed complete original Qiskit props JSON; source SHA stored in provenance',
         'measurement_type_note':'T2 reported by IBM backend properties is Hahn-echo, not Ramsey T2-star',
         'qubits':qubits,'two_qubit_gates':gates}
    validate_calibration(obj)
    return obj


def validate_calibration(obj):
    if obj.get('schema') != 'ftqc.ibm_backend_properties_curated_subset.v1':
        raise ValueError('unsupported calibration schema')
    _when(obj.get('last_update_date'))
    name = obj.get('backend_name')
    if not isinstance(name,str) or not name.startswith(('ibmq_','ibm_')):
        raise ValueError('real IBM backend name required')
    qlist=obj.get('qubits',[])
    if not isinstance(qlist,list) or not qlist:
        raise ValueError('empty qubit calibration')
    if [x.get('qubit') for x in qlist] != list(range(len(qlist))):
        raise ValueError('qubits must be uniquely ordered and indexed')
    for q in qlist:
        for k in ('t1_us','t2_echo_us','readout_length_ns'):
            _float(q.get(k),k,positive=True)
        if q['t2_echo_us'] > 2*q['t1_us'] * (1+1e-12):
            raise ValueError('unphysical relaxation/dephasing ratio')
        for k in ('readout_error','prob_meas0_prep1','prob_meas1_prep0'):
            _float(q.get(k),k,upper=1)
        avg=(q['prob_meas0_prep1']+q['prob_meas1_prep0'])/2
        if not math.isclose(avg,q['readout_error'],abs_tol=5e-5):
            raise ValueError('readout error inconsistent with assignment calibration')
    gates=obj.get('two_qubit_gates',[])
    if not isinstance(gates,list) or not gates:
        raise ValueError('no two-qubit gate calibrations')
    seen=set()
    for gate in gates:
        edge=tuple(gate.get('qubits',[]))
        if (gate.get('gate')!='cx' or len(edge)!=2 or len(set(edge))!=2 or
            any(type(i) is not int or i<0 or i>=len(qlist) for i in edge) or edge in seen):
            raise ValueError('invalid or duplicated directed gate edge')
        seen.add(edge)
        _float(gate.get('gate_error'),'cx gate_error',upper=1)
        _float(gate.get('gate_length_ns'),'cx gate_length_ns',positive=True)
    return obj


def project_calibration(obj):
    """Measured inputs => *approximated* circuit noise; missing T2* remains unknown.

    A repetition-code d3 layout needs five alternating sites; this import
    intentionally restricts the demonstrator to a five-qubit connected path.
    These estimates are not an IBM-specific pulse-level noise model.
    """
    validate_calibration(obj)
    qubits=obj['qubits']; gates=obj['two_qubit_gates']
    if len(qubits)!=5:
        raise ValueError('demonstration projection requires exactly five measured qubits')
    undirected={frozenset(g['qubits']) for g in gates}
    if not all(frozenset((i,i+1)) in undirected for i in range(4)):
        raise ValueError('this projection requires a calibrated 5-site path')
    median_readout_ns=median(q['readout_length_ns'] for q in qubits)
    # A relaxation-only Pauli-twirl proxy for an idle of the published readout
    # length: pX=pY=(1-exp(-t/T1))/4, phase pZ not identifiable from T2_echo.
    t_us=median_readout_ns / 1000
    per_qubit_relaxation=[(1-math.exp(-t_us/q['t1_us']))/4 for q in qubits]
    # Stim's depolarization parameter is an *illustrative aggregate* for
    # gate errors. RB error and after-Clifford depolarization are not equal.
    proxy={'backend_name':obj['backend_name'],
           'snapshot_timestamp':obj['last_update_date'],
           'physical_qubits':len(qubits),
           'median_t1_us_measured':median(q['t1_us'] for q in qubits),
           'median_t2_echo_us_measured_not_free_idle':median(q['t2_echo_us'] for q in qubits),
           'median_readout_duration_us_measured':t_us,
           'median_readout_error_measured':median(q['readout_error'] for q in qubits),
           'mean_readout_error_measured':sum(q['readout_error'] for q in qubits)/len(qubits),
           'mean_cx_error_measured':sum(g['gate_error'] for g in gates)/len(gates),
           'max_cx_error_measured':max(g['gate_error'] for g in gates),
           'relaxation_only_pX_per_qubit_approx':per_qubit_relaxation,
           'relaxation_only_pY_per_qubit_approx':per_qubit_relaxation,
           't2_ramsey_us':'NOT_MEASURED_IN_THIS_SNAPSHOT',
           'controller_parallelism':'NOT_MEASURED_IN_THIS_SNAPSHOT',
           'idling_noise_inference':'T1_only_Pauli_twirled_relaxation_proxy__missing_free_idle_dephasing',
           'surface_code_hardware_prediction_supported':False,
           'five_qubit_repetition_memory_demo_only':True,
           'stim_parameters_ILLUSTRATIVE':{
               'distance':3,'rounds':3,
               'after_clifford_depolarization':median(g['gate_error'] for g in gates),
               'before_round_data_depolarization': min(1.,1.5*median(per_qubit_relaxation)),
               'before_measure_flip_probability':median(q['readout_error'] for q in qubits),
               'after_reset_flip_probability':0.0,
           },
           'limitations':[
             'Measured RB CX errors are not identical to after-Clifford depolarization.',
             'T1-only relaxation omits phase decoherence and unknown Ramsey T2-star.',
             'Median readout error merges asymmetric assignment probabilities.',
             'The Stim repetition-code generator is not a transpiled pulse-level Manila experiment.',
             'No real device bitstrings were compared, no out-of-sample prediction is claimed.',
             'This historical 5-qubit processor cannot validate rotated-surface-code d3 memory.'
           ]}
    return proxy


def produce_outputs(obj:dict, destination:Path, *, source_type:str, source_sha256:str, source_url:str):
    validate_calibration(obj)
    if source_type not in ('CURATED_PUBLISHED_SUBSET','FULL_ORIGINAL_JSON'):
        raise ValueError('unsupported source type')
    proxy=project_calibration(obj)
    destination.mkdir(parents=True,exist_ok=True)
    provenance={'schema':'ftqc.public_calibration_provenance.v1',
                'classification':'MEASURED_HISTORICAL_INPUTS__MODEL_PROJECTION_NOT_VALIDATED',
                'backend':obj['backend_name'], 'snapshot_timestamp':obj['last_update_date'],
                'source_type':source_type,'source_url':source_url,'source_sha256':source_sha256,
                'original_raw_json_parsed':source_type=='FULL_ORIGINAL_JSON',
                'raw_file_verified':False, # no authenticated upstream checksum is pinned
                'hardware_validation_completed':False}
    (destination/'normalized_calibration.json').write_text(json.dumps(obj,indent=2)+'\n')
    (destination/'calibration_projection.json').write_text(json.dumps(proxy,indent=2)+'\n')
    (destination/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    with (destination/'qubit_calibrations.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['qubit','t1_us','t2_echo_us','readout_error',
                'prob_meas0_prep1','prob_meas1_prep0','readout_length_ns'])
        writer.writeheader();writer.writerows(obj['qubits'])
    with (destination/'coupling_errors.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['gate','qubits','gate_error','gate_length_ns'])
        writer.writeheader()
        for g in obj['two_qubit_gates']:
            writer.writerow({**g,'qubits':'-'.join(map(str,g['qubits']))})
    report=f'''# Real hardware calibration import - {obj['backend_name']}

**Snapshot:** {obj['last_update_date']} (historical IBM backend properties).
**Source:** {source_url}
**SHA256 of ingested source bytes:** `{source_sha256}`
**Input provenance:** {source_type}; the bundled subset is a transcription, not a SHA-verified copy of the entire upstream raw JSON.

## Measured properties (NOT guessed)

- Number of characterized physical qubits: {len(obj['qubits'])}.
- Median T1: {proxy['median_t1_us_measured']:.3f} µs.
- Median Hahn-echo T2: {proxy['median_t2_echo_us_measured_not_free_idle']:.3f} µs. **Not Ramsey T2-star.**
- Median readout duration: {proxy['median_readout_duration_us_measured']:.3f} µs.
- Median readout error: {proxy['median_readout_error_measured']:.4%}; mean {proxy['mean_readout_error_measured']:.4%}.
- Mean directed CX gate error: {proxy['mean_cx_error_measured']:.4%} across {len(obj['two_qubit_gates'])} calibrations.

## Calibration-informed, explicitly unvalidated simulator input (NOT hardware-validated)

`calibration_projection.json` contains a **five-qubit d=3 repetition-code demonstration**, derived from published qubit and gate metrics. The T1-only waiting channel uses the measured readout duration as a *hypothesized* wait. It does not assume T2 echo equals free-idle Ramsey. Gate RB error mapped onto Stim's generic after-Clifford depolarization is a **proxy**, not a physical equality. No readout channel count is inferred from gate/readout timings.

### Not established

- No matched real-device QEC shots or experimentally verified logical-failure predictions.
- No contemporaneous or 2026 calibration; the snapshot is from 2024.
- No full surface-code validation: this machine has only five physical qubits.
- No free-idle Ramsey T2*, no measured cross-talk, no schedule/concurrency model.

**Next:** Compare a specifically matched open hardware repetition-code dataset against this proxy, with timestamps and held-out shots. See `docs/PHYSICAL_CALIBRATION.md` and `docs/LIMITATIONS.md`.
'''
    (destination/'CALIBRATION_IMPORT_REPORT.md').write_text(report)
    return proxy


def simulate_calibration_proxy(proxy:dict, shots:int, seed:int)->dict:
    """Real Stim+PyMatching *simulator* execution when available; not QPU data."""
    if not isinstance(shots,int) or shots<1 or not isinstance(seed,int):
        raise ValueError('shots must be positive integer and seed integer')
    try:
        import stim, pymatching
        import numpy as np
    except ImportError as e:
        raise RuntimeError('Stim, PyMatching and NumPy required for actual decoded simulator trials') from e
    cfg=proxy['stim_parameters_ILLUSTRATIVE']
    circuit=stim.Circuit.generated('repetition_code:memory', **cfg)
    dem=circuit.detector_error_model(decompose_errors=True)
    decoder=pymatching.Matching.from_detector_error_model(dem)
    samples,actual=circuit.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    predicted=decoder.decode_batch(samples)
    failure=int(np.count_nonzero(np.any(predicted!=actual,axis=1)))
    return {'status':'STIM_SIMULATION_OF_CALIBRATION_DERIVED_PROXY__NOT_DEVICE_PREDICTION',
            'shots':shots,'logical_failures':failure,'observed_failure_fraction':failure/shots,
            'stim_version':stim.__version__,'pymatching_version':pymatching.__version__,
            'seed':seed,'distance':cfg['distance'],'rounds':cfg['rounds'],
            'source_timestamp':proxy['snapshot_timestamp'],
            'hardware_observations_used':False,
            'limitations':proxy['limitations']}


def main():
    parser=argparse.ArgumentParser(description='Import real historical Qiskit backend properties and derive an explicitly conditional noise proxy')
    parser.add_argument('--input',type=Path,default=Path('examples/public_ibmq_manila_2024_subset.json'))
    parser.add_argument('--raw',action='store_true',help='parse complete raw IBM props JSON, not curated subset')
    parser.add_argument('--output-dir',type=Path,default=Path('outputs/public_calibration'))
    parser.add_argument('--simulate',action='store_true',help='run Stim+PyMatching repetition-code proxy, not hardware')
    parser.add_argument('--shots',type=int,default=20000)
    parser.add_argument('--seed',type=int,default=20261029)
    args=parser.parse_args()
    contents=args.input.read_bytes()
    raw=json.loads(contents)
    obj=normalize_full_ibm_properties(raw) if args.raw else validate_calibration(raw)
    if args.raw:
        if obj['backend_name']!='ibmq_manila' or obj['last_update_date']!=CURATED_DATE:
            raise ValueError('raw upstream file has changed; do not silently mix snapshots or devices')
        # Independently reconcile each curated field against the original
        # source bytes before claiming the hand-transcribed subset matches.
        expected_path=Path(__file__).resolve().parents[2]/'examples/public_ibmq_manila_2024_subset.json'
        expected=validate_calibration(json.loads(expected_path.read_text()))
        if (obj['qubits']!=expected['qubits'] or
            obj['two_qubit_gates']!=expected['two_qubit_gates'] or
            obj['backend_version']!=expected['backend_version']):
            raise ValueError('Downloaded raw property values disagree with bundled published-source transcription')
        obj['upstream_raw_url']=CURATED_URL
        obj['upstream_browse_url']=CURATED_URL.replace('raw.githubusercontent.com/','github.com/').replace('/main/','/blob/main/')
        source_type='FULL_ORIGINAL_JSON'
    else:
        if obj['upstream_raw_url']!=CURATED_URL or obj['last_update_date']!=CURATED_DATE:
            raise ValueError('unrecognized bundled source, expected pinned historical IBM Manila')
        source_type='CURATED_PUBLISHED_SUBSET'
    proxy=produce_outputs(obj,args.output_dir,source_type=source_type,
                          source_sha256=sha256(contents).hexdigest(),source_url=CURATED_URL)
    if args.simulate:
        simulation=simulate_calibration_proxy(proxy,args.shots,args.seed)
        (args.output_dir/'stim_repetition_memory_proxy.json').write_text(json.dumps(simulation,indent=2)+'\n')
        print('STIM SIMULATION (NOT HARDWARE):',simulation['logical_failures'],'/',simulation['shots'])
    print(f'Imported {len(obj["qubits"])} historical measured qubits and {len(obj["two_qubit_gates"])} directed CX calibrations')
    print(f'Provenance {source_type}; calibration-derived noise proxy is NOT hardware-validated')
    print('Outputs:',args.output_dir)

if __name__=='__main__':main()
