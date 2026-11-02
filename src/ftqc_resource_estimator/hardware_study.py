"""Hardware-specific sensitivity study; not a platform or hardware benchmark."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from .hardware_profiles import ReferenceWorkload,from_record
from .platform_boundaries import scenario_scope


def run(config:Path,outdir:Path)->list[dict]:
    settings=json.loads(config.read_text())
    workload=ReferenceWorkload(**settings['reference_workload'])
    entries=settings['scenarios']
    if not entries:raise ValueError('at least one scenario is required')
    rows=[profile.evaluate(workload) for profile in map(from_record,entries)]
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'PLATFORM_SCOPES.json').write_text(json.dumps({
        family:scenario_scope(family) for family in sorted(set(r['profile'] for r in rows))
    },indent=2)+'\n')
    # Deliberately separate schemas and files: optical states are not qubits or ions.
    for platform in sorted(set(r['profile'] for r in rows)):
        specific=[r for r in rows if r['profile']==platform]
        cols=list(dict.fromkeys(k for r in specific for k in r))
        with (outdir/f'{platform}_scenarios.csv').open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=cols);writer.writeheader();writer.writerows(specific)
    report=['# Hardware-aware FTQC architecture: three **illustrative** adapters','',
      '**NOT a scientific ranking of photonic, superconducting and trapped-ion platforms.**',
      'No hardware-calibrated fidelity, gate noise, photonic GKP code, loss-to-error mapping, leakage, decoder runtime, or transport topology is implemented.','',
      'The same workload labels structure three *different* simplified cost analyses; their outcome numbers are not an apples-to-apples comparison.','',
      'The accompanying `PLATFORM_SCOPES.json` marks every scenario as hypothetical, uncalibrated and not cross-platform comparable. The separately imported IBM records apply only to superconducting characterization and have NOT been injected into these hypothetical scheduling profiles.','',
      f'Common synthetic demand: {workload.logical_qubits} logical storage patches; {workload.memory_windows} memory windows × {workload.syndrome_rounds_per_window} nominal rounds; d={workload.distance}.','',
      '## Results within each platform (hypothetical input values)','']
    for platform in sorted(set(r['profile'] for r in rows)):
        report.extend([f'### {platform.replace("_"," ").title()}','',
         '| Scenario | Modeled runtime (µs) | Bottleneck | Accounting unit |',
         '|---|---:|---|---|'])
        for r in rows:
            if r['profile']==platform:
                report.append(f"| {r['scenario']} | {r['runtime_us']:.3f} | {r['dominant_bottleneck']} | {r['resource_unit']} |")
        report.append('')
    report.extend(['## Interpretation and limitations','',
      '- **Photonic:** independent heralding and path transmissions; a delivered abstract resource does not imply a usable GKP grid state. Mean supply and measurement times are overlapped optimistically; no queue or finite-buffer bottleneck.',
      '- **Superconducting:** assumes ideal layer parallelism, explicit serialized layer counts and independent readout. No connectivity, crosstalk, leakage or decoherence calibrated.',
      '- **Trapped ion:** gate/transport operations are serialized in abstract parallel zones; no explicit ion geometry, heating or scheduling graph.',
      '- **None:** a value for `runtime_us` predicts actual machine latency. The sample scenario values are hypothetical teaching/analysis inputs, not manufacturer specifications.',
      '- **Surface-code decoder:** Stim/PyMatching output, when available, is an *un-calibrated shared circuit reference* and cannot be injected as any of these platforms’ failure rates without a matched noise/channel/schedule validation.',
      '', '## Reproduce', '',
      '`PYTHONPATH=src python3 -m ftqc_resource_estimator.hardware_study --config examples/hardware_profiles.json --output-dir outputs/hardware_profiles`',
      '', '## Source context', '',
      '- Stim QEC circuit experiment: https://github.com/quantumlib/Stim',
      '- PyMatching decoding: https://pymatching.readthedocs.io/en/stable/',
      '- Xanadu photonic FTQC Blueprint: https://doi.org/10.22331/q-2021-02-04-392',
      '- Fowler et al. surface code: https://doi.org/10.1103/PhysRevA.86.032324',
      '', 'Model arithmetic, organization, tests and analyses are independent implementations; no vendor implementation has been copied.'])
    (outdir/'HARDWARE_STUDY.md').write_text('\n'.join(report)+'\n')
    # A separate figure for each platform; intentionally NO cross-platform ranking.
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for platform in sorted(set(r['profile'] for r in rows)):
            local=[r for r in rows if r['profile']==platform]
            fig,ax=plt.subplots(figsize=(8,3.8))
            ax.barh([r['scenario'].replace('illustrative ', '') for r in local],
                    [r['runtime_us'] for r in local])
            ax.invert_yaxis()
            ax.set_xlabel('Assumed modeled runtime (microseconds)')
            ax.set_title(f'{platform.replace("_"," ").title()}: within-platform sensitivity only')
            ax.grid(axis='x',alpha=.25)
            fig.tight_layout()
            fig.savefig(outdir/f'{platform}_sensitivity.png',dpi=160)
            plt.close(fig)
    except ImportError:
        pass
    return rows


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=Path('examples/hardware_profiles.json'))
    p.add_argument('--output-dir',type=Path,default=Path('outputs/hardware_profiles'))
    args=p.parse_args(argv)
    rows=run(args.config,args.output_dir)
    print(f'Wrote {len(rows)} hypothetical scenario outcomes; NOT a hardware comparison. See {args.output_dir}/HARDWARE_STUDY.md')
    return 0
if __name__=='__main__':raise SystemExit(main())
