"""Literature-aligned surface-memory protocol, not a reproduction of digitized paper points.

Matches the public Riverlane/Deltakit Stim+PyMatching teaching example:
rotated X memory, r=d, four equal noise knobs, DEM(decompose_errors=True), MWPM.
Retains independent code, fixed-shots binomial uncertainty, seed/hash evidence.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform

from .stim_memory import simulate_memory, DECODER, NOISE_PROFILE
from .reliability import wilson

SCHEMA = 'ftqc.literature_aligned_rounds_equals_distance.v1'
REFERENCE = 'https://textbook.riverlane.com/en/latest/notebooks/ch5-decoding-surfcodes/simulating-surface-codes-stim.html'
DEFAULT_DISTANCES = (3, 5, 7, 9)
DEFAULT_ERRORS = (0.0, .003, .005, .007, .009)


def validate_benchmark(obj: dict, *, strict: bool = True) -> list[dict]:
    if obj.get('schema') != SCHEMA or obj.get('protocol', {}).get('reference_url') != REFERENCE:
        raise ValueError('unrecognized literature benchmark')
    p = obj['protocol']
    if (p.get('code') != 'surface_code:rotated_memory_x' or
        p.get('rounds_rule') != 'rounds=distance' or
        p.get('noise_profile') != NOISE_PROFILE or
        p.get('decoder') != DECODER or
        set(p.get('noise_knobs', [])) != {
            'after_clifford_depolarization','before_round_data_depolarization',
            'before_measure_flip_probability','after_reset_flip_probability'}):
        raise ValueError('protocol differs from the declared public reference')
    ds, ps = tuple(p['distances']), tuple(p['physical_errors'])
    if not ds or not ps or len(set(ds)) != len(ds) or len(set(ps)) != len(ps):
        raise ValueError('invalid sweep')
    if any(not isinstance(d,int) or d<3 or d%2!=1 for d in ds):
        raise ValueError('odd distances >=3 required')
    if any(not isinstance(q,(int,float)) or q<0 or q>=1 for q in ps):
        raise ValueError('invalid p')
    shots = p['shots_per_point']
    if not isinstance(shots,int) or shots<1: raise ValueError('invalid shots')
    observations = obj.get('observations', [])
    pairs = {(d,round(float(q),12)) for d in ds for q in ps}
    if len(observations)!=len(pairs): raise ValueError('missing observations')
    seen=set()
    for row in observations:
        d,q=row['distance'],row['physical_error']
        key=(d,round(float(q),12))
        if key not in pairs or key in seen: raise ValueError('missing, duplicate or foreign observation')
        seen.add(key)
        if (row.get('rounds') != d or row.get('observable_basis') != 'X' or
            row.get('code_family') != 'rotated_surface' or
            row.get('experiment') != 'memory_distance_scaled_rounds' or
            row.get('noise_profile') != NOISE_PROFILE or
            row.get('shots') != shots or
            row.get('decoder') != (DECODER if q>0 else 'noiseless_identity_control') or
            row.get('observables') != 1 or row.get('detectors',0)<1 or
            not row.get('circuit_sha256') or not row.get('detector_model_sha256') or
            not isinstance(row.get('seed'),int)):
            raise ValueError('observations not protocol-matched')
        failures=row.get('failures')
        if not isinstance(failures,int) or failures<0 or failures>shots:
            raise ValueError('invalid logical failure count')
        if q==0 and failures!=0: raise ValueError('noiseless control failed')
        if not isinstance(row.get('trivial_decoder_failures'),int) or not 0<=row['trivial_decoder_failures']<=shots:
            raise ValueError('invalid trivial control')
        if q>0 and row.get('batch_single_agreement_checked_shots',0) < min(shots,16):
            raise ValueError('missing batch/single decode verification')
    # The generated index order and seeds are part of the reproducible protocol.
    seed_base = p.get('seed_base')
    if not isinstance(seed_base,int):raise ValueError('missing seed base')
    for i,r in enumerate(observations):
        if r['seed'] != seed_base+i:
            raise ValueError('seeds do not follow declared generation order')
    expected_order=[(d,round(float(q),12)) for q in ps for d in ds]
    if [(r['distance'],round(float(r['physical_error']),12)) for r in observations]!=expected_order:
        raise ValueError('sweep ordering differs from reference protocol')
    if strict and (tuple(ds)!=DEFAULT_DISTANCES or tuple(float(x) for x in ps)!=DEFAULT_ERRORS or shots!=20000):
        raise ValueError('required published-reference benchmark grid must be complete')
    return observations


def run_benchmark(*, shots=20000, seed=20261028) -> dict:
    import stim
    import pymatching
    import numpy
    observations=[]
    for i,(p,d) in enumerate((p,d) for p in DEFAULT_ERRORS for d in DEFAULT_DISTANCES):
        result=simulate_memory(stim,pymatching,distance=d,rounds=d,physical_error=p,
                               shots=shots,seed=seed+i,basis='X')
        result['experiment']='memory_distance_scaled_rounds'
        observations.append(result)
        print(f'literature-match d={d}, rounds={d}, p={p:g}: {result["failures"]}/{shots}',flush=True)
    obj={'schema': SCHEMA, 'generated_utc':datetime.now(timezone.utc).isoformat(),
         'software':{'stim':stim.__version__,'pymatching':pymatching.__version__,
                     'numpy':numpy.__version__,'python':platform.python_version()},
         'protocol':{'reference_url':REFERENCE,'code':'surface_code:rotated_memory_x',
                     'rounds_rule':'rounds=distance','basis':'X','noise_profile':NOISE_PROFILE,
                     'decoder':DECODER,'noise_knobs':['after_clifford_depolarization',
                     'before_round_data_depolarization','before_measure_flip_probability',
                     'after_reset_flip_probability'],
                     'distances':list(DEFAULT_DISTANCES), 'physical_errors':list(DEFAULT_ERRORS),
                     'shots_per_point':shots,'seed_base':seed,
                     'warning':'Protocol-level match to the textbook, not digitized figure-value replication; seeded RNG may change across library versions.'},
         'observations':observations}
    validate_benchmark(obj,strict=shots==20000)
    return obj


def replay_benchmark(obj: dict) -> None:
    import stim,pymatching
    validate_benchmark(obj)
    if (obj['software'].get('stim') != stim.__version__ or
        obj['software'].get('pymatching') != pymatching.__version__):
        raise ValueError('replay requires the same Stim and PyMatching versions')
    for row in obj['observations']:
        now=simulate_memory(stim,pymatching,distance=row['distance'],rounds=row['distance'],
                            physical_error=row['physical_error'],shots=row['shots'],
                            seed=row['seed'],basis='X')
        for key in ['failures','trivial_decoder_failures','circuit_sha256',
                    'detector_model_sha256','detectors','observables']:
            if now[key] != row.get(key):
                raise ValueError(f'replay failed at d={row["distance"]} p={row["physical_error"]}: {key}')


def crossover_diagnostics(rows:list[dict]) -> list[str]:
    """Report overlaps, not an unjustified point threshold estimate."""
    pairs={(r['distance'],r['physical_error']):r for r in rows}
    result=[]
    for p in DEFAULT_ERRORS[1:]:
        a,b=pairs[(3,p)],pairs[(9,p)]
        lo=wilson(a['failures'],a['shots'])
        hi=wilson(b['failures'],b['shots'])
        if hi.upper < lo.lower: label='distance 9 clearly lower (nonoverlapping marginal 95% intervals)'
        elif lo.upper < hi.lower: label='distance 9 clearly higher (nonoverlapping marginal 95% intervals)'
        else: label='inconclusive / overlapping marginal 95% intervals'
        result.append(f'p={p:g}: d3={lo.mean:.5f}, d9={hi.mean:.5f}; {label}')
    return result


def report_benchmark(obj:dict,out:Path) -> None:
    rows=validate_benchmark(obj)
    out.mkdir(parents=True,exist_ok=True)
    table=[]
    for r in sorted(rows,key=lambda v:(v['physical_error'],v['distance'])):
        ci=wilson(r['failures'],r['shots'])
        table.append({'distance':r['distance'],'rounds':r['rounds'],'physical_error':r['physical_error'],
                      'shots':r['shots'],'failures':r['failures'],'logical_failure':ci.mean,
                      'wilson_low95':ci.lower,'wilson_upper95':ci.upper,
                      'circuit_sha256':r['circuit_sha256'],'seed':r['seed']})
    with (out/'round_scaled_results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    notes=['# Literature-aligned distance-scaled memory benchmark','',
           f'**Protocol reference:** {REFERENCE}',
           '**Scientific lineage:** the public Riverlane/Deltakit textbook uses Stim rotated-X surface memory, rounds equal to distance, four equal circuit-noise parameters, and PyMatching/MWPM.',
           '**Important:** this is an independently executed, *protocol-matched subset* of its parameter sweep; **not** an exact numerical reproduction of an identified panel, a calibrated physical threshold, or a new decoder.',
           f'**Sweep:** {len(table)} combinations, {obj["protocol"]["shots_per_point"]} shots each; Stim {obj["software"]["stim"]}; PyMatching {obj["software"]["pymatching"]}.','',
           '## Outcome', '',
           '| p | d | rounds | failures/shots | estimate | 95% Wilson interval |',
           '|---:|---:|---:|---:|---:|---:|']
    for r in table:
        notes.append(f'| {r["physical_error"]:.3g} | {r["distance"]} | {r["rounds"]} | {r["failures"]}/{r["shots"]} | {r["logical_failure"]:.5g} | [{r["wilson_low95"]:.5g}, {r["wilson_upper95"]:.5g}] |')
    notes+=['','## Pairwise diagnostics - not a numerical threshold fit','',
            *['- '+x for x in crossover_diagnostics(rows)],'',
            'The tutorial reports crossings around p≈0.007 using a **much denser/larger** study. Agreement of the qualitative direction in this small subset is only a sanity comparison. A rigorous numerical threshold reproduction would require the full grid, compatible versions and statistical precision.',
            'The existing nine-round distance-9 feasibility study tests a **different experiment length** than d=3,5,7 in this benchmark. Do not pool their rates or directly compare outcomes as equal-duration memories.','',
            '## Reproducibility','',
            'Run `./scripts/commands/RUN_LITERATURE_BENCHMARK.sh` with Stim/PyMatching installed; it regenerates, replays and audits this benchmark. No synthetic results are substituted.',
            '', '## Limitations','',
            '- Same numerical p assigned to four distinct error locations; no experimental noise calibration or correlation model.',
            '- Fixed shots per point and separate per-point Wilson intervals; no simultaneous confidence interval or finite-size scaling fit.',
            '- Per-experiment logical failure rate for r=d rounds; not a common-duration or per-round comparison.',
            '- Does not reproduce the 2025 O’Rourke–Devitt rotated-vs-unrotated comparison, which uses a broader protocol.']
    (out/'LITERATURE_COMPARISON.md').write_text('\n'.join(notes)+'\n')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8.5,5.3))
        for d in DEFAULT_DISTANCES:
            pts=[r for r in table if r['distance']==d and r['physical_error']>0]
            ax.errorbar([r['physical_error']*100 for r in pts],
                        [r['logical_failure']*100 for r in pts],
                        yerr=[[100*(r['logical_failure']-r['wilson_low95']) for r in pts],
                              [100*(r['wilson_upper95']-r['logical_failure']) for r in pts]],
                        marker='o',capsize=2,label=f'd={d}, rounds={d}')
        ax.axvline(.7,linestyle=':',color='gray',label='Reference qualitative crossover ~0.7%')
        ax.set_xlabel('Equal circuit noise parameter p (%)')
        ax.set_ylabel('Failure probability for a d-round memory (%)')
        ax.set_title('Literature-aligned rotated-X memory: independent subset, not figure digitization')
        ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout()
        fig.savefig(out/'round_scaled_curves.png',dpi=170);plt.close(fig)
    except ImportError:
        pass


def verify_saved(manifest:Path, output_dir:Path, certificate:Path) -> dict:
    raw=manifest.read_bytes();obj=json.loads(raw)
    validate_benchmark(obj)
    replay_benchmark(obj)
    report_benchmark(obj,output_dir)
    with (output_dir/'round_scaled_results.csv').open(newline='') as f:
        if len(list(csv.DictReader(f)))!=len(obj['observations']):raise RuntimeError('csv incomplete')
    cert={'status':'PASSED real Stim/PyMatching same-environment protocol replay',
          'verified_utc':datetime.now(timezone.utc).isoformat(),
          'manifest_sha256':sha256(raw).hexdigest(),
          'stim_version':obj['software']['stim'],
          'pymatching_version':obj['software']['pymatching'],
          'observations':len(obj['observations']),
          'total_shots':sum(r['shots'] for r in obj['observations']),
          'reference_url':REFERENCE,
          'scope':'Published tutorial protocol matched; not numeric publication figure replication or hardware validation'}
    certificate.write_text(json.dumps(cert,indent=2)+'\n')
    return cert


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--output-dir',type=Path,default=Path('outputs/literature_benchmark'))
    ap.add_argument('--shots',type=int,default=20000)
    ap.add_argument('--seed',type=int,default=20261028)
    ap.add_argument('--replay-only',action='store_true')
    args=ap.parse_args(argv)
    if args.shots!=20000:raise ValueError('published benchmark release requires 20000 shots per point')
    dest=args.output_dir;dest.mkdir(parents=True,exist_ok=True)
    manifest=dest/'observations.json'
    if not args.replay_only:
        obj=run_benchmark(shots=args.shots,seed=args.seed)
        manifest.write_text(json.dumps(obj,indent=2)+'\n')
    cert=verify_saved(manifest,dest,dest/'VALIDATED_LITERATURE_BENCHMARK.json')
    print(f'REAL literature-aligned benchmark verified: {cert["observations"]} conditions, {cert["total_shots"]} shots')
    return 0

if __name__=='__main__':raise SystemExit(main())
