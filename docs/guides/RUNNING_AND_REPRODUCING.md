# Running and reproducing FTQC Resource Estimator

This guide covers **Track A: architecture modeling and simulations** and **Track B: hardware calibration and validation**. Simulator shots, published figure data, and experimental device shots are distinct kinds of evidence. None alone certifies independently calibrated universal FTQC.

## Before running

From the repository root, install supported scientific dependencies for your Python installation and verify them. The project declares its optional packages in `pyproject.toml`.

```zsh
python3 --version
python3 -m pip show stim pymatching numpy openpyxl matplotlib
PYTHONPATH=src:. python3 -m unittest discover -s tests -q
```

On Homebrew-managed Python, use a compatible package-management approach. Do not bypass externally managed environment protections without assessing the risks.

## Five supported runner profiles

| Profile | Command | Verifies |
|---|---|---|
| `ci` | `python3 scripts/automation/run_pipeline.py --profile ci` | Fast regression tests, invariants and documentation checks |
| `science` | `python3 scripts/automation/run_pipeline.py --profile science` | Runs tests once, regenerates the original Pareto and d=11 architecture study, then executes the Stim/PyMatching baseline, d=9 controller-cost follow-up, distance-scaled benchmark and idle-noise sweep |
| `ibm` | `python3 scripts/automation/run_pipeline.py --profile ibm --fetch --review-bundle` | IBM Fez source audit, QASM/register mapping, raw decoder, descriptive and cross-chain analysis, readout-only baseline |
| `evidence` | `python3 scripts/automation/run_pipeline.py --profile evidence --fetch --review-bundle` | Four hardware-source pipelines, source inventory, figures/counts, evidence candidates and illustrative native workloads |
| `all` | `python3 scripts/automation/run_pipeline.py --profile all --fetch --review-bundle` | CI, simulation and available experimental evidence (longest run) |

The `--dry-run` flag lists the complete configured plan and planned output destinations without executing downloads or simulations. Some data-dependent steps will be blocked until the corresponding source files exist.

Use `--profile evidence --max-ibm-jobs 1 --review-bundle` for a **smoke test only**. It does not constitute a full-dataset reproduction. Optional Aurora plots may be requested with `--plot-figures`.

The approximately 1 GB neutral-atom archive is opt-in:

```zsh
python3 scripts/automation/run_pipeline.py --profile evidence --fetch --download-large-neutral --review-bundle
```

This verifies download provenance and inventories the archive. It does **not** reproduce the authors' loss-aware ML decoding automatically.

## Source files and outputs

| Family | Download location | Implemented processing | Validation boundary |
|---|---|---|---|
| IBM | `data/public_calibrations/2026/ibm_fez.tar.gz` | Source/QASM audits, repetition-code majority and syndrome decoding, calibration-informed readout-only predictions | Not a complete circuit-level noise predictor |
| Xanadu | `data/external_hardware/xanadu_aurora/`, `data/external_hardware/xanadu_gkp/` | Aurora Figure 3c/3d workbook matrices; optional safe numeric quadratures | Not raw optical/GKP logical-FTQC validation |
| Quantinuum | `data/external_hardware/quantinuum_helios/`, `data/external_hardware/quantinuum_specifications/` | Helios source histogram reanalysis and separate device-identified JSON count benchmarks | Full global-infidelity fit and logical FT gates still pending |
| Neutral atoms | `data/external_hardware/neutral_atom_qec/` | Metadata, checksum-controlled large download and archive-schema inspection | Published loss-aware QEC reproduction still pending |

The downloader creates the relevant directories. Do not manufacture `data/verified/*.csv` for missing experimental protocols. Data used in reproducible claims must retain a source URL, checksums, exact preparation/circuit and measurement conventions.

**Logs:** `logs/runs/<run-id>/`, with separate tests, architecture/Pareto and simulator command logs, `run_manifest.json`, and `SUMMARY.md`. In the distance-9 follow-up, the logical-failure figure is written once under `outputs/stim_memory/followup/analysis/`; the controller-cost directory contains its own tradeoff plot and numerical report.

**Review bundle:** `outputs/FOUR_PLATFORM_REVIEW_BUNDLE.zip`, containing the canonical `evidence/gate_review_candidates/` dossiers and a separately generated candidate JSON snapshot, not vendor raw data. Inspect statuses `passed`, `failed`, `blocked_missing_input` and `blocked_upstream` individually. In particular, an inventory pass is not a calibrated prediction.

## Reviewer navigation

- [Methods and original simulations](../methods/METHODS.md)
- [IBM Fez validation](../hardware/IBM_FEZ_VALIDATION.md)
- [Hardware data sources](../hardware/HARDWARE_DATA_GUIDE.md)
- [Evidence and results](../validation/EVIDENCE_AND_RESULTS.md)
- [Component progress](../validation/PROJECT_PROGRESS.md) and [strict full-stack gates](../validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.md)
- [Limitations](../validation/LIMITATIONS.md)
- [GitHub automation](GITHUB_AUTOMATION.md)

The source code lives in `src/ftqc_resource_estimator/` and `external_validation/`. `scripts/automation/` handles downloads, run manifests, candidate dossiers and review bundling. `evidence/verified/` contains compact source-linked receipts, and `evidence/gate_review_candidates/` contains dossiers awaiting independent review. **A candidate is not an accepted scientific gate.**

## Script organization

Shell entry points live in `scripts/commands/`, standalone Python helpers live in `scripts/tools/`, and the central runner and supporting automation live in `scripts/automation/`. There are no executable shell scripts in the repository root. See [Script entry points](../../scripts/README.md) for the directory contract and command examples.

The moved shell scripts resolve the repository root internally. Existing automation and publication workflows invoke their new paths, and the Python helper scripts use the repository root relative to `scripts/tools/`. Use the central runner for normal operation and the individual commands only for focused debugging or reproduction.

## Canonical outputs and duplicate avoidance

- The `science` profile runs regression tests once, invokes `scripts/commands/RUN_ARCHITECTURE_STUDY.sh` to regenerate the original Pareto and distance-11 architecture study, and then invokes `scripts/commands/RUN_ALL_VALIDATIONS.sh` for the other Track A simulations. GitHub Actions archives `outputs/architecture_study/` as well as the Stim/PyMatching outputs.
- Authoritative scenario CSV: `outputs/scenarios.csv`. Do not duplicate it under `examples/generated/`.
- Distance-9 logical-failure plot: `outputs/stim_memory/followup/analysis/memory_logical_failure.png`. The controller-cost output directory retains its distinct report, `memory_tradeoffs.csv`, and `memory_architecture_tradeoff.png`, not a copy of the same failure-probability figure.
- Authoritative human-readable candidate gate dossiers: `evidence/gate_review_candidates/`. Run-specific artifact hashes and candidate attachments are written to `outputs/external_validation/GATE_EVIDENCE_CANDIDATES.json` and packaged for review. Dossiers are not auto-approved.
