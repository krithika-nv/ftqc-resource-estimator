"""Independent finite-workload supply queue sanity check.

Successful *heralded* delivery events are modeled as a Poisson process with
rate=number_of_factories * attempt_rate * per-attempt-success. This model is
NOT a photonic quantum optical network simulator. Its purpose is to expose the
startup/stochastic-queuing effects omitted by the idealized throughput envelope.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import random
import statistics
from .architecture import Architecture, Workload


@dataclass(frozen=True)
class QueueStats:
    trials: int
    mean_us: float
    standard_deviation_us: float
    percentile_05_us: float
    percentile_95_us: float
    ideal_envelope_us: float


def sample_latency(arch:Architecture, distance:int, work:Workload, rng:random.Random) -> float:
    if distance<3 or distance%2!=1:
        raise ValueError('distance must be odd and >=3')
    demand=work.logical_qubits*work.resources_per_qubit_layer
    if demand != int(demand):
        raise ValueError('queue model requires an integer number of units per layer')
    demand=int(demand)
    delivery_rate=arch.supply.delivered_per_us
    compute_time=distance*arch.noise.cycle_microseconds+arch.noise.decode_microseconds
    next_delivery=rng.expovariate(delivery_rate)
    ready=0.0
    available=0
    for _ in range(work.logical_layers):
        # Resource preparation continues independently while computation runs.
        while next_delivery<=ready:
            available+=1
            next_delivery+=rng.expovariate(delivery_rate)
        # Block if the layer's resource bundle is not yet in the buffer.
        while available<demand:
            ready=next_delivery
            available+=1
            next_delivery+=rng.expovariate(delivery_rate)
        available-=demand
        ready+=compute_time
    return ready


def sample_statistics(arch:Architecture,distance:int,work:Workload,
                      *,trials:int=200,seed:int=2026) -> QueueStats:
    if not isinstance(trials,int) or trials<2:
        raise ValueError('require at least 2 trials')
    rng=random.Random(seed)
    runs=sorted(sample_latency(arch,distance,work,rng) for _ in range(trials))
    ideal=max(work.logical_layers*(distance*arch.noise.cycle_microseconds+arch.noise.decode_microseconds),
              work.logical_layers*work.logical_qubits*work.resources_per_qubit_layer/arch.supply.delivered_per_us)
    return QueueStats(trials,statistics.mean(runs),statistics.stdev(runs),
                      runs[int(.05*(trials-1))],runs[int(.95*(trials-1))],ideal)
