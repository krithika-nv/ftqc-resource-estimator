"""Reproducible independent event simulation exposing ideal-envelope limitations."""
import csv
from dataclasses import replace
from pathlib import Path
from ftqc_resource_estimator.study import load_configuration
from ftqc_resource_estimator.architecture import Workload
from ftqc_resource_estimator.queue_simulation import sample_statistics


def main():
    _,designs,_=load_configuration(Path('examples/architecture_scenarios.json'))
    small=Workload(logical_qubits=4,logical_layers=30,target_failure=.1)
    examples=[]
    # Choose multiple supply rates to illustrate supply- and compute-limited regimes.
    for rate in (1.0,3.0,10.0,30.0):
        a=replace(designs[0],supply=replace(designs[0].supply,attempts_per_factory_per_us=rate))
        s=sample_statistics(a,11,small,trials=350,seed=20261025)
        examples.append({'attempt_rate_per_us':rate,'successful_delivery_rate_per_us':a.supply.delivered_per_us,
                         'trials':s.trials,'mean_latency_us':s.mean_us,'sd_latency_us':s.standard_deviation_us,
                         'p05_latency_us':s.percentile_05_us,'p95_latency_us':s.percentile_95_us,
                         'infinite_stream_envelope_us':s.ideal_envelope_us})
    out=Path('outputs/queue_sanity.csv');out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(examples[0]));w.writeheader();w.writerows(examples)
    for r in examples:
        print(f'attempt rate={r["attempt_rate_per_us"]:g}/us: mean={r["mean_latency_us"]:.2f} us, '
              f'ideal envelope={r["infinite_stream_envelope_us"]:.2f} us '
              f'(350 trials; simplified Poisson success process)')
    print(f'Wrote {out}')

if __name__=='__main__':main()
