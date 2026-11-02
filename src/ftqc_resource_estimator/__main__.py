import argparse, csv
from dataclasses import asdict
from pathlib import Path
from .model import Scenario,estimate,choose_distance
def main():
    ap=argparse.ArgumentParser(description='Compare assumption-driven logical architecture scenarios')
    ap.add_argument('--output',default='outputs/scenarios.csv')
    ap.add_argument('--operations',type=int,default=1000)
    ap.add_argument('--logical-qubits',type=int,default=10)
    ap.add_argument('--target',type=float,default=.01)
    ap.add_argument('--physical-error',type=float,default=.001)
    a=ap.parse_args()
    common=dict(physical_error=a.physical_error,threshold_assumption=.01,prefactor=.1)
    scenarios=[Scenario('reference_timing',cycle_microseconds=1.0,decode_microseconds=5.0,**common),
               Scenario('lower_measurement_latency',cycle_microseconds=.35,decode_microseconds=9.0,**common)]
    rows=[asdict(estimate(d,s,a.logical_qubits,a.operations,a.target)) for s in scenarios for d in range(3,16,2)]
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for s in scenarios:
        best=choose_distance(s,a.logical_qubits,a.operations,a.target,range(3,16,2))
        print(f'{s.name}: '+(f'd={best.distance}, sites={best.physical_sites}, latency_us={best.latency_microseconds:.2f}' if best else 'no feasible d in search grid'))
    print(f'Wrote {path}; all results are heuristic scenarios, NOT device predictions')
if __name__=='__main__':main()
