"""Transparent *heuristic* surface-code architecture cost model.

Not fitted to a specific device, paper dataset or simulated decoder.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Scenario:
    name: str
    physical_error: float
    threshold_assumption: float
    prefactor: float
    cycle_microseconds: float
    decode_microseconds: float

@dataclass(frozen=True)
class Estimate:
    scenario: str
    distance: int
    logical_error_per_operation: float
    total_failure_probability: float
    physical_sites: int
    latency_microseconds: float
    site_microseconds: float
    target_satisfied: bool

def logical_error_heuristic(distance: int, scenario: Scenario) -> float:
    """A *chosen ansatz* A * (p / p_th)^((d+1)/2), not a measured threshold."""
    if distance<3 or distance%2!=1:
        raise ValueError('code distance must be odd and >= 3')
    if not 0<scenario.physical_error<scenario.threshold_assumption<1:
        raise ValueError('requires 0 < p < assumed threshold < 1')
    if scenario.prefactor<=0 or scenario.cycle_microseconds<=0 or scenario.decode_microseconds<0:
        raise ValueError('nonpositive model parameter')
    return min(1.0,scenario.prefactor * (scenario.physical_error/scenario.threshold_assumption)**((distance+1)/2))

def estimate(distance:int,scenario:Scenario,logical_qubits:int,operations:int,
             target_failure:float) -> Estimate:
    if logical_qubits<1 or operations<1 or not 0<target_failure<1:
        raise ValueError('positive logical qubits/operations and target in (0,1) required')
    pl=logical_error_heuristic(distance,scenario)
    # Independent-operation approximation; stable even for tiny p_L.
    fail=-math.expm1(logical_qubits*operations*math.log1p(-pl)) if pl<1 else 1.0
    physical_sites=(2*distance*distance-1)*logical_qubits  # toy rotated patch + checks
    latency=operations*(distance*scenario.cycle_microseconds+scenario.decode_microseconds)
    return Estimate(scenario.name,distance,pl,fail,physical_sites,latency,
                    physical_sites*latency,fail<=target_failure)

def choose_distance(scenario:Scenario,logical_qubits:int,operations:int,
                    target_failure:float,distances=range(3,20,2)) -> Estimate|None:
    candidates=[estimate(d,scenario,logical_qubits,operations,target_failure) for d in distances]
    feasible=[x for x in candidates if x.target_satisfied]
    return min(feasible,key=lambda x:(x.site_microseconds,x.distance)) if feasible else None
