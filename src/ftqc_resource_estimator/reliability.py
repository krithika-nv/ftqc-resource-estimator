"""Reliable numerical bookkeeping, NOT an error-correction decoder.

Empirical logical error observations must specify their code family, circuit
experiment, physical error, distance, trial count and failure count.  We do not
interpolate or extrapolate these observations: each supported comparison uses
an exactly matched (code, experiment, physical_error, distance) observation.
"""
from __future__ import annotations
from dataclasses import dataclass
from csv import DictReader
from pathlib import Path
from statistics import NormalDist
import math


@dataclass(frozen=True)
class ErrorRate:
    mean: float
    lower: float
    upper: float
    source: str
    observations: int | None = None
    failures: int | None = None
    def __post_init__(self):
        if not 0 <= self.lower <= self.mean <= self.upper <= 1:
            raise ValueError('requires 0 <= lower <= mean <= upper <= 1')


def wilson(failures: int, shots: int, confidence: float = 0.95) -> ErrorRate:
    """Two-sided Wilson score interval (no false zero uncertainty)."""
    if not isinstance(failures, int) or not isinstance(shots, int) or shots <= 0 or not 0 <= failures <= shots:
        raise ValueError('shots and failures must be integers, 0 <= failures <= shots, shots > 0')
    if not 0 < confidence < 1:
        raise ValueError('confidence must lie in (0, 1)')
    z = NormalDist().inv_cdf(0.5 + confidence/2)
    phat = failures / shots
    denom = 1 + z*z/shots
    middle = (phat + z*z/(2*shots)) / denom
    radius = z/denom * math.sqrt(phat*(1-phat)/shots + z*z/(4*shots*shots))
    return ErrorRate(phat, min(phat, max(0, middle-radius)), max(phat, min(1, middle+radius)),
                     f'empirical_wilson_{confidence:g}', shots, failures)


def cumulative_failure(rate: float, locations: int) -> float:
    """Independent equally risky logical locations; stable for tiny probabilities."""
    if not 0 <= rate <= 1 or locations < 0 or not isinstance(locations, int):
        raise ValueError('invalid rate or locations')
    if rate == 1:
        return float(bool(locations))
    return -math.expm1(locations*math.log1p(-rate))


def propagate(rate: ErrorRate, locations: int) -> ErrorRate:
    return ErrorRate(cumulative_failure(rate.mean, locations),
                     cumulative_failure(rate.lower, locations),
                     cumulative_failure(rate.upper, locations),
                     rate.source+' / independence_assumption',
                     rate.observations, rate.failures)


@dataclass(frozen=True)
class Measurement:
    code_family: str
    experiment: str  # e.g. 'memory_d_rounds'; NOT a generic gate error
    physical_error: float
    distance: int
    shots: int
    failures: int
    def __post_init__(self):
        if not self.code_family.strip() or not self.experiment.strip():
            raise ValueError('code family and experiment are required')
        if not 0 <= self.physical_error <= 1:
            raise ValueError('physical error must be a probability')
        if not isinstance(self.distance,int) or self.distance < 1:
            raise ValueError('distance must be a positive integer')
        wilson(self.failures, self.shots)


class EmpiricalTable:
    """Supports exact matching only. Cannot use repetition data for surface codes."""
    def __init__(self, measurements: list[Measurement]):
        self._data: dict[tuple[str,str,float,int], tuple[int,int]] = {}
        for m in measurements:
            key = (m.code_family,m.experiment,m.physical_error,m.distance)
            shots,failures = self._data.get(key,(0,0))
            self._data[key] = shots+m.shots, failures+m.failures

    @classmethod
    def from_csv(cls, path: str | Path) -> 'EmpiricalTable':
        with open(path, newline='', encoding='utf-8') as f:
            reader = DictReader(f)
            required = {'code_family','experiment','physical_error','distance','shots','failures'}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError('empirical CSV needs ' + ', '.join(sorted(required)))
            measurements = [Measurement(row['code_family'],row['experiment'],
                            float(row['physical_error']),int(row['distance']),
                            int(row['shots']),int(row['failures'])) for row in reader]
        if not measurements:
            raise ValueError('empirical CSV is empty')
        return cls(measurements)

    def lookup(self, code_family: str, experiment: str, physical_error: float, distance: int,
               *, confidence: float = 0.95) -> ErrorRate:
        key = (code_family,experiment,physical_error,distance)
        if key not in self._data:
            raise KeyError(f'no exact matched observation: {key!r}; no interpolation/extrapolation performed')
        shots,failures = self._data[key]
        return wilson(failures,shots,confidence)


def repetition_failure_exact(distance:int, p:float) -> float:
    """Odd-length bit-flip repetition memory: independent X errors + perfect decoding.

    Only an ideal *single-round bit-flip* memory toy. Not FTQC surface-code rate.
    """
    if distance<1 or distance%2==0 or not 0<=p<=1:
        raise ValueError('distance odd positive, 0 <= p <= 1')
    return math.fsum(math.comb(distance,k)*p**k*(1-p)**(distance-k)
                     for k in range(distance//2+1,distance+1))
