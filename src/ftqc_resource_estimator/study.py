"""Reproducible architecture sensitivity study. Pure standard-library computation.

Optional matplotlib makes figures but is NOT required to reproduce CSVs.
"""
from __future__ import annotations
import argparse
import csv
import json
from dataclasses import replace, asdict
from pathlib import Path
from .model import Scenario
from .architecture import Workload, ResourceSupply, Architecture, evaluate, pareto
from .reliability import EmpiricalTable


def load_configuration(path: Path) -> tuple[Workload,list[Architecture],list[int]]:
    config=json.loads(path.read_text(encoding='utf-8'))
    workload=Workload(**config['workload'])
    distances=list(config['distances'])
    if not distances or len(set(distances))!=len(distances) or any(d<3 or d%2!=1 for d in distances):
        raise ValueError('distances must be unique odd integers >=3')
    if len(config['architectures'])<2:
        raise ValueError('at least two architecture scenarios needed for comparison')
    designs=[]
    for row in config['architectures']:
        supply=dict(row['supply'])
        supply['path_transmissions']=tuple(supply['path_transmissions'])
        noise=dict(row['noise'])
        designs.append(Architecture(row['name'], Scenario(row['name'],**noise),ResourceSupply(**supply),
                                    row.get('extra_patch_fraction',0)))
    if len({a.name for a in designs}) != len(designs):
        raise ValueError('architecture names must be unique')
    return workload,designs,distances


def write_csv(path:Path,rows:list[dict]):
    if not rows:
        raise ValueError('cannot write an empty experiment')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def sensitivity(design: Architecture,workload: Workload,distance:int,values: list[float]):
    """Change ONLY transmission in the first path segment; others held fixed."""
    if not design.supply.path_transmissions:
        raise ValueError('needs at least one transmission segment')
    rows=[]
    for t in values:
        altered=replace(design,supply=replace(design.supply,path_transmissions=(t,)+design.supply.path_transmissions[1:]))
        r=evaluate(altered,distance,workload)
        rows.append({'first_segment_transmission':t,'distance':distance,
                     'delivery_probability':r.delivery_probability,'bottleneck':r.bottleneck,
                     'latency_us':r.latency_us,'compute_us':r.compute_us,'supply_us':r.supply_us,
                     'expected_attempts':r.expected_preparation_attempts})
    return rows


def factory_sweep(design: Architecture,workload: Workload,distance:int,counts: list[int]):
    """Vary number of source factories at fixed code, workload, device assumptions."""
    rows=[]
    for n in counts:
        modified=replace(design,supply=replace(design.supply,factories=n))
        r=evaluate(modified,distance,workload)
        rows.append({'factories':n, 'distance':distance,'total_site_equivalents':r.total_site_equivalents,
                     'compute_us':r.compute_us,'supply_us':r.supply_us,'latency_us':r.latency_us,
                     'site_equivalent_us':r.site_equivalent_us,'bottleneck':r.bottleneck})
    return rows


def reliability_sweep(design: Architecture,workload: Workload,distances: list[int],p_values: list[float]):
    """Sensitivity ONLY to the hypothetical physical noise parameter, NOT observed thresholds."""
    rows=[]
    for p in p_values:
        variant=replace(design,noise=replace(design.noise,physical_error=p))
        eligible=[evaluate(variant,d,workload) for d in distances]
        best=min((r for r in eligible if r.model_feasible_mean),
                 key=lambda r:(r.site_equivalent_us,r.distance),default=None)
        rows.append({'physical_error_assumption':p,'chosen_distance':best.distance if best else 'none',
                     'total_site_equivalents':best.total_site_equivalents if best else '',
                     'latency_us':best.latency_us if best else '',
                     'modeled_failure':best.mean_failure if best else '',
                     'note':'unfitted reliability ansatz; no real threshold inference'})
    return rows


def figures(results,rows,out:Path):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    out.mkdir(parents=True,exist_ok=True)
    fig,ax=plt.subplots(figsize=(8,4.8))
    for name in sorted({r.architecture for r in results}):
        subset=sorted((r for r in results if r.architecture==name),key=lambda r:r.distance)
        ax.plot([r.distance for r in subset],[r.latency_us/1000 for r in subset],marker='o',label=name)
    ax.set(xlabel='Rotated patch code distance (toy)',ylabel='Estimated elapsed time (ms)',
           title='Throughput / compute latency envelope (illustrative)')
    ax.grid(alpha=.22);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'latency_vs_distance.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.8))
    for name in sorted({r.architecture for r in results}):
        subset=[r for r in results if r.architecture==name and r.model_feasible_mean]
        ax.scatter([r.total_site_equivalents for r in subset],
                   [r.latency_us/1000 for r in subset],label=name)
        for r in subset:
            ax.annotate(f'd={r.distance}',(r.total_site_equivalents,r.latency_us/1000),fontsize=7)
    ax.set(xlabel='Assumed physical site-equivalents (not photons)', ylabel='Elapsed time (ms)',
           title='Model-feasible tradeoffs; no real hardware performance claims')
    ax.grid(alpha=.22);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'feasible_tradeoffs.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.8))
    ax.plot([r['first_segment_transmission'] for r in rows],
            [r['latency_us']/1000 for r in rows],marker='o')
    ax.set(xlabel='First optical path segment transmission (toy)',ylabel='Elapsed time (ms)',
           title='One-at-a-time transmission sensitivity (not GKP loss modeling)')
    ax.grid(alpha=.22);fig.tight_layout();fig.savefig(out/'transmission_sensitivity.png',dpi=160);plt.close(fig)
    return True


def report(path: Path, workload:Workload, designs:list[Architecture], results, frontier, used_empirical:bool,
           plots:bool):
    lines=['# Architecture comparison - reproducible example','',
           '**Interpretation boundary:** This is a **toy surface-patch and abstract resource-delivery model**. '
           'It is not an estimation of Xanadu hardware, photonic GKP logical-error performance, '
           'magic-state factories, or total FTQC cost.','',
           f'- Logical qubits: **{workload.logical_qubits}**',
           f'- Sequential logical layers: **{workload.logical_layers}**',
           f'- Modeled logical locations: **{workload.logical_qubits*workload.logical_layers}**',
           f'- Target failure: **{workload.target_failure:.3g}**',
           f'- Reliability: **{"exact-key empirical CSV with Wilson confidence bounds" if used_empirical else "unfitted heuristic (NO statistical uncertainty)"}**','',
           '## Architecture inputs','']
    for a in designs:
        lines.extend([f'### {a.name}',
           f'- Syndrome round: {a.noise.cycle_microseconds:g} μs; decoder delay: {a.noise.decode_microseconds:g} μs',
           f'- Resource factories: {a.supply.factories}; attempt rate: {a.supply.attempts_per_factory_per_us:g}/μs/factory',
           f'- Preparation success: {a.supply.preparation_success:g}; segments: {a.supply.path_transmissions}',
           f'- Delivery probability: {a.supply.delivery_probability:.4g}',
           f'- Extra patch reserve fraction: {a.extra_patch_fraction:g}; assumed factory site-equivalents per factory: {a.supply.factory_site_equivalents}',
           ''])
    lines.extend(['## Minimum model-feasible code distance','',
           '| Architecture | d | Site equivalents | Runtime (ms) | Bottleneck | Modeled failure |',
           '|---|---:|---:|---:|---|---:|'])
    for design in designs:
        matches=[r for r in results if r.architecture==design.name and r.model_feasible_upper]
        if matches:
            r=min(matches,key=lambda item:(item.site_equivalent_us,item.distance))
            lines.append(f'| {design.name} | {r.distance} | {r.total_site_equivalents} | {r.latency_us/1000:.2f} | {r.bottleneck} | {r.mean_failure:.4g} |')
        else:
            lines.append(f'| {design.name} | Not found | - | - | - | - |')
    lines.extend(['','## Pareto set (site count and latency, model-reliability constraint)','',
                  f'{len(frontier)} non-dominated scenarios found within the scanned distances.',''])
    for r in frontier:
        lines.append(f'- `{r.architecture}`, d={r.distance}: {r.total_site_equivalents} site equivalents; '
                     f'{r.latency_us/1000:.2f} ms; {r.bottleneck}-limited')
    lines.extend(['','## What the study demonstrates','',
     '1. For a fixed **assumed** reliability model, faster syndrome cycles need not reduce runtime '
     'when the resource supply is the bottleneck.',
     '2. High success probability helps delivery throughput, but the cost of more physical factories '
     'and slower control can reverse the preferred design.',
     '3. The selected design depends on the **specified resource accounting** and a fixed workload; '
     'Pareto results are not intrinsic rankings of FTQC platforms.','',
     '## Missing physics and uncertainty','',
     '- The assumed logical-error formula is not calibrated to a quantum code simulation or hardware.',
     '- An error rate **per logical layer** is treated as independent across every logical qubit-layer; '
     'correlated failures and different gate types are omitted.',
     '- Resource failures are treated as **heralded**, costing attempts/time rather than logical errors.',
     '- `max(compute_us, supply_us)` assumes perfect overlap, no buffer starvation, and no start-up cost.',
     '- Factory site equivalents are analyst-specified accounting proxies, not a physical factory layout.',
     '- A real surface-code memory experiment cannot be used as a logical-gate rate without a matched schedule.',
     '- No numerical thresholds or photonic resource estimates are extracted from the cited papers.','',
     '## Reproduce','',
     '```bash',
     'PYTHONPATH=src python3 -m ftqc_resource_estimator.study --config examples/architecture_scenarios.json --output-dir outputs/architecture_study',
     'PYTHONPATH=src python3 -m unittest discover -s tests -v',
     '```','',
     f'Figures generated: {plots}. Matplotlib optional; all CSV and Markdown outputs are standard-library.','',
     '## Analysis context (not model calibration)','',
     '- Fowler et al. (2012), *Surface Codes: Towards Practical Large-Scale Quantum Computation*. https://doi.org/10.1103/PhysRevA.86.032324',
     '- Horsman et al. (2012), *Surface Code Quantum Computing by Lattice Surgery*. https://doi.org/10.1088/1367-2630/14/12/123011',
     '- Zhou, Cain, Lukin (2025), *Opportunities in Full-Stack Design of Low-Overhead Fault-Tolerant Quantum Computation*. https://doi.org/10.1038/s43588-025-00895-6',
     '- Microsoft QRE documentation (conceptual layer decomposition only). https://learn.microsoft.com/azure/quantum/intro-to-resource-estimation',
     ''])
    path.write_text('\n'.join(lines),encoding='utf-8')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Compare toy FTQC architectures across code distance / optical transmission')
    parser.add_argument('--config',type=Path,default=Path('examples/architecture_scenarios.json'))
    parser.add_argument('--output-dir',type=Path,default=Path('outputs/architecture_study'))
    parser.add_argument('--empirical-csv',type=Path,help='Only rotated_surface/logical_layer EXACT matched data (NO extrapolation)')
    args=parser.parse_args(argv)
    workload, designs, distances=load_configuration(args.config)
    empirical=EmpiricalTable.from_csv(args.empirical_csv) if args.empirical_csv else None
    results=[evaluate(a,d,workload,empirical=empirical) for a in designs for d in distances]
    best=pareto(results,robust=empirical is not None)
    out=args.output_dir
    rows=[r.row() for r in results]
    write_csv(out/'distance_sweep.csv',rows)
    if best:
        write_csv(out/'pareto_feasible.csv',[r.row() for r in best])
    else:
        (out/'pareto_feasible.csv').write_text('No feasible points in grid\n',encoding='utf-8')
    reference=designs[0]
    target_d=min((r.distance for r in results if r.architecture==reference.name and r.model_feasible_upper), default=max(distances))
    sweep=sensitivity(reference,workload,target_d,[.55,.65,.75,.8,.85,.9,.95,.975,.99])
    write_csv(out/'transmission_sensitivity.csv',sweep)
    if empirical is None:
        write_csv(out/'reliability_sensitivity.csv',reliability_sweep(reference,workload,distances,[.0005,.001,.0015,.002,.003]))
        write_csv(out/'factory_sensitivity.csv',factory_sweep(reference,workload,target_d,[1,2,4,8]))
    wrote=figures(results,sweep,out)
    report(out/'ARCHITECTURE_REPORT.md',workload,designs,results,best,empirical is not None,wrote)
    print(f'Generated {len(results)} architecture-distance observations; {len(best)} feasible nondominated')
    print(f'Outputs: {out}; reliability source: {"empirical matched observations" if empirical else "ILLUSTRATIVE HEURISTIC"}')
    for r in best:
        print(f'  {r.architecture}: d={r.distance}, site equivalents={r.total_site_equivalents}, ms={r.latency_us/1000:.3f}, bottleneck={r.bottleneck}')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
