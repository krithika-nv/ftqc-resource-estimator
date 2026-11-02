# FTQC Resource Estimator

A reproducible investigation of how quantum error correction, decoding, control latency and non-Clifford resource supply affect fault-tolerant architecture feasibility. The completed evidence comes from **Stim/PyMatching simulator experiments**; the repository also integrates carefully scoped public experimental evidence from four hardware families.

> **Evidence boundaries:** No claim of independently calibrated or validated universal FTQC predictions across four hardware platforms. Native-unit architecture outputs are illustrative toy scenarios unless clearly tied to independent measured data. See [the evidence ledger](docs/validation/EVIDENCE_AND_RESULTS.md) and [limitations](docs/validation/LIMITATIONS.md).

## Overview and reproducibility

- **[GitHub reviewer guide and all five runner profiles](docs/guides/RUNNING_AND_REPRODUCING.md)** - what to inspect, `ci` / `science` / `ibm` / `evidence` / `all`, GitHub Actions, downloads and archived logs.
- **[Experimental implementation notes](docs/validation/EVIDENCE_AND_RESULTS.md)** - verified experimental improvements and remaining scientific gaps.
- **[Scientific roadmap](ROADMAP.md)** - eight milestone requirements, Track A/Track B and priorities.
- **[Concepts guide](docs/reference/PROJECT_CONCEPTS.md)** - QEC, algorithms, hardware physics, control, architecture and statistical assumptions.
- **[Script entry points](scripts/README.md)** - shell commands, Python utilities and pipeline orchestration.

**Quick checks:** `PYTHONPATH=src:. python3 -m unittest discover -s tests -q`; `python3 scripts/automation/run_pipeline.py --profile science` (Stim/PyMatching); `python3 scripts/automation/run_pipeline.py --profile evidence --fetch --review-bundle` (all four platform evidence streams). The large neutral-atom archive is an **explicit opt-in**, not a Git checkout.

**Scientific status:** different four-family engineering scenarios are *illustrative*; available measured hardware primitives are recorded separately and are not silently converted into logical-gate error rates. The strict 34-gate audit needs independent reviewer acceptance; candidate dossiers are not automatically passed.

## Two complementary project tracks

The project separates **architecture modeling and reproducible simulations (Track A)** from **experimental hardware evidence and model validation (Track B)**. A passed Track A simulation is *not* evidence that Track B is hardware-calibrated. Both tracks are active, with distinct evidence and completion criteria.

### Track A - Architecture modeling and simulations

The original simulations and architecture studies are preserved alongside the four-platform expansion:

| Study | Reproducible entry point | Evidence and scope |
|---|---|---|
| Original architecture Pareto analysis | `scripts/commands/RUN_ARCHITECTURE_STUDY.sh` | [Analysis report](outputs/architecture_study/ARCHITECTURE_REPORT.md), [Pareto configurations](outputs/architecture_study/pareto_feasible.csv); heuristic input assumptions |
| Distance-9 rotated-surface-code memory | `scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh` | [Follow-up report](outputs/stim_memory/followup/analysis/MEMORY_REPORT.md), [simulated observations](outputs/stim_memory/followup/observations.json); real Stim/PyMatching runs, **not hardware shots** |
| Controller-cost tradeoffs and Pareto frontier | `scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh` | [Controller-cost report](outputs/stim_memory/followup/control_cost_analysis/MEMORY_REPORT.md), [tradeoffs CSV](outputs/stim_memory/followup/control_cost_analysis/memory_tradeoffs.csv); assumed controller costs |
| Distance-11 heuristic architecture study | `scripts/commands/RUN_ARCHITECTURE_STUDY.sh` | [Architecture study](outputs/architecture_study/ARCHITECTURE_REPORT.md); **not** the same as the separately measured IBM d=11 repetition-code experiment |
| Distance-scaled literature-aligned benchmark | `scripts/commands/RUN_LITERATURE_BENCHMARK.sh` | [Experiment implementation](src/ftqc_resource_estimator/literature_benchmark.py) and [protocol checks](tests/test_literature_benchmark.py); rerun to regenerate outputs |
| Controller-induced idle-noise study | `scripts/commands/RUN_IDLE_COHERENCE_STUDY.sh` | [Implementation](src/ftqc_resource_estimator/idle_coherence.py), [test invariants](tests/test_idle_coherence.py), and [methods provenance](docs/methods/IDLE_NOISE_METHOD.md); result files depend on local runs |

The original owner-provided local run logs recorded **860,000 simulated shots** across the baseline, follow-up, literature-aligned and idle-noise studies. The logs are not hardware observations and are not silently substituted for missing generated study outputs. To run the science suite, use `python3 scripts/automation/run_pipeline.py --profile science`.

### Track B - Hardware calibration and validation (in progress)

Four distinct hardware families are analyzed: **IBM superconducting, Xanadu photonic, Quantinuum trapped ion, and neutral atoms**. The analysis workflow covers measured-source ingestion, native error/noise models, QEC/decoding, Clifford and non-Clifford logical operations, physical scheduling, independent experimental holdouts, and a common logical workload. [Evidence and claims by platform](docs/validation/EVIDENCE_AND_RESULTS.md) · [Eight validation requirements](ROADMAP.md) · [Strict four-platform acceptance contract](docs/validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.md).

Existing demonstrations include Fez repetition-code measurements and a measured-terminal-readout-only baseline, Aurora published figure-data reconstruction, independently recomputed Helios original MCMR counts, independent H-series JSON counts, and **illustrative** four-family workload scenarios. **The four-family FTQC predictor is not hardware-calibrated or independently validated end to end.** [Conditional workload implementation](src/ftqc_resource_estimator/conditional_architecture.py) and [illustrative numerical receipt](evidence/verified/FOUR_NATIVE_SCENARIOS_UNCALIBRATED.json).

## Measured, simulated and conditional evidence

| Platform/study | Completed work | Remaining boundary |
|---|---|---|
| Core QEC and controller | Owner logs: 860,000 Stim/PyMatching simulated shots, including a 400,000-shot literature-aligned experiment and a 240,000-shot controller-induced idle-noise experiment | Not a hardware validation |
| IBM superconducting | Real Fez QASM3 + `per_shot_cregs` parsing; ~1.09 million decoded chain-shots in local review; measured terminal-readout-only calibration baseline with QASM qubit mapping (one job checked independently) | Full circuit-matched physical-noise predictions and later-calibration validation pending |
| Xanadu photonic | Published Aurora Fig 3c/3d matrix reconstruction and residuals | No raw optical data or GKP logical-operation calibration |
| Quantinuum trapped ion | Helios original MCMR histograms independently reanalyzed: 360/360 recorded marginal distributions matched without executing pickle; separate H-series numerical trial counts | Helios final fitted infidelity, native logical FT gates and independent holdouts pending |
| Neutral atoms | Dataset registry, loss-aware requirements and safe source inventory | Full source-specific loss-aware decoding pending |
| Common FTQC logical workload | Four **distinct** platform-labeled conditional scenarios, native-unit cost/latency and explicit T-state supply | Scenario inputs hypothetical; no platform is hardware calibrated or comparable as a ranking |

### Small source-traceable numerical receipts

- [IBM Fez measured-readout-only smoke comparison](evidence/verified/IBM_FEZ_READOUT_ONLY_SMOKE.json) - 8 comparisons from 16,384 genuine chain-shots; not a syndrome-conditioned hardware predictor.
- [Helios original MCMR raw histogram count reconstruction](evidence/verified/HELIOS_MCMR_ORIGINAL_COUNTS_REPRODUCTION.json) - 360 marginal records verified from 4 × 1000 original circuit shots, no pickle execution.
- [Separate H-series hardware counts](evidence/verified/QUANTINUUM_H_SERIES_PUBLIC_COUNTS.json) - not Helios.
- [Aurora published figure workbook reproduction](evidence/verified/AURORA_WORKBOOK_REPRODUCTION.json) - not raw optical reconstruction.
- [Four native *illustrative* workload scenarios](evidence/verified/FOUR_NATIVE_SCENARIOS_UNCALIBRATED.json) - different numbers but not device-calibrated predictions.

None of these receipts automatically passes the strict 34 hardware FTQC evidence gates. Candidate dossiers live in generated review outputs and require independent scientific review.

## Start here

```zsh
python3 -m pip show stim pymatching numpy openpyxl matplotlib
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
python3 scripts/automation/run_pipeline.py --profile evidence --fetch --review-bundle
```

This single runner fetches small approved public inputs into the correct ignored `data/` directories, writes separate `logs/runs/<run-id>/` diagnostics and a `outputs/FOUR_PLATFORM_REVIEW_BUNDLE.zip`. The approximately 1 GB neutral-atom archive is **opt-in** (`--download-large-neutral`) and the reader currently inventories its numeric schemas, not the authors’ loss-aware ML decoding. **Blocked or excluded evidence is not completed validation**. For full simulations, separately run `python3 scripts/automation/run_pipeline.py --profile science`.

For a quick IBM development smoke test on the downloaded archive:

```zsh
PYTHONPATH=src:. python3 -m external_validation.ibm_raw \
  --archive data/public_calibrations/2026/ibm_fez.tar.gz \
  --decoder majority --max-jobs 1 \
  --output data/verified/ibm_majority_smoke.csv \
  --summary outputs/external_validation/ibm_majority_smoke.json
```

Run the explicitly uncalibrated common workload model:

```zsh
PYTHONPATH=src:. python3 -m ftqc_resource_estimator.conditional_architecture \
  --profiles examples/ILLUSTRATIVE_ONLY_four_family_profiles.json \
  --workload evidence/validation/reference_workload.json \
  --output outputs/external_validation/CONDITIONAL_FOUR_PLATFORM_WORKLOAD.json
```

## Project navigation

- **[Component progress and strict scientific acceptance](docs/validation/PROJECT_PROGRESS.md)** - per-platform engineering evidence, recent run results and full-stack gate status (kept separate).
- **[Scientific evidence and evidence status](docs/validation/EVIDENCE_AND_RESULTS.md)** - completed versus pending by hardware family.
- **[All scientific concepts explained](docs/reference/PROJECT_CONCEPTS.md)** - comprehensive study/interview guide.
- **[Roadmap and eight-part analysis checklist](ROADMAP.md)** - what is implementable now, each missing scientific validation, genuine IBM holdout methodology.
- **[Four-platform scientific acceptance contract](docs/validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.md)** - strict full FTQC evidence criteria.
- **[Limitations](docs/validation/LIMITATIONS.md)** - model boundaries and open risks.
- **[Methods](docs/methods/METHODS.md)** and **[references](docs/reference/REFERENCES.md)** - scientific context and provenance.
- `src/ftqc_resource_estimator/` - models, Stim/PyMatching and conditional architecture envelopes.
- `external_validation/` - source-specific IBM, Aurora, Helios and neutral-atom processing.
- `scripts/automation/` - CI orchestration, source refresh and manifests.
- `tests/` - regression and scientific invariants.
