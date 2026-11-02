"""Published-coherence-informed *conditional* controller-idle-noise study.

All code in this file is a analysis-specific orchestration built around the
public Stim/PyMatching APIs. Uses Google's *reported mean* Willow T1 and
T2_CPMG for an EXPLORATORY Pauli-twirled waiting channel; this is not a
hardware-calibrated idle experiment or an independent decoder.

The waiting-time scenario is an assumed readout batching model, not a
measurement of Willow controller channel availability or electronics power.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import re

from .reliability import wilson, cumulative_failure
from .sample_planning import allowed_memory_error

SCHEMA = 'ftqc.controller_idle_coherence.v1'
DOI = 'https://doi.org/10.1038/s41586-024-08449-y'
REFERENCE_NOTE = ('Google Quantum AI and Collaborators, Nature 638, 920–926 (2025), '
                  'mean Willow T1=68 us, T2,CPMG=89 us, QEC cycle=1.1 us. '
                  'T2,CPMG is NOT idle Ramsey T2 and is used only as a sensitivity proxy.')
DEFAULT_DISTANCES = (3, 5, 7, 9)
BASE_NOISE = .003
DEFAULT_SHOTS = 20000
DEFAULT_SEED = 20261029
EXPECTED_SCENARIOS = ('wide_parallel_readout', 'medium_parallel_readout', 'constrained_parallel_readout')


@dataclass(frozen=True)
class CoherenceParameters:
    t1_us: float = 68.0
    t2_proxy_us: float = 89.0
    published_cycle_us: float = 1.1
    reference: str = DOI
    coherence_label: str = 'T2_CPMG_IS_NOT_IDLE_T2__EXPLORATORY_PROXY'

    def __post_init__(self):
        vals = (self.t1_us, self.t2_proxy_us, self.published_cycle_us)
        if any(not math.isfinite(x) or x <= 0 for x in vals):
            raise ValueError('coherence times and cycle duration must be finite positive values')
        if self.t2_proxy_us > 2*self.t1_us:
            raise ValueError('invalid time constants: T2 may not exceed 2*T1 in this channel')
        if self.reference != DOI or self.coherence_label != 'T2_CPMG_IS_NOT_IDLE_T2__EXPLORATORY_PROXY':
            raise ValueError('unrecognized calibration provenance')


@dataclass(frozen=True)
class SchedulingHypothesis:
    name: str
    channels_shared_by_all_patches: int
    readout_slot_us: float
    power_per_channel_w: float

    def __post_init__(self):
        if (not self.name or self.channels_shared_by_all_patches < 1 or
            not isinstance(self.channels_shared_by_all_patches,int)):
            raise ValueError('invalid readout channels')
        if (not math.isfinite(self.readout_slot_us) or self.readout_slot_us<=0 or
            not math.isfinite(self.power_per_channel_w) or self.power_per_channel_w<0):
            raise ValueError('invalid hypothetical scheduling input')


def load_hypotheses(path: Path) -> tuple[CoherenceParameters, list[SchedulingHypothesis], int, int, float]:
    obj = json.loads(path.read_text())
    if obj.get('classification') != 'PUBLISHED_COHERENCE_WITH_UNCALIBRATED_SCHEDULING' or obj.get('source_doi') != DOI:
        raise ValueError('missing provenance / no fabricated hardware certification allowed')
    coh = CoherenceParameters(**obj['coherence'])
    ctrl = [SchedulingHypothesis(**item) for item in obj['controllers']]
    if tuple(x.name for x in ctrl)!=EXPECTED_SCENARIOS:
        raise ValueError('registered controller scenario names or order changed')
    workload=obj['workload']
    patches, windows=workload['patches'],workload['windows']
    target=workload['target_total_failure']
    if not isinstance(patches,int) or not isinstance(windows,int) or patches<1 or windows<1 or not 0<target<1:
        raise ValueError('invalid workload')
    return coh,ctrl,patches,windows,float(target)


def twirled_idle_paulis(duration_us:float, coh:CoherenceParameters)->tuple[float,float,float]:
    """Pauli twirl of amplitude + exponential phase decay, not exact damping.

    Pauli eigenvalues lambda_x=lambda_y=exp(-t/T2), lambda_z=exp(-t/T1).
    Pauli mixture gives P(X)=P(Y)=(1-lambda_z)/4,
    P(Z)=(1+lambda_z-2*lambda_x)/4. Translation drops the
    non-unital part of amplitude damping, a significant approximation.
    """
    if not math.isfinite(duration_us) or duration_us<0:
        raise ValueError('duration must be finite nonnegative')
    a=math.exp(-duration_us/coh.t1_us)
    b=math.exp(-duration_us/coh.t2_proxy_us)
    px=py=(1-a)/4
    pz=(1+a-2*b)/4
    if min(px,py,pz)<-1e-12 or px+py+pz>1+1e-12:
        raise ValueError('Pauli-twirl probabilities are not physical')
    return max(0.0,px),max(0.0,py),max(0.0,pz)


def scenario_schedule(distance:int, scenario:SchedulingHypothesis,coh:CoherenceParameters,patches:int=4)->dict:
    if distance<3 or distance%2!=1 or not isinstance(patches,int) or patches<1:
        raise ValueError('odd code distance >=3 and positive patch count required')
    checks=patches*(distance*distance-1)
    batches=math.ceil(checks/scenario.channels_shared_by_all_patches)
    readout_envelope_us=batches*scenario.readout_slot_us
    extra=max(0.0,readout_envelope_us-coh.published_cycle_us)
    px,py,pz=twirled_idle_paulis(extra,coh)
    return {'distance':distance,'rounds':distance,'controller':scenario.name,
            'patches':patches,'readout_checks_per_round_all_patches':checks,
            'readout_channels':scenario.channels_shared_by_all_patches,
            'batches_per_round':batches,'hypothetical_readout_slot_us':scenario.readout_slot_us,
            'hypothetical_round_duration_us':max(coh.published_cycle_us,readout_envelope_us),
            'extra_data_idle_per_round_us':extra,
            'idle_pauli_x':px,'idle_pauli_y':py,'idle_pauli_z':pz,
            'idle_total_pauli_probability_per_data_per_round':px+py+pz,
            'hypothetical_controller_power_w':scenario.channels_shared_by_all_patches*scenario.power_per_channel_w,
            'patch_physical_qubits':patches*(2*distance*distance-1)}


def _data_targets_from_x_memory(stim,base,distance:int)->list[int]:
    # In Stim's generated rotated X-memory circuit the d² data qubits are the
    # initial RX set. Fail closed if generator layout changes in future Stim.
    init=[x for x in base if isinstance(x,stim.CircuitInstruction) and x.name=='RX']
    if len(init)!=1:
        raise RuntimeError('unexpected Stim rotated-X data initialization layout')
    data=[int(t.value) for t in init[0].targets_copy()]
    if len(data)!=distance*distance or len(set(data))!=len(data):
        raise RuntimeError('incorrect data set from Stim generated RX initialization')
    return data


def _insert_idle_after_round_start(base_text:str, data:list[int], paulis:tuple[float,float,float], rounds:int)->str:
    """Transform Stim generator *text*, not its detector/measurement records.

    Inject exactly one channel after the first TICK of the initialization
    block and one after the first TICK of the repeated syndrome block.
    Guard against unexpected generator layouts rather than guessing timing.
    """
    if sum(paulis)==0:
        return base_text
    lines=base_text.splitlines()
    inside_repeat=False
    counts={'first':0,'repeat':0}
    repeat_count=0
    output=[]
    insertion='PAULI_CHANNEL_1('+','.join(format(p,'.17g') for p in paulis)+') '+' '.join(map(str,data))
    for line in lines:
        s=line.strip()
        if s.startswith('REPEAT '):
            if inside_repeat or repeat_count:
                raise RuntimeError('unexpected nested or multiple Stim REPEAT blocks')
            m=re.fullmatch(r'REPEAT\s+(\d+)\s*\{',s)
            if not m: raise RuntimeError('unrecognized Stim repeat block')
            repeat_count=int(m.group(1))
            inside_repeat=True
        elif s=='}':
            if not inside_repeat:raise RuntimeError('unexpected Stim closing brace')
            inside_repeat=False
        output.append(line)
        if s=='TICK':
            key='repeat' if inside_repeat else 'first'
            if counts[key]==0:
                # We only append at the first tick in each iteration's block.
                output.append(('    ' if inside_repeat else '')+insertion)
            counts[key]+=1
    if inside_repeat or counts['first']<1 or (rounds>1 and (counts['repeat']<1 or repeat_count!=rounds-1)):
        raise RuntimeError('unexpected first-round / repeated-round Stim layout')
    if rounds==1 and repeat_count:
        raise RuntimeError('unexpected REPEAT block for one round')
    return '\n'.join(output)+'\n'


def build_idle_circuit(stim, *,distance:int, rounds:int,base_p:float,
                       schedule:dict, basis:str='X'):
    if not 0<=base_p<1 or basis!='X' or rounds != distance:
        raise ValueError('registered study requires basis X and rounds=distance')
    base=stim.Circuit.generated('surface_code:rotated_memory_x',distance=distance,rounds=rounds,
         after_clifford_depolarization=base_p,before_round_data_depolarization=base_p,
         before_measure_flip_probability=base_p,after_reset_flip_probability=base_p)
    paulis=tuple(schedule[k] for k in ('idle_pauli_x','idle_pauli_y','idle_pauli_z'))
    if sum(paulis)==0:return base
    data=_data_targets_from_x_memory(stim,base,distance)
    amended=stim.Circuit(_insert_idle_after_round_start(str(base),data,paulis,rounds))
    if (amended.num_detectors!=base.num_detectors or amended.num_observables!=base.num_observables or
        amended.num_measurements!=base.num_measurements):
        raise RuntimeError('idle insertion unexpectedly changed detector/observable/measurement structure')
    return amended


def _one_case(stim,pymatching,*,distance:int,scenario:SchedulingHypothesis,coh:CoherenceParameters,
              patches:int,shots:int,seed:int,base_p:float)->dict:
    schedule=scenario_schedule(distance,scenario,coh,patches)
    circuit=build_idle_circuit(stim,distance=distance,rounds=distance,base_p=base_p,schedule=schedule)
    dem=circuit.detector_error_model(decompose_errors=True)
    syndromes,logical=circuit.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    if syndromes.shape[0]!=shots or logical.shape!=(shots,1):
        raise RuntimeError('Stim returned unexpected shot / observable dimensions')
    decoder=pymatching.Matching.from_detector_error_model(dem)
    estimates=decoder.decode_batch(syndromes)
    if estimates.shape != logical.shape:
        raise RuntimeError('PyMatching returned unexpected estimates')
    for i in range(min(shots,8)):
        if not (decoder.decode(syndromes[i])==estimates[i]).all():
            raise RuntimeError('PyMatching batch and single-shot disagree')
    errors=int((logical!=estimates).any(axis=1).sum())
    return {**schedule,'physical_error':base_p,'shots':shots,'failures':errors,'seed':seed,
            'circuit_sha256':sha256(str(circuit).encode()).hexdigest(),
            'detector_model_sha256':sha256(str(dem).encode()).hexdigest(),
            'num_detectors':int(circuit.num_detectors),'num_observables':int(circuit.num_observables),
            'decoder':'pymatching_mwpm_from_full_modified_circuit_dem',
            'noise_model':'stim_four_uniform_baseline_knobs_PLUS_independent_per_round_data_idle_Pauli_twirl'}


def _expected_grid(controllers:list[SchedulingHypothesis])->list[tuple[int,SchedulingHypothesis]]:
    return [(d,c) for d in DEFAULT_DISTANCES for c in controllers]


def validate_manifest(obj:dict,coh:CoherenceParameters,ctrl:list[SchedulingHypothesis],
                      patches:int,windows:int,target:float,*,strict:bool=True)->list[dict]:
    if obj.get('schema')!=SCHEMA or obj.get('source_doi')!=DOI or obj.get('coherence')!=asdict(coh):
        raise ValueError('wrong provenance or coherence parameters')
    p=obj.get('protocol',{})
    shots=p.get('shots_per_case')
    if strict and (shots!=DEFAULT_SHOTS or p.get('seed_base')!=DEFAULT_SEED or
                   p.get('physical_error')!=BASE_NOISE):
        raise ValueError('registered experiment parameters were changed')
    if (p.get('rounds_rule')!='rounds=distance' or p.get('patches')!=patches or
        p.get('windows')!=windows or p.get('target_total_failure')!=target or
        not isinstance(shots,int) or shots<1):
        raise ValueError('invalid experiment protocol')
    rows=obj.get('observations',[])
    if len(rows)!=len(DEFAULT_DISTANCES)*len(ctrl):
        raise ValueError('missing controller-distance observations')
    for i,((d,scenario),row) in enumerate(zip(_expected_grid(ctrl),rows)):
        expected=scenario_schedule(d,scenario,coh,patches)
        if row.get('distance')!=d or row.get('controller')!=scenario.name:
            raise ValueError('wrong order or mismatched scenarios')
        for k,value in expected.items():
            if row.get(k)!=value:
                raise ValueError(f'controller schedule was altered: {k}')
        if (row.get('shots')!=shots or row.get('physical_error')!=p.get('physical_error') or
            row.get('seed')!=p.get('seed_base')+i or
            row.get('decoder')!='pymatching_mwpm_from_full_modified_circuit_dem' or
            row.get('num_observables')!=1 or not row.get('circuit_sha256') or
            not row.get('detector_model_sha256')):
            raise ValueError('invalid decoding or result provenance')
        if not isinstance(row.get('failures'),int) or not 0<=row['failures']<=shots:
            raise ValueError('invalid shot counts')
    return rows


def analyze_rows(obj:dict,coh:CoherenceParameters,ctrl:list[SchedulingHypothesis],
                 patches:int,windows:int,target:float,*,strict:bool=True)->list[dict]:
    raw=validate_manifest(obj,coh,ctrl,patches,windows,target,strict=strict)
    budget=allowed_memory_error(target,patches,windows)
    out=[]
    for r in raw:
        ci=wilson(r['failures'],r['shots'])
        out.append({**r,'observed_logical_failure':ci.mean,'wilson_upper95':ci.upper,
                    'per_event_budget':budget,'conservatively_feasible':ci.upper<=budget,
                    'workload_failure_upper_proxy':cumulative_failure(ci.upper,patches*windows),
                    'modeled_time_per_memory_window_us':r['hypothetical_round_duration_us']*r['rounds']})
    return out


def save_parameter_preview(path:Path,config:Path)->None:
    coh,ctrl,patches,windows,target=load_hypotheses(config)
    path.mkdir(parents=True,exist_ok=True)
    rows=[scenario_schedule(d,c,coh,patches) for d,c in _expected_grid(ctrl)]
    with (path/'idle_channel_inputs_ONLY.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    doc=['# Published-coherence / hypothetical controller-delay INPUT PREVIEW','',
         '> This is NOT a decoded QEC result. NO logical failure rates or feasibility decisions are generated here.','',
         f'**Source:** {REFERENCE_NOTE}',
         '**Classification:** measured published means are T1, T2_CPMG and the cycle time; '
         'controller readout-channel counts, batching, per-channel timing and power are NOT Willow measurements.',
         '**Model:** Readout waves per round = ceil(4(d²−1)/channels). Extra data idle = '
         'max(0, batches × assumed readout-slot − 1.1us). Insert a Pauli-twirled '
         'exponential T1/T2 channel on data qubits at each of d syndrome-round starts.',
         '**Warning:** Pauli twirling omits the non-unital part of amplitude damping. '
         'CPMG coherence is not free-idle Ramsey T2. Measurement queuing assumes '
         'time can be reallocated without modifying the stabilizer circuit; this is not established.',
         '**Distinct question:** The calibrated device metric is not yet a calibrated controller-delay model. '
         'Only real Stim/PyMatching simulation can test the hypothetical delayed schedules.','',
         '| d | Scenario | Batches | Extra idle / round (us) | Added data Pauli probability / round |',
         '|---:|---|---:|---:|---:|']
    for r in rows:
        doc.append(f'| {r["distance"]} | {r["controller"]} | {r["batches_per_round"]} | '
                   f'{r["extra_data_idle_per_round_us"]:.4f} | '
                   f'{r["idle_total_pauli_probability_per_data_per_round"]:.6f} |')
    (path/'README_INPUTS_ONLY.md').write_text('\n'.join(doc)+'\n')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8.4,5.2))
        for c in ctrl:
            group=[r for r in rows if r['controller']==c.name]
            ax.plot([r['distance'] for r in group],
                    [100*r['idle_total_pauli_probability_per_data_per_round'] for r in group],
                    marker='o',label=c.name.replace('_',' '))
        ax.set_xlabel('Code distance (syndrome rounds also equal d)')
        ax.set_ylabel('Added per-data-qubit Pauli event / round (%)')
        ax.set_title('Published coherence + hypothetical queuing: input channels ONLY')
        ax.grid(alpha=.2);ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(path/'idle_input_sensitivity.png',dpi=170);plt.close(fig)
    except ImportError:pass


def write_study(obj:dict,out:Path,coh,ctrl,patches,windows,target,*,strict=True):
    rows=analyze_rows(obj,coh,ctrl,patches,windows,target,strict=strict)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'idle_decoding_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    text=['# Controller-induced idle errors: simulated conditional QEC sensitivity','',
          '**Status:** Real Stim/PyMatching executed for specified input assumptions; published coherence numbers are not full hardware calibration.',
          '**Reference:** '+REFERENCE_NOTE,'',
          '**Causal interpretation:** Published T1 and T2_CPMG only set the Pauli-twirled waiting channel. '
          'Readout batching and channel power are *independent hypothetical counterfactuals*, '
          'not measured Google Willow electronics.',
          '**Protocol:** rotated X surface-code memory; rounds=d; all four baseline error knobs p=.003; '
          'additional independent Pauli channel on all data qubits at the start of each round; '
          'new matching decoder graph built from each modified circuit.',
          '**Reliability decision:** two-sided pointwise Wilson upper 95% bound ≤ '
          f'{allowed_memory_error(target,patches,windows):.8f} per event, assuming {patches*windows} independent identical memory events.',
          '**Not justified:** true device-level QEC logical rates, empirical crossover, correlated leakage/crosstalk, '
          'controller-watt calibration, or statistical comparison of paired samples.', '',
          '| d | Scenario | Extra idle (us/round) | Failures/shots | Wilson upper95 | Feasible |',
          '|---:|---|---:|---:|---:|---|']
    for r in rows:
        text.append(f'| {r["distance"]} | {r["controller"]} | {r["extra_data_idle_per_round_us"]:.3f} | '
                    f'{r["failures"]}/{r["shots"]} | {r["wilson_upper95"]:.6f} | '
                    f'{"yes" if r["conservatively_feasible"] else "no"} |')
    text+=['','## Feasibility changes at each distance','']
    for d in DEFAULT_DISTANCES:
        group=[r for r in rows if r['distance']==d]
        meets=[r['controller'] for r in group if r['conservatively_feasible']]
        text.append(f'- d={d}: '+(', '.join(meets) if meets else 'NO tested controller meets the conservative bound'))
    text+=['','## Validity and novelty','',
           'This tests a new, carefully delimited *conditional architecture decision* within known stabilizer-code and MWPM methods. '
           'It is an integration/ablation analysis, not a novel decoder, a new QEC code, or a hardware prediction.',
           'A channel-level test does not assert that real readout-channel batching creates exactly these idle intervals. '
           'For device validity, obtain measured raw idle Ramsey T2, per-channel readout schedule, gate-idle placement, '
           'noise covariance and control throughput for the same processor before interpreting these as calibrated predictions.',
           'Marginal 95% Wilson upper intervals are not a familywise 95% guarantee over 12 configurations.']
    (out/'IDLE_NOISE_REPORT.md').write_text('\n'.join(text)+'\n')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8.5,5.4))
        for ctrl_name in EXPECTED_SCENARIOS:
            group=[r for r in rows if r['controller']==ctrl_name]
            ax.errorbar([r['distance'] for r in group],
                        [100*r['observed_logical_failure'] for r in group],
                        yerr=[[100*(r['observed_logical_failure']-wilson(r['failures'],r['shots']).lower) for r in group],
                              [100*(r['wilson_upper95']-r['observed_logical_failure']) for r in group]],
                        marker='o',capsize=3,label=ctrl_name.replace('_',' '))
        ax.axhline(100*allowed_memory_error(target,patches,windows),ls='--',color='gray',label='per-event reliability target')
        ax.set_xlabel('Code distance (rounds=d)')
        ax.set_ylabel('Per-memory-experiment logical failure (%)')
        ax.set_title('Conditional delayed-controller QEC simulation - not device predictions')
        ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout()
        fig.savefig(out/'idle_logical_failure.png',dpi=170);plt.close(fig)
    except ImportError:pass


def _make_manifest(*,coh,ctrl,patches,windows,target,shots,seed,base_p,stim,pymatching,numpy):
    records=[]
    for i,(d,c) in enumerate(_expected_grid(ctrl)):
        r=_one_case(stim,pymatching,distance=d,scenario=c,coh=coh,patches=patches,
                    shots=shots,seed=seed+i,base_p=base_p)
        records.append(r)
        print(f'idle QEC d={d}, controller={c.name}: {r["failures"]}/{shots}, additional idle={r["extra_data_idle_per_round_us"]:.3g} us',flush=True)
    return {'schema':SCHEMA,'source_doi':DOI,'generated_utc':datetime.now(timezone.utc).isoformat(),
            'coherence':asdict(coh),
            'protocol':{'physical_error':base_p,'rounds_rule':'rounds=distance',
                        'shots_per_case':shots,'seed_base':seed,'patches':patches,'windows':windows,
                        'target_total_failure':target,
                        'claim':'published coherence with uncalibrated controller batching, not hardware calibration'},
            'software':{'stim':stim.__version__,'pymatching':pymatching.__version__,
                        'numpy':numpy.__version__,'python':platform.python_version()},
            'observations':records}


def replay_manifest(obj,coh,ctrl,patches,windows,target):
    import stim,pymatching
    rows=validate_manifest(obj,coh,ctrl,patches,windows,target)
    if obj['software'].get('stim')!=stim.__version__ or obj['software'].get('pymatching')!=pymatching.__version__:
        raise RuntimeError('replay requires EXACT Stim/PyMatching versions')
    for r,(d,c) in zip(rows,_expected_grid(ctrl)):
        fresh=_one_case(stim,pymatching,distance=d,scenario=c,coh=coh,patches=patches,
                        shots=r['shots'],seed=r['seed'],base_p=r['physical_error'])
        for key in ('failures','circuit_sha256','detector_model_sha256','num_detectors',
                    'num_observables','extra_data_idle_per_round_us'):
            if fresh[key]!=r[key]:raise RuntimeError(f'Replay mismatch d={d}/{c.name}: {key}')
    return rows


def main(argv=None):
    ap=argparse.ArgumentParser(description='Published-coherence/hypothetical scheduling: conditional Stim/PyMatching idle-noise experiment')
    ap.add_argument('--config',type=Path,default=Path('examples/idle_coherence_study.json'))
    ap.add_argument('--output-dir',type=Path,default=Path('outputs/idle_coherence'))
    ap.add_argument('--preview-only',action='store_true',help='No Stim; plot assumed input channels only. Cannot establish feasibility.')
    ap.add_argument('--shots',type=int,default=DEFAULT_SHOTS,help='Use 20000 for registered certification; smaller runs are exploratory.')
    ap.add_argument('--replay-only',action='store_true',help='Replay saved full experiment in identical backend; no new input parameters.')
    args=ap.parse_args(argv)
    coh,ctrl,patches,windows,target=load_hypotheses(args.config)
    save_parameter_preview(args.output_dir/'inputs_only',args.config)
    if args.preview_only:
        print('Published coherence / hypothetical readout input preview generated. NO QEC simulation or feasibility evidence.')
        return 0
    import stim,pymatching,numpy
    manifest_path=args.output_dir/'observations.json'
    if args.replay_only:
        obj=json.loads(manifest_path.read_text())
        replay_manifest(obj,coh,ctrl,patches,windows,target)
        print('PASS: all 12 idle-noise Stim/PyMatching cases exactly replayed')
    else:
        if args.shots<1:raise ValueError('shots must be positive')
        obj=_make_manifest(coh=coh,ctrl=ctrl,patches=patches,windows=windows,target=target,
                           shots=args.shots,seed=DEFAULT_SEED,base_p=BASE_NOISE,
                           stim=stim,pymatching=pymatching,numpy=numpy)
        validate_manifest(obj,coh,ctrl,patches,windows,target,strict=(args.shots==DEFAULT_SHOTS))
        args.output_dir.mkdir(parents=True,exist_ok=True)
        manifest_path.write_text(json.dumps(obj,indent=2)+'\n')
        if args.shots==DEFAULT_SHOTS:
            replay_manifest(obj,coh,ctrl,patches,windows,target)
            print('PASS: independent replay of all 12 conditions with matching circuit hashes and failure counts')
        else:print('EXPLORATORY: nonregistered shot count, no certificate produced')
    write_study(obj,args.output_dir,coh,ctrl,patches,windows,target,strict=args.shots==DEFAULT_SHOTS if not args.replay_only else True)
    if obj['protocol']['shots_per_case']==DEFAULT_SHOTS:
        cert={'status':'PASSED real Stim/PyMatching full replay - conditional idle model only',
              'schema':SCHEMA,'source_doi':DOI,'manifest_sha256':sha256(manifest_path.read_bytes()).hexdigest(),
              'shots':DEFAULT_SHOTS*len(DEFAULT_DISTANCES)*len(ctrl),'conditions':12,
              'stim_version':stim.__version__,'pymatching_version':pymatching.__version__,
              'calibration_scope':'PUBLISHED_MEAN_COHERENCE_ONLY__CONTROLLER_SCHEDULE_ASSUMED'}
        (args.output_dir/'VALIDATED_IDLE_STUDY.json').write_text(json.dumps(cert,indent=2)+'\n')
        print('CONDITIONAL IDLE-NOISE SCIENTIFIC GATE PASSED; not hardware calibration')
    return 0

if __name__=='__main__':raise SystemExit(main())
