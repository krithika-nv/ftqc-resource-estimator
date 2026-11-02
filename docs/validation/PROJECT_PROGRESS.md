# FTQC evidence dashboard - component progress versus scientific acceptance

**Snapshot:** derived from the  source files and a **previous** evidence-run review bundle (`20261101T035516Z-79033`) created before the latest repository changes. Run outcomes should be refreshed on your Mac. This is an engineering progress overview, not a release certification.

> **Do not interpret 0/34 as 34 failed experiments.** The strict manifest has no submitted full-stack evidence dossiers. This dashboard reports a **selected implemented-and-planned capability inventory**, not a percentage of all required analysis. File/run observations are **separate** from certification.

| Hardware | Component code | Test files | Saved scoped evidence | Last supplied run steps passed | Strict gate dossiers |
|---|---:|---:|---:|---:|---:|
| Superconducting | 4/8 | 4/8 | 3/8 | 1/8 | 0/9 (registered 0) |
| Photonic | 2/6 | 2/6 | 1/6 | 2/6 | 0/8 (registered 0) |
| Trapped Ion | 2/6 | 2/6 | 1/6 | 1/6 | 0/9 (registered 0) |
| Neutral Atom | 3/7 | 3/7 | 1/7 | 0/7 | 0/8 (registered 0) |

**How to read the table:** Denominators include selected planned-but-unimplemented capabilities. Code and test-file counts are filesystem observations, *not* pass rates or a science-completeness percentage. Saved evidence includes narrowly qualified published-data replots, measured-shot baselines, and illustrative simulations. Missing latest run information is displayed as zero (no observed pass), **not as failure**. Matching a gate dossier hash is not independent scientific peer review.

**Run context:** 20261101T035516Z-79033. This dashboard is not a hardware readiness percentage.

## Track A - simulator-backed and heuristic analysis

| Study | Source | Report present | Scope |
|---|---|---|---|
| Original architecture Pareto optimization | `src/ftqc_resource_estimator/pareto.py` | Yes | heuristic model |
| Distance-9 surface-code memory | `src/ftqc_resource_estimator/stim_memory.py` | Yes | simulator |
| Controller-cost Pareto tradeoffs | `src/ftqc_resource_estimator/controller_capacity.py` | Yes | simulator plus assumed costs |
| Distance-11 heuristic architecture | `src/ftqc_resource_estimator/architecture.py` | Yes | heuristic model |
| Literature-aligned memory benchmark | `src/ftqc_resource_estimator/literature_benchmark.py` | Not bundled; regenerate | simulator outputs not bundled |
| Controller-induced idle-noise model | `src/ftqc_resource_estimator/idle_coherence.py` | Not bundled; regenerate | simulator outputs not bundled |

## Track B - actual per-family components

### Superconducting

| Component | Recorded evidence | Last pipeline step |
|---|---|---|
| IBM repetition-code register reader | `evidence/verified/IBM_FEZ_D11_R1_JOB1_MAJORITY.json` - measured single job majority baseline | passed |
| Historical Fez calibration-epoch audit | `evidence/verified/IBM_FEZ_CALIBRATION_EPOCH_AUDIT.json` - historical calibration inventory | not_checked |
| Repetition-code numerical analysis | No bundled result | failed |
| Rotated surface-code Stim/PyMatching simulator | `outputs/stim_memory/VALIDATED_RUN.json` - simulator not ibm hardware | not_checked |
| Calibrated circuit-level physical noise | **Planned: not implemented** | not_applicable |
| Circuit-matched held-out prediction and residuals | **Planned: not implemented** | not_applicable |
| Verified hardware-native logical Clifford gates | **Planned: not implemented** | not_applicable |
| Verified non-Clifford resource path | **Planned: not implemented** | not_applicable |

Strict hardware-specific evidence files: **0/9**. Missing requirements: device_calibration, circuit_level_noise, syndrome_decoder, logical_memory, logical_clifford_gates, nonclifford_factory, routing_scheduler, physical_resource_accounting, independent_holdout. The entire model is **not certified**.

### Photonic

| Component | Recorded evidence | Last pipeline step |
|---|---|---|
| Aurora figures 3c/3d replot from published workbook | `evidence/verified/AURORA_PUBLISHED_FIGURE_DATA_REPORT.json` - published figure data replot not raw optics | passed |
| GKP/density-matrix numerical diagnostics | No bundled result | passed |
| Measured-loss and GKP-noise calibration | **Planned: not implemented** | not_applicable |
| Raw optical shot GKP QEC decoder reproduction | **Planned: not implemented** | not_applicable |
| Native protected Clifford and non-Clifford path | **Planned: not implemented** | not_applicable |
| Matched GKP/logical experiment holdout | **Planned: not implemented** | not_applicable |

Strict hardware-specific evidence files: **0/8**. Missing requirements: loss_squeezing_gkp_characterization, gkp_noise_and_decoder, logical_memory, logical_clifford_gates, nonclifford_factory, optical_routing_and_multiplexing, physical_resource_accounting, independent_holdout. The entire model is **not certified**.

### Trapped Ion

| Component | Recorded evidence | Last pipeline step |
|---|---|---|
| Helios saved-notebook numeric output extractor | `evidence/verified/HELIOS_MCMR_CACHED_NOTEBOOK_OUTPUT.json` - author saved notebook values not raw reanalysis | passed |
| Verified-count trapped-ion statistical analysis | No bundled result | blocked_missing_input |
| Gate, leakage, SPAM and transport calibration | **Planned: not implemented** | not_applicable |
| Hardware-matched ion logical-code reproduction | **Planned: not implemented** | not_applicable |
| Native protected Clifford and non-Clifford path | **Planned: not implemented** | not_applicable |
| Independent Helios logical-protocol holdout | **Planned: not implemented** | not_applicable |

Strict hardware-specific evidence files: **0/9**. Missing requirements: gate_spam_leakage_calibration, transport_and_crosstalk, native_logical_code_decoder, logical_memory, logical_clifford_gates, nonclifford_factory, routing_scheduler, physical_resource_accounting, independent_holdout. The entire model is **not certified**.

### Neutral Atom

| Component | Recorded evidence | Last pipeline step |
|---|---|---|
| Loss-aware QEC archive safe inventory | No bundled result | blocked_missing_input |
| Neutral-atom geometry and scheduling model | `outputs/neutral_atom_schedule_illustrative/NEUTRAL_ATOM_SCHEDULING.json` - illustrative scheduling not device calibration | not_applicable |
| Neutral-atom randomized measurement diagnostic | No bundled result | blocked_missing_input |
| Gate-loss-erasure-rearrangement calibration | **Planned: not implemented** | not_applicable |
| Published loss-aware decoder and logical-memory reproduction | **Planned: not implemented** | not_applicable |
| Verified protected neutral-atom logical gates | **Planned: not implemented** | not_applicable |
| Independent experimental neutral-atom holdout | **Planned: not implemented** | not_applicable |

Strict hardware-specific evidence files: **0/8**. Missing requirements: gate_loss_rearrangement_calibration, erasure_aware_decoder, logical_memory, logical_clifford_gates, nonclifford_factory, replenishment_and_parallel_zones, physical_resource_accounting, independent_holdout. The entire model is **not certified**.

## Shared models

- **Illustrative four-family logical workload** - source present: True; saved artifact: True; evidence scope: illustrative not hardware calibrated.
- **Conditional logical-primitive probability composition** - source present: True; saved artifact: False; evidence scope: implementation only.

## Scientific qualification and next action

1. The full-stack gate manifest (`evidence/validation/four_family_evidence.json`) is empty. A legitimate gate dossier requires source hashes, a matching experiment/protocol, independent prediction and holdout evidence, and a methodology review. Never fill it automatically from code or source inventories.
2. Record actual CI execution separately from test-file presence. On each four-family evidence run, retain the run manifest plus this report in the GitHub artifact bundle.
3. Prioritize converting specific sub-results into reviewed, source-traceable evidence dossiers. Do not count figures, notebook cached values, or toy workload output as certified end-to-end native FTQC predictions.

## Refresh after local experiment run

```zsh
python3 scripts/automation/run_pipeline.py --profile evidence --fetch --review-bundle
# New per-run dashboard: outputs/external_validation/COMPONENT_PROGRESS.md
# Strict scientific gate status: outputs/external_validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.json
```

GitHub Actions uploads these reports as workflow artifacts. Do not automatically promote completed steps into the strict gate manifest.
