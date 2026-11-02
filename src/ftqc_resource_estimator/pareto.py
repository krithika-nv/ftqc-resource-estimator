"""Evaluate non-dominated scenarios on three *declared* heuristic metrics.

Only compare within a COMMON specified toy workload and same logical-error
ansatz; not a ranking of hardware platforms.
"""
from .model import Scenario,Estimate,estimate

def frontier(scenarios:list[Scenario], distances:list[int], logical_qubits:int,
             operations:int,target_failure:float)->list[Estimate]:
    estimates=[estimate(d,s,logical_qubits,operations,target_failure)
               for s in scenarios for d in distances]
    # A feasible point can be Pareto efficient in both resource and latency.
    feasible=[e for e in estimates if e.target_satisfied]
    def dominates(a:Estimate,b:Estimate)->bool:
        dims_a=(a.physical_sites,a.latency_microseconds,a.total_failure_probability)
        dims_b=(b.physical_sites,b.latency_microseconds,b.total_failure_probability)
        return all(x<=y for x,y in zip(dims_a,dims_b)) and any(x<y for x,y in zip(dims_a,dims_b))
    return sorted([b for b in feasible if not any(dominates(a,b) for a in feasible if a is not b)],
                  key=lambda e:(e.physical_sites,e.latency_microseconds,e.scenario,e.distance))
