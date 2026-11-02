"""Architecture layers kept separate: QEC reliability, patches, scheduling, supply.

Scope: hypothetical surface-code storage patches with an abstract heralded
resource supply. NO full photonic GKP/QEC or magic-state distillation model.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from .model import Scenario, logical_error_heuristic
from .reliability import ErrorRate, EmpiricalTable, propagate


@dataclass(frozen=True)
class Workload:
    logical_qubits: int
    logical_layers: int
    target_failure: float
    resources_per_qubit_layer: float = 1.0
    def __post_init__(self):
        if not isinstance(self.logical_qubits,int) or self.logical_qubits<1:
            raise ValueError('logical qubits must be a positive integer')
        if not isinstance(self.logical_layers,int) or self.logical_layers<1:
            raise ValueError('logical layers must be a positive integer')
        if not 0 < self.target_failure < 1:
            raise ValueError('target total failure must lie in (0,1)')
        if not math.isfinite(self.resources_per_qubit_layer) or self.resources_per_qubit_layer<=0:
            raise ValueError('resources_per_qubit_layer must be positive')


@dataclass(frozen=True)
class ResourceSupply:
    factories: int
    attempts_per_factory_per_us: float
    preparation_success: float
    path_transmissions: tuple[float,...]
    factory_site_equivalents: int = 0
    def __post_init__(self):
        if not isinstance(self.factories,int) or self.factories<1 or self.factory_site_equivalents<0:
            raise ValueError('factory counts positive; factory site equivalents >=0')
        if self.attempts_per_factory_per_us <= 0 or not math.isfinite(self.attempts_per_factory_per_us):
            raise ValueError('attempt rate must be positive and finite')
        if not 0 < self.preparation_success <= 1 or any(not 0<t<=1 for t in self.path_transmissions):
            raise ValueError('probabilities must be in (0,1]')

    @property
    def delivery_probability(self) -> float:
        return self.preparation_success * math.prod(self.path_transmissions)

    @property
    def delivered_per_us(self) -> float:
        return self.factories*self.attempts_per_factory_per_us*self.delivery_probability


@dataclass(frozen=True)
class Architecture:
    name: str
    noise: Scenario
    supply: ResourceSupply
    # Quibit sites in rotated memory patches PLUS explicitly assumed factory-site equivalents.
    # All quantities are toy *sites*, not physical photons or fully laid out factories.
    extra_patch_fraction: float = 0.0
    def __post_init__(self):
        if not self.name.strip() or self.extra_patch_fraction < 0 or not math.isfinite(self.extra_patch_fraction):
            raise ValueError('invalid architecture name or extra patch fraction')


@dataclass(frozen=True)
class ArchitectureResult:
    architecture: str
    distance: int
    reliability_source: str
    mean_failure: float
    lower_failure: float
    upper_failure: float
    model_feasible_mean: bool
    model_feasible_upper: bool
    data_sites: int
    syndrome_sites: int
    reserve_sites: int
    factory_site_equivalents: int
    total_site_equivalents: int
    compute_us: float
    supply_us: float
    latency_us: float
    bottleneck: str
    delivery_probability: float
    expected_preparation_attempts: float
    site_equivalent_us: float
    # mean failure rate includes independent-location approximation; no joint statistical guarantee.

    def row(self) -> dict[str,object]:
        return asdict(self)


def evaluate(arch: Architecture, distance: int, workload: Workload,
             empirical: EmpiricalTable|None = None, *,
             experiment: str = 'logical_layer', code_family: str = 'rotated_surface') -> ArchitectureResult:
    """Either an explicitly heuristic model OR matching empirical logical data.

    Experiments defined in a CSV must be per logical layer of this exact
    workload type. A memory experiment cannot silently stand in for a gate.
    """
    if distance < 3 or distance%2 == 0:
        raise ValueError('distance must be odd >=3 for the hypothetical rotated patch')
    if empirical is not None:
        if code_family != 'rotated_surface' or experiment != 'logical_layer':
            raise ValueError('estimator only models rotated_surface logical_layer observations')
        rate = empirical.lookup(code_family,experiment,arch.noise.physical_error,distance)
    else:
        p = logical_error_heuristic(distance,arch.noise)
        rate = ErrorRate(p,p,p,'illustrative_surface_heuristic_NO_uncertainty')
    failure = propagate(rate,workload.logical_qubits*workload.logical_layers)
    data_sites = distance**2*workload.logical_qubits
    syndrome_sites = (distance**2-1)*workload.logical_qubits
    reserve_sites = math.ceil((data_sites+syndrome_sites)*arch.extra_patch_fraction)
    factory_sites = arch.supply.factories*arch.supply.factory_site_equivalents
    sites = data_sites+syndrome_sites+reserve_sites+factory_sites
    compute_us = workload.logical_layers*(distance*arch.noise.cycle_microseconds + arch.noise.decode_microseconds)
    delivered = workload.logical_qubits*workload.logical_layers*workload.resources_per_qubit_layer
    supply_us = delivered / arch.supply.delivered_per_us
    latency_us = max(compute_us,supply_us)   # idealized perfectly overlapped pipelines
    bottleneck = 'supply' if supply_us > compute_us else 'compute'
    attempts = delivered / arch.supply.delivery_probability
    return ArchitectureResult(arch.name,distance,failure.source,failure.mean,failure.lower,
           failure.upper,failure.mean <= workload.target_failure,
           failure.upper <= workload.target_failure, data_sites,syndrome_sites,reserve_sites,
           factory_sites,sites,compute_us,supply_us,latency_us,bottleneck,
           arch.supply.delivery_probability,attempts,sites*latency_us)


def pareto(results: list[ArchitectureResult], *, robust: bool = False) -> list[ArchitectureResult]:
    """Nondominated site-time, site count, and latency among same-workload feasible designs.

    Reliability is a constraint, NOT implicitly interchangeable with cost.
    """
    eligible = ([r for r in results if r.model_feasible_upper] if robust
                else [r for r in results if r.model_feasible_mean])
    def dominates(a:ArchitectureResult,b:ArchitectureResult)->bool:
        x=(a.total_site_equivalents,a.latency_us,a.site_equivalent_us)
        y=(b.total_site_equivalents,b.latency_us,b.site_equivalent_us)
        return all(u<=v for u,v in zip(x,y)) and any(u<v for u,v in zip(x,y))
    return sorted((r for r in eligible if not any(dominates(a,r) for a in eligible if a is not r)),
                  key=lambda r:(r.total_site_equivalents,r.latency_us,r.architecture,r.distance))
