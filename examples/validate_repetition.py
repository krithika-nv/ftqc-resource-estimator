"""Sanity-check exact majority vote against INDEPENDENT Monte Carlo bit flips.

Not a surface-code simulator or photonic threshold calibration. Uses only Python stdlib.
"""
from __future__ import annotations
import csv
import random
from pathlib import Path
from ftqc_resource_estimator.reliability import repetition_failure_exact,wilson


def simulate(distance:int,p:float,shots:int,rng:random.Random):
    failures=0
    for _ in range(shots):
        count=sum(rng.random()<p for _ in range(distance))
        failures+=count>(distance//2)
    return failures


def main():
    out=Path('outputs/repetition_sanity.csv');out.parent.mkdir(parents=True,exist_ok=True)
    shots=30000
    p=.08
    rng=random.Random(20261025)
    rows=[]
    for d in (3,5,7,9):
        failures=simulate(d,p,shots,rng)
        ci=wilson(failures,shots)
        exact=repetition_failure_exact(d,p)
        rows.append({'code_family':'repetition','experiment':'memory_one_round','distance':d,
                     'physical_error':p,'shots':shots,'failures':failures,
                     'estimate':ci.mean,'wilson_low':ci.lower,'wilson_high':ci.upper,
                     'exact_probability':exact,'exact_inside_interval':ci.lower<=exact<=ci.upper})
    with out.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(f'Analytic vs Monte Carlo repetition-code check (not surface-code), p={p}, seed=20261025')
    for r in rows:
        print(f'd={r["distance"]}, observed={r["estimate"]:.6g} [{r["wilson_low"]:.6g}, {r["wilson_high"]:.6g}], exact={r["exact_probability"]:.6g}, interval_covers={r["exact_inside_interval"]}')
    print(f'Wrote {out}')

if __name__=='__main__':main()
