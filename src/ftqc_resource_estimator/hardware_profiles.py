"""Original, transparent *un-calibrated* hardware-specific scheduling proxies.

These are scenario sensitivity calculators, not device models. In particular,
photo-optical resource attempts cannot be counted as qubits or equated to
surface-code ancilla sites. This module intentionally returns native units.

The Stim experiment is a common algorithmic QEC reference only; its results
are never re-labelled as platform-specific memory or logical-gate fidelity.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math


def _positive(name: str, value: float) -> None:
    if not isinstance(value,(int,float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be positive and finite')


def _nonnegative(name: str, value: float) -> None:
    if not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be nonnegative and finite')


def _integer(name: str, value: int, *, minimum: int = 1) -> None:
    if not isinstance(value,int) or isinstance(value,bool) or value < minimum:
        raise ValueError(f'{name} must be integer >= {minimum}')


@dataclass(frozen=True)
class ReferenceWorkload:
    """The same *synthetic* scheduling demand is used for sensitivity analyses."""
    distance: int
    logical_qubits: int
    syndrome_rounds_per_window: int
    memory_windows: int

    def __post_init__(self):
        _integer('distance',self.distance,minimum=3)
        if self.distance % 2 != 1: raise ValueError('distance must be odd')
        for field in ('logical_qubits','syndrome_rounds_per_window','memory_windows'):
            _integer(field,getattr(self,field))

    @property
    def total_rounds(self) -> int:
        return self.syndrome_rounds_per_window * self.memory_windows

    @property
    def surface_patch_sites(self) -> int:
        # Schematic layout, not hardware specific. No geometry/routing computed.
        return self.logical_qubits*(2*self.distance**2-1)


@dataclass(frozen=True)
class PhotonicScenario:
    name: str
    sources: int
    source_attempts_per_us: float
    heralding_success: float
    path_transmission: tuple[float,...]
    # In the very simplified demand model, one resource-state equivalent per
    # logical patch per syndrome round; not a photon count or a GKP factory.
    state_equivalents_per_patch_round: float
    measurement_us_per_round: float
    feedforward_us_per_round: float

    def __post_init__(self):
        if not self.name.strip(): raise ValueError('name required')
        _integer('sources',self.sources)
        for name in ('source_attempts_per_us','state_equivalents_per_patch_round'):
            _positive(name,getattr(self,name))
        for name in ('measurement_us_per_round','feedforward_us_per_round'):
            _nonnegative(name,getattr(self,name))
        if not 0<self.heralding_success<=1: raise ValueError('invalid heralding success')
        if not self.path_transmission or any(not 0<t<=1 for t in self.path_transmission):
            raise ValueError('path transmission must be nonempty with each value in (0,1]')

    def evaluate(self,w:ReferenceWorkload)->dict:
        delivery_p=self.heralding_success*math.prod(self.path_transmission)
        required=w.logical_qubits*w.total_rounds*self.state_equivalents_per_patch_round
        rate=self.sources*self.source_attempts_per_us*delivery_p
        supply_us=required/rate
        measurement_us=w.total_rounds*(self.measurement_us_per_round+self.feedforward_us_per_round)
        return dict(profile='photonic',scenario=self.name,model='illustrative_resource_delivery',
                    runtime_us=max(supply_us,measurement_us),supply_us=supply_us,
                    critical_path_us=measurement_us,delivery_probability=delivery_p,
                    expected_attempts=required/delivery_p,
                    state_equivalents_required=required,
                    sources=self.sources,resource_unit='heralded_resource_state_equivalent',
                    dominant_bottleneck='supply' if supply_us>measurement_us else 'measurement_and_feedforward')


@dataclass(frozen=True)
class SuperconductingScenario:
    name: str
    one_qubit_us: float
    two_qubit_us: float
    readout_reset_us: float
    decode_us_per_window: float
    one_qubit_layers_per_round: int
    two_qubit_layers_per_round: int
    extra_routing_layers_per_round: int = 0

    def __post_init__(self):
        if not self.name.strip():raise ValueError('name required')
        for field in ('one_qubit_us','two_qubit_us','readout_reset_us','decode_us_per_window'):
            _nonnegative(field,getattr(self,field))
        for field in ('one_qubit_layers_per_round','two_qubit_layers_per_round','extra_routing_layers_per_round'):
            _integer(field,getattr(self,field),minimum=0)
        if self.one_qubit_layers_per_round+self.two_qubit_layers_per_round==0:
            raise ValueError('must include quantum operations per round')

    def evaluate(self,w:ReferenceWorkload)->dict:
        per_round=(self.one_qubit_layers_per_round*self.one_qubit_us +
                   (self.two_qubit_layers_per_round+self.extra_routing_layers_per_round)*self.two_qubit_us +
                   self.readout_reset_us)
        compute_us=w.total_rounds*per_round
        decode_us=w.memory_windows*self.decode_us_per_window
        return dict(profile='superconducting',scenario=self.name,model='illustrative_gate_schedule',
                    runtime_us=compute_us+decode_us,critical_path_us=compute_us,
                    decoder_us=decode_us,nominal_patch_qubits=w.surface_patch_sites,
                    resource_unit='nominal_data_and_syndrome_qubits',
                    dominant_bottleneck='specified_serial_gate_and_readout_schedule')


@dataclass(frozen=True)
class TrappedIonScenario:
    name: str
    entangling_gate_us: float
    transport_us: float
    readout_reset_us: float
    decode_us_per_window: float
    gates_per_patch_round: int
    transfers_per_patch_round: int
    parallel_gate_zones: int
    parallel_transport_zones: int

    def __post_init__(self):
        if not self.name.strip():raise ValueError('name required')
        for field in ('entangling_gate_us','transport_us','readout_reset_us','decode_us_per_window'):
            _nonnegative(field,getattr(self,field))
        for field in ('gates_per_patch_round','transfers_per_patch_round'):
            _integer(field,getattr(self,field),minimum=0)
        if self.gates_per_patch_round==0:raise ValueError('must have entangling gates')
        _integer('parallel_gate_zones',self.parallel_gate_zones)
        _integer('parallel_transport_zones',self.parallel_transport_zones)

    def evaluate(self,w:ReferenceWorkload)->dict:
        # This deliberately uses an assumed count, not a derived shuttling network.
        gates=math.ceil(w.logical_qubits*self.gates_per_patch_round/self.parallel_gate_zones)
        moves=math.ceil(w.logical_qubits*self.transfers_per_patch_round/self.parallel_transport_zones)
        per_round=gates*self.entangling_gate_us+moves*self.transport_us+self.readout_reset_us
        compute_us=w.total_rounds*per_round
        decode_us=w.memory_windows*self.decode_us_per_window
        return dict(profile='trapped_ion',scenario=self.name,model='illustrative_zoned_serial_schedule',
                    runtime_us=compute_us+decode_us,critical_path_us=compute_us,
                    decoder_us=decode_us,entangling_slots_per_round=gates,
                    transport_slots_per_round=moves,
                    nominal_patch_ions=w.surface_patch_sites,
                    resource_unit='nominal_data_and_syndrome_ions',
                    dominant_bottleneck='serialized_zoned_gate_and_transport_schedule')


PROFILE_CLASSES={
    'photonic':PhotonicScenario,
    'superconducting':SuperconductingScenario,
    'trapped_ion':TrappedIonScenario,
}


def from_record(record:dict):
    """Strict config parser prevents a photonic model masquerading as an ion one."""
    record=dict(record)
    which=record.pop('profile')
    if which not in PROFILE_CLASSES:raise ValueError(f'unknown profile: {which}')
    if which=='photonic' and 'path_transmission' in record:
        record['path_transmission']=tuple(record['path_transmission'])
    return PROFILE_CLASSES[which](**record)
