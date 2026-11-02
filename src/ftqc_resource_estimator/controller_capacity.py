"""Capacity-limited control scheduling envelope, separated from physical qubit accounting.

Toy electronics constraints, NOT a calibrated or circuit-faithful measurement schedule.
A single Stim memory noise distribution is held constant across electronics assumptions.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import dataclass
import json
import math
from pathlib import Path
from hashlib import sha256
from .memory_analysis import validate_stim_manifest
from .reliability import wilson, cumulative_failure
from .sample_planning import allowed_memory_error

@dataclass(frozen=True)
class ReadoutController:
    name: str
    concurrent_readout_channels: int
    readout_slot_us: float
    minimum_round_us: float
    decode_latency_us: float
    power_per_channel_w: float
    fixed_controller_power_w: float = 0
    def __post_init__(self):
        if not self.name or not isinstance(self.concurrent_readout_channels,int) or self.concurrent_readout_channels<1:
            raise ValueError('positive integer readout channels required')
        vals=(self.readout_slot_us,self.minimum_round_us,self.decode_latency_us,
              self.power_per_channel_w,self.fixed_controller_power_w)
        if any(not math.isfinite(v) or v<0 for v in vals) or self.readout_slot_us==0 or self.minimum_round_us==0:
            raise ValueError('invalid nonnegative finite duration or power parameter')


def evaluate_controller(rows:list[dict],controllers:list[ReadoutController],*,patches:int=4,windows:int=10,
                        target_failure:float=.1)->list[dict]:
    if patches<1 or windows<1 or not 0<target_failure<1:raise ValueError('invalid workload')
    budget=allowed_memory_error(target_failure,patches,windows)
    result=[]
    for obs in rows:
        d=obs['distance'];rounds=obs['rounds'];shots=obs['shots']
        if d<3 or d%2!=1 or rounds<1:raise ValueError('invalid memory code geometry')
        upper=wilson(obs['failures'],shots).upper
        for ctrl in controllers:
            measurement_events_per_round=patches*(d*d-1)
            readout_batches=math.ceil(measurement_events_per_round/ctrl.concurrent_readout_channels)
            round_envelope_us=max(ctrl.minimum_round_us,readout_batches*ctrl.readout_slot_us)
            time_us=windows*(rounds*round_envelope_us+ctrl.decode_latency_us)
            result.append({
                'controller':ctrl.name,'distance':d,'rounds':rounds,
                'patches':patches,'windows':windows,'data_and_ancilla_qubits':patches*(2*d*d-1),
                'stabilizer_measurements_per_round':measurement_events_per_round,
                'readout_channels':ctrl.concurrent_readout_channels,
                'readout_batches_per_round':readout_batches,
                'readout_slots_us':ctrl.readout_slot_us,
                'round_envelope_us':round_envelope_us,
                'total_memory_time_us':time_us,
                'controller_power_proxy_w':ctrl.concurrent_readout_channels*ctrl.power_per_channel_w+ctrl.fixed_controller_power_w,
                'logical_error_upper95':upper,
                'independent_event_budget':budget,
                'workload_failure_upper95':cumulative_failure(upper,patches*windows),
                'reliability_feasible':upper<=budget,
                'timing_noise_coupling':'NOT_SIMULATED',
                'calibration_status':'HYPOTHETICAL_NOT_HARDWARE_VALIDATED',
            })
    return result


def load_controllers(path:Path):
    obj=json.loads(path.read_text())
    if obj.get('calibration_status')!='HYPOTHETICAL_NOT_HARDWARE_VALIDATED':
        raise ValueError('only explicitly hypothetical example input accepted in this demo')
    return [ReadoutController(**c) for c in obj['controllers']]


def capacity_pareto(rows:list[dict])->list[dict]:
    """Three separate axes: physical qubits, controller power, wall-clock envelope."""
    eligible=[r for r in rows if r['reliability_feasible']]
    keys=('data_and_ancilla_qubits','controller_power_proxy_w','total_memory_time_us')
    return [r for r in eligible if not any(
        all(x[k]<=r[k] for k in keys) and any(x[k]<r[k] for k in keys)
        for x in eligible if x is not r)]


def analyze(manifest:dict,controller_config:Path,output:Path,*,verified:bool):
    obs=validate_stim_manifest(manifest,basis='X',physical_error=.003,rounds=9,distances=(7,9))
    ctrls=load_controllers(controller_config)
    rows=evaluate_controller([obs[k] for k in sorted(obs)],ctrls)
    output.mkdir(parents=True,exist_ok=True)
    with (output/'capacity_sensitivity.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    pareto=capacity_pareto(rows)
    text=['# Capacity-constrained control envelope - independent architecture extension','',
          '**Status:** '+ ('owner-supplied Stim manifest with replay certificate checked' if verified else 'UNVERIFIED owner-supplied manifest; analysis is not a validation certificate'),
          '**Scientific boundary:** abstract readout-channel scheduling bound, NOT a waveform/circuit-level schedule; Stim error rates are held fixed, so extra wait/decoherence and controller noise have NOT been simulated.',
          '**Physical accounting:** patch qubits and controller-channel/power proxies are reported in **separate columns**; electronic channels and watts are not added to physical qubits.',
          '**Inputs:** all example readout timing and power coefficients are HYPOTHETICAL, not measurements from quantum hardware.', '',
          '## Scenario results','',
          '| d | Controller | Physical patch qubits | Readout channels | Batches / round | Controller power proxy (W) | Memory time (us) | Reliability feasible |',
          '|---:|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        text.append(f'| {r["distance"]} | {r["controller"]} | {r["data_and_ancilla_qubits"]} | {r["readout_channels"]} | {r["readout_batches_per_round"]} | {r["controller_power_proxy_w"]:.2f} | {r["total_memory_time_us"]:.1f} | {r["reliability_feasible"]} |')
    text.extend(['','## Feasible nondominated points (qubits, power, latency independently)','',
                 *(f'- d={r["distance"]}, {r["controller"]}' for r in pareto), '',
                 'An electronic readout channel is NOT a physical qubit or universal readout architecture. Real readout multiplexing, gate scheduling, readout duration, controller bandwidth, correlated errors, classical decoder pipeline, and waiting-time decoherence must be calibrated and incorporated into circuit simulation before any performance claim.',
                 'An operational extension would build a matching error channel with duration-dependent idle errors and independently measured controller throughput; this project does not yet implement that calibration.'])
    (output/'CAPACITY_STUDY.md').write_text('\n'.join(text)+'\n')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8.5,5))
        for r in rows:
            ax.scatter(r['controller_power_proxy_w'],r['total_memory_time_us'],
                       marker='o' if r['reliability_feasible'] else 'x',s=90)
            ax.annotate(f'd{r["distance"]} {r["controller"]}',
                        (r['controller_power_proxy_w'],r['total_memory_time_us']),
                        textcoords='offset points',xytext=(5,4),fontsize=8)
        ax.set_xlim(0,118)
        ax.set_ylim(35,480)
        ax.set_xlabel('Hypothetical controller power (W; not hardware measured)')
        ax.set_ylabel('Abstract capacity-limited memory time (µs)')
        ax.set_title('Physical patch qubits counted separately - scheduling envelope only')
        ax.grid(alpha=.2);fig.tight_layout()
        fig.savefig(output/'capacity_envelope.png',dpi=170);plt.close(fig)
    except ImportError:pass
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--observations',type=Path,default=Path('outputs/stim_memory/followup/observations.json'))
    p.add_argument('--verified-certificate',type=Path,default=Path('outputs/stim_memory/followup/VERIFIED_FOLLOWUP.json'))
    p.add_argument('--controller-config',type=Path,default=Path('examples/controller_capacity_hypotheses.json'))
    p.add_argument('--output-dir',type=Path,default=Path('outputs/controller_capacity'))
    a=p.parse_args()
    raw=a.observations.read_bytes();obj=json.loads(raw)
    cert=json.loads(a.verified_certificate.read_text()) if a.verified_certificate.is_file() else {}
    if not str(cert.get('status','')).startswith('PASSED') or cert.get('observation_sha256')!=sha256(raw).hexdigest():
        raise ValueError('follow-up not yet replay-certified; first run scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh on your Mac')
    rows=analyze(obj,a.controller_config,a.output_dir,verified=True)
    print(f'Capacity scheduling illustration generated: {len(rows)} scenarios; NOT device calibrated')

if __name__=='__main__':main()
