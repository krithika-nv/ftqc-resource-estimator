"""Independent arithmetic audit of *reported* IBM Nighthawk r2 readout findings.

This module is NOT new quantum hardware data and is NOT a calibrated simulator.
The input table is manually transcribed from Kan et al. (2026), arXiv:2610.23840v1,
Section 2 (Readout duration), Fig. 2, on one selected d=3 placement with fused reset.
Rates are approximate rounded values in the publication, not raw shot counts.
The detector-pair diagnostic probabilities are DIFFERENT observables from logical
errors; never fit a per-qubit Pauli channel directly to these numbers.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import math

PAPER = 'https://arxiv.org/html/2610.23840'
SCHEMA = 'ftqc.published_readout_empirical_anchor.v1'
DATA = {
    'schema': SCHEMA,
    'reference': PAPER,
    'version': 'arXiv:2610.23840v1 (16 October 2026), preprint',
    'device': 'IBM Nighthawk r2, ibm_phoenix',
    'experiment': 'Selected distance-3 placement with fused reset; readout-duration comparison, Fig. 2b-d',
    'interpretation': 'Reported, rounded published measurements; NOT newly collected, NOT full-device calibration',
    'readout_duration_us': {'standard': 1.94, 'short': 1.14},
    'reported_per_round_logical_error_percent': {
        'X_memory': {'standard': 1.67, 'short': 0.98},
        'Z_memory': {'standard': 0.82, 'short': 0.63},
    },
    'reported_detector_pair_reduction_percentage_points': {
        'bit_flip_associated': {'measured': 0.22, 'coherence_only_prediction': 0.23},
        'phase_associated': {'measured': 0.95, 'coherence_only_prediction': 0.22},
    },
    'critical_distinctions': [
        'Source experiment is IBM Nighthawk, not Google Willow; never mix device inputs for a calibrated claim.',
        'Logical-error percentages are paper-reported epsilon per round, not nine-round failure probabilities.',
        'Detector-pair percentage-point changes are not independent per-qubit Pauli probabilities.',
        'Shortening readout also changes circuit schedule; coherent ZZ and other correlated effects may matter.',
        'Measurement channels and the total concurrent readout capacity are not derived from these durations.',
    ],
}


def validate_source_record(obj: dict) -> None:
    """Fail closed: a result cannot call itself this published anchor after editing inputs."""
    if obj != DATA:
        raise ValueError('Published values or provenance changed; review the primary paper and update the registered schema')
    if not (obj['readout_duration_us']['standard'] > obj['readout_duration_us']['short'] > 0):
        raise ValueError('Invalid published readout durations')


def summarize(obj: dict = DATA) -> dict:
    validate_source_record(obj)
    old = obj['readout_duration_us']['standard']
    new = obj['readout_duration_us']['short']
    result = {'source': obj['reference'], 'device': obj['device'], 'readout_saved_us': old-new,
              'readout_relative_reduction_percent': 100*(old-new)/old,
              'derived_data_status': 'published_rounded_summary_arithmetic_only'}
    for basis, item in obj['reported_per_round_logical_error_percent'].items():
        before, after = item['standard'], item['short']
        result[basis] = {'reported_standard_epsilon_percent': before,
                         'reported_short_epsilon_percent': after,
                         'derived_absolute_reduction_percentage_points': before-after,
                         'derived_relative_reduction_percent': 100*(before-after)/before}
    for label, vals in obj['reported_detector_pair_reduction_percentage_points'].items():
        result[label] = {'measured_change_percentage_points':vals['measured'],
                         'coherence_prediction_change_percentage_points':vals['coherence_only_prediction'],
                         'observed_minus_model_percentage_points':vals['measured']-vals['coherence_only_prediction'],
                         'measured_to_model_ratio':vals['measured']/vals['coherence_only_prediction']}
    return result


def write_report(folder:Path) -> None:
    folder.mkdir(parents=True,exist_ok=True)
    s=summarize()
    (folder/'SOURCE_RECORD.json').write_text(json.dumps(DATA,indent=2)+'\n')
    (folder/'RECALCULATED_SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n')
    with (folder/'published_readout_comparison.csv').open('w',newline='') as f:
        w=csv.writer(f)
        w.writerow(['basis','standard_readout_us','short_readout_us','published_epsilon_standard_percent',
                    'published_epsilon_short_percent','derived_relative_reduction_percent','data_type'])
        for basis in ('X_memory','Z_memory'):
            row=s[basis]
            w.writerow([basis,DATA['readout_duration_us']['standard'],DATA['readout_duration_us']['short'],
                        row['reported_standard_epsilon_percent'],row['reported_short_epsilon_percent'],
                        row['derived_relative_reduction_percent'],'secondary published rounded measurement'])
    lines=[
        '# Independently analyzed **published** IBM Nighthawk readout measurements', '',
        '> These are **reported values from Kan et al. (2026)**, not new experiments or an independently',
        '> reproduced hardware result. We independently recompute arithmetic contrasts only.', '',
        f'- Primary source: {PAPER} (Section 2, Fig. 2, preprint as of 28 October 2026).',
        '- Device: IBM Nighthawk r2 `ibm_phoenix`, selected d=3 placement with fused reset.',
        '- Two readout durations: **1.94 µs** standard vs **1.14 µs** short, a **0.80 µs** difference.',
        '- The published logical-error parameter ε is **per syndrome round**, not the total probability of a 9-round memory failure.', '',
        '| Memory basis | Reported ε, standard | Reported ε, short | Derived reduction |',
        '|---|---:|---:|---:|',
    ]
    for basis in ('X_memory','Z_memory'):
        x=s[basis]
        lines.append(f'| {basis} | {x["reported_standard_epsilon_percent"]:.2f}% | '
                     f'{x["reported_short_epsilon_percent"]:.2f}% | '
                     f'{x["derived_relative_reduction_percent"]:.1f}% |')
    lines+=['', '## Why a coherence-only idle model is insufficient', '',
        'The same publication reports a median change in *detector-pair* probabilities, not logical error rates:', '',
        '| Detector-pair signature | Measured reduction | Coherence-only prediction | Unexplained residual |',
        '|---|---:|---:|---:|']
    for label in ('bit_flip_associated','phase_associated'):
        v=s[label]
        lines.append(f'| {label} | {v["measured_change_percentage_points"]:.2f} pp | '
                     f'{v["coherence_prediction_change_percentage_points"]:.2f} pp | '
                     f'{v["observed_minus_model_percentage_points"]:+.2f} pp |')
    lines+=['',
        '**Interpretation:** The phase-associated reduction is over four times the coherence-only prediction.',
        'A single effective T2 from an echo/CPMG protocol cannot make the proposed waiting model fully calibrated.',
        'The authors investigate ancilla-state-dependent ZZ phases and other scheduling effects. See paper §2 and appendix.', '',
        '## What this fixes - and what it does not', '',
        '- **Fixed:** A published example now grounds actual readout durations AND experimental sensitivity to readout shortening.',
        '- **Fixed:** We avoid treating T2_CPMG as unprotected Ramsey T2; the comparison exposes missing phase physics.',
        '- **Not fixed:** The Willow 32/128/256 channel scenarios remain hypotheses. No credible matching channel-capacity',
        '  measurement or per-qubit free-idle Ramsey T2* was obtained for those same schedules.',
        '- **Not fixed:** These paper values are a *separate device and protocol*; they are not calibration inputs for',
        '  the Willow-inspired Stim baseline, nor can reported ε or detector pairs be inserted as per-qubit Pauli error rates.',
        '- **Next real calibration:** same-device qubit-by-qubit Ramsey data, timestamped readout parallelism and',
        '  durations, placement-dependent noise, and original syndrome-shot data. See `docs/DEVICE_CALIBRATION_REQUIRED.md`.', '',
        'Source data are rounded; uncertainty intervals and shot counts for these specific summarized contrasts are not',
        'reconstructed here. The source paper contains further statistical analyses and controls.', '']
    (folder/'PUBLISHED_READOUT_AUDIT.md').write_text('\n'.join(lines))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(7.2,4.6))
        xx=[0,1]
        for condition,shift in [('standard',-.17),('short',.17)]:
            vv=[DATA['reported_per_round_logical_error_percent'][b][condition] for b in ('X_memory','Z_memory')]
            ax.bar([x+shift for x in xx],vv,width=.32,label=f'{condition} readout')
        ax.set_xticks(xx, ['X memory','Z memory'])
        ax.set_ylabel('Reported logical error per round ε (%)')
        ax.set_title('Published IBM Nighthawk measurements (Kan et al., 2026)')
        ax.legend(fontsize=8);fig.tight_layout()
        fig.savefig(folder/'published_readout_comparison.png',dpi=170)
        plt.close(fig)
    except ImportError:
        pass


def main() -> None:
    parser=argparse.ArgumentParser(description='Audit secondary published source numbers; no simulator required')
    parser.add_argument('--output-dir',type=Path,default=Path('outputs/published_readout'))
    args=parser.parse_args()
    write_report(args.output_dir)
    print(f'Published-source arithmetic audit generated in {args.output_dir} - NOT a new hardware experiment')

if __name__=='__main__':main()
