"""Hardware-independent statistical budget planning for logical-memory experiments.

No numerical observations are created.  The formulas answer how many Bernoulli
trials are needed before a *zero-failure* result could even clear a specified
workload error budget with a two-sided Wilson interval.  This is a planning
bound, not a promise that a noisy experiment will have zero failures.
"""
from __future__ import annotations
import argparse
import json
import math

# 97.5th percentile of the standard normal; two-sided nominal 95% CI.
Z95 = 1.959963984540054


def allowed_memory_error(target_failure: float, logical_qubits: int, memory_windows: int) -> float:
    """Per-memory-event limit under the explicitly assumed independent-event model."""
    if not (math.isfinite(target_failure) and 0 < target_failure < 1):
        raise ValueError('target_failure must be finite in (0,1)')
    if (not isinstance(logical_qubits, int) or isinstance(logical_qubits,bool) or logical_qubits < 1 or
        not isinstance(memory_windows,int) or isinstance(memory_windows,bool) or memory_windows < 1):
        raise ValueError('logical_qubits and memory_windows must be positive integers')
    return -math.expm1(math.log1p(-target_failure)/(logical_qubits*memory_windows))


def zero_failures_upper95(shots: int) -> float:
    """Two-sided Wilson upper 95% limit for 0 successes out of N Bernoulli trials."""
    if not isinstance(shots,int) or isinstance(shots,bool) or shots < 1:
        raise ValueError('shots must be positive integer')
    z2 = Z95**2
    return z2/(shots+z2)


def minimum_shots_if_zero_failures(per_event_budget: float) -> int:
    """Smallest N for which zero observed failures WOULD pass nominal Wilson 95%.

    Does not adjust for simultaneous multiple comparisons, model error, or
    dependence between observed windows, and may be insufficient if failures occur.
    """
    if not (math.isfinite(per_event_budget) and 0 < per_event_budget < 1):
        raise ValueError('per_event_budget must be finite in (0,1)')
    guess = max(1, int(math.ceil((Z95**2)*(1-per_event_budget)/per_event_budget)))
    while zero_failures_upper95(guess) > per_event_budget:
        guess+=1
    while guess>1 and zero_failures_upper95(guess-1)<=per_event_budget:
        guess-=1
    return guess


def plan(target_failure:float,logical_qubits:int,memory_windows:int,shots:int)->dict:
    allowable=allowed_memory_error(target_failure,logical_qubits,memory_windows)
    upper=zero_failures_upper95(shots)
    minimum=minimum_shots_if_zero_failures(allowable)
    return {
        'target_total_failure':target_failure,
        'independent_memory_events':logical_qubits*memory_windows,
        'per_event_failure_budget':allowable,
        'planned_shots_per_circuit':shots,
        'minimum_shots_per_circuit_if_zero_failures':minimum,
        'zero_failure_wilson_upper95_at_planned_shots':upper,
        'zero_failures_could_pass_nominal_budget':upper<=allowable,
        'assumptions':'independent memory events; fixed circuit/noise/basis/rounds; two-sided nominal Wilson 95%; zero hypothetical observed failures',
        'limitations':'NOT expected sample sufficiency for nonzero errors; NOT simultaneous coverage across distances; NOT a hardware threshold or FT gate forecast',
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description='Analytical sample-planning check; no Stim numerical results generated')
    p.add_argument('--target-failure',type=float,default=.1)
    p.add_argument('--logical-qubits',type=int,default=4)
    p.add_argument('--memory-windows',type=int,default=10)
    p.add_argument('--shots',type=int,default=20000)
    a=p.parse_args(argv)
    print(json.dumps(plan(a.target_failure,a.logical_qubits,a.memory_windows,a.shots),indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
