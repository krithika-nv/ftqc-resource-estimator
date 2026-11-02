"""Evidence-scoped composition of measured logical primitive rates.

A conditional independence baseline, NOT a physics-calibrated FTQC stack.
A measurement-level calibration is insufficient for claims about universal FTQC.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any

FAMILIES = ("superconducting", "photonic", "trapped_ion", "neutral_atom")
OPERATIONS = ("prepare", "memory_cycle", "clifford_1q", "clifford_2q", "t_gate", "measure")


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label}: expected non-negative integer")
    return value


def wilson(failures: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    _nonnegative_int(failures, "failures")
    _nonnegative_int(trials, "trials")
    if trials == 0 or failures > trials or not 0 < confidence < 1:
        raise ValueError("need positive trials, valid counts and confidence")
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p = failures / trials
    denom = 1 + z*z/trials
    mid = (p + z*z/(2*trials)) / denom
    rad = z * math.sqrt(p*(1-p)/trials + z*z/(4*trials*trials)) / denom
    return max(0.0,mid-rad),min(1.0,mid+rad)


def _read_time(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("experimental timestamps must include UTC offset")
    return t


def _positive_float(v: Any, label: str) -> float:
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
        raise ValueError(f"{label}: expected positive finite value")
    return float(v)


def evaluate(model: dict, workload: dict) -> dict:
    """Evaluate only protocol-matched, disjoint chronological train/holdout records.

    Sources remain externally supplied. Do NOT mark output independently verified:
    source-to-count extraction, cross-layer correlations and hardware calibration
    must still be audited separately against original experimental files.
    """
    if model.get("schema") != "ftqc.logical-primitives.v1":
        raise ValueError("unknown logical-primitive input schema")
    family = model.get("hardware_family")
    if family not in FAMILIES:
        raise ValueError("unknown hardware family")
    device = str(model.get("device_id", "")).strip()
    code = str(model.get("code_family", "")).strip()
    if not device or not code:
        raise ValueError("device and native code family required")
    if workload.get("schema") != "ftqc.logical-workload.v1":
        raise ValueError("unknown workload schema")
    counts = workload.get("operation_counts", {})
    if set(counts) != set(OPERATIONS):
        raise ValueError("logical workload must explicitly define all six primitive counts")
    for k in OPERATIONS:
        _nonnegative_int(counts[k], f"operation_counts.{k}")
    if not counts["t_gate"] or not counts["clifford_2q"]:
        raise ValueError("universal-workload example requires non-Clifford and entangling gates")
    records = model.get("observations", [])
    if not isinstance(records,list):
        raise ValueError("observations must be a list")
    by_op = {k:{"train":[],"holdout":[]} for k in OPERATIONS}
    for idx,rec in enumerate(records):
        op,split = rec.get("operation"), rec.get("split")
        if op not in OPERATIONS or split not in ("train","holdout"):
            raise ValueError(f"observation {idx}: invalid primitive or split")
        if rec.get("device_id") != device or rec.get("code_family") != code:
            raise ValueError("mixed devices or incompatible logical codes")
        if not rec.get("protocol_id") or not rec.get("run_id"):
            raise ValueError("protocol_id and run_id are mandatory")
        n = _nonnegative_int(rec.get("trials"),"trials")
        f = _nonnegative_int(rec.get("failures"),"failures")
        if n == 0 or f > n:
            raise ValueError("invalid measured trial counts")
        _read_time(rec.get("observed_utc",""))
        _positive_float(rec.get("duration_us"),"duration_us")
        by_op[op][split].append(rec)
    missing = [k for k,st in by_op.items() if not st["train"] or not st["holdout"]]
    if missing:
        raise ValueError("required matched train and holdout measurements missing: "+", ".join(missing))
    estimated={}
    joint_success=joint_success_upper=joint_success_lower=1.0
    serial_runtime_us = 0.0
    for op in OPERATIONS:
        training,holdout=by_op[op]["train"],by_op[op]["holdout"]
        a={(x['protocol_id']) for x in training}; b={(x['protocol_id']) for x in holdout}
        if len(a)!=1 or a!=b:
            raise ValueError(f"{op}: must compare the exact same operation protocol")
        train_ids={x["run_id"] for x in training}
        holdout_ids={x["run_id"] for x in holdout}
        if train_ids & holdout_ids:
            raise ValueError(f"{op}: train/holdout run leakage")
        if max(_read_time(x["observed_utc"]) for x in training) >= min(_read_time(x["observed_utc"]) for x in holdout):
            raise ValueError(f"{op}: holdout must be strictly later than training")
        tr=sum(x['trials'] for x in training); tf=sum(x['failures'] for x in training)
        hr=sum(x['trials'] for x in holdout); hf=sum(x['failures'] for x in holdout)
        lo,hi=wilson(tf,tr)
        p=tf/tr
        count=counts[op]
        runtime=sum(x['duration_us']*x['trials'] for x in training)/tr
        serial_runtime_us+=runtime*count
        # Conservative, componentwise envelope; NOT a simultaneous confidence bound.
        joint_success *= (1-p)**count
        joint_success_lower *= (1-hi)**count
        joint_success_upper *= (1-lo)**count
        hlo,hhi=wilson(hf,hr)
        estimated[op]={"protocol_id":next(iter(a)),"train_failures":tf,"train_trials":tr,
                       "train_error_rate":p,"train_wilson_95":[lo,hi],
                       "holdout_failures":hf,"holdout_trials":hr,
                       "holdout_error_rate":hf/hr,"holdout_wilson_95":[hlo,hhi],
                       "train_and_holdout_wilson_intervals_overlap": not (hi<hlo or hhi<lo),
                       "duration_us_observed_mean":runtime,"workload_operations":count}
    return {"schema":"ftqc.conditional-logical-composition.v1", "hardware_family":family,
            "device_id":device,"code_family":code,"workload_id":workload.get("id","unspecified"),
            "predicted_success_independent_primitives":joint_success,
            "componentwise_wilson_envelope_success":[joint_success_lower,joint_success_upper],
            "sum_of_serial_primitive_durations_us_no_overlap_assumed":serial_runtime_us,
            "primitives":estimated,
            "calibration_status":"self_reported_primitive_counts_not_independently_authenticated",
            "claim_scope":"conditional primitive-composition baseline only; NOT an end-to-end device-calibrated FTQC prediction",
            "missing_physics":["physical noise and correlated fault propagation", "native code-level circuit synthesis",
              "matched fault-tolerant logical gates and magic-state distillation", "decoder and feedforward deadlines",
              "parallel scheduling, routing and resource contention", "hardware-derived area and factory budgets",
              "independent source-to-shot verification and cross-layer held-out experiment"]}


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--observations',type=Path,required=True)
    p.add_argument('--workload',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    r=evaluate(json.loads(args.observations.read_text()),json.loads(args.workload.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print('Conditional model only:',args.output)

if __name__=='__main__':
    main()
