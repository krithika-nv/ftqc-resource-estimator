# Evidence, experiment results and source analysis

> Current documentation is authoritative only for the specific claims supported by linked measured data, simulation outputs and tests.

## Current evidence status

**Project scope:** Reproducible modeling and hardware-data analysis with documented limitations; not an independently validated four-platform universal FTQC predictor. Do not claim four-platform hardware calibration.

### Two project tracks - evidence boundaries

- **Track A (completed, reproducible within its simulation/model assumptions):** original architecture Pareto study, d=9 surface-code memory and controller-cost follow-up, d=11 heuristic architecture study, literature-aligned distance-scaled benchmark, and controller-induced idle-noise sensitivity. The source, tests, and included outputs are linked from the [README](../../README.md#track-a-architecture-modeling-and-simulations). The historical 860,000 simulator shots are *simulation*, not measured-device data; literature/idle reports are reproduced by running their scripts where not included in the source archive.
- **Track B (experimental calibration/prediction, unfinished):** IBM, Xanadu, Quantinuum, and neutral-atom source ingestion, native noise/QEC/logical-operation models, authentic holdouts, architecture scheduling and one comparable logical workload. Track B's partial experiments do not imply four validated universal FTQC predictors. See the [eight-part roadmap](../../ROADMAP.md#eight-validation-requirements-explicit-completion-checklist) and [acceptance gates](FOUR_PLATFORM_FTQC_ACCEPTANCE.md).

### Completed and source-linked

| Work | Evidence class | Exact scope |
|---|---|---|
| Core 210+ tests, historical validated Stim runs | Simulator and tests | Owner-provided macOS log showed 860,000 repeated simulator shots. Simulation is not device hardware. |
| IBM public Fez ingestion repair | Hardware raw data + decoder baseline | Parser now accepts real `metadata.logical_state`, `per_shot_cregs`, QASM3 `$n` measurements. First d=11/r=1 job successfully decoded **16,384 chain-shots via majority** from actual uploaded tar archive. |
| IBM initial majority result | Hardware measurement analysis | State 0: **0/8,192** failures; state 1: **1/8,192** failures. Uses majority voting and a real date-stamped job; neither surface-code nor calibration-matched FTQC prediction. |
| IBM QASM compatibility guard | Protocol audit | 40/41 Fez state-0 QASM records satisfy the current extraction order check; `ibm_fez/d3_r3/job_2` has interleaved data and final syndrome readout and requires separate protocol handling. Skip only with explicit report. |
| Xanadu Aurora Figure 3c/3d | Published figure data replot | Workbook-derived numerical matrices; MAE/RMSE relative to supplied simulation numbers; not raw optical reconstruction or GKP FTQC calibration. |
| Quantinuum Helios MCMR | Author saved numerical output | Five error-channel entries extracted read-only from source notebook, with hash and unit scale. No `.p` unpickling, independent fit or logical-code calibration. |
| Common logical workload | Conditional architecture software | The original consistency fixture used identical illustrative inputs. The current project also includes **four distinct hypothetical native engineering scenarios**; neither fixture is a vendor-calibrated prediction or hardware ranking. |

### Six analysis milestones (implementation versus evidence)

| Milestone | Present code | Missing to claim scientifically complete |
|---|---|---|
| Physical calibration | IBM calibration reader; Helios author values; Aurora published matrices; neutral-source registry | Four distinct matched, independently fitted physical noise models and calibration uncertainty |
| Native QEC and logical gates | Stim rotated-surface memory; IBM repetition decoder; native adapter scaffolds | Physical-error models, native validated logical gates, independent decoder checks for all four |
| Universal computation | Common T-gate workload, configurable accepted-magic supply and injection error | Proven native non-Clifford generation/distillation, injection protocols and validation for each family |
| Architecture integration | Resource site accounting, controller limits, factory throughput and latency envelopes | Device-calibrated parallel routing/control schedules and native resource scaling |
| Independent validation | Simulation replay, published figure data and subset IBM hardware decode | Disjoint held-out calibration/prediction of matched logical observables for all four |
| Final comparison | Same logical workload, per-family native resource units and conditional results | Credible calibrated numerical four-family comparison with traceable uncertainty |

### Known blockers and important boundaries

- IBM archive is historically dated; `max-age-days 365` is a *fresh-calibration filter*, not an invalidation of experimental reproduction. IBM decoder uses uniform phenomenological weights by default. One QASM job has unsupported readout chronology and must be excluded and counted or independently reconstructed.
- Do not mistake **zero logical failures** for zero physical error; Wilson intervals remain nonzero.
- Aurora reproduction contains no shot-level experimental covariance; reported numerical differences are not predictive holdout residuals.
- Helios `.p` records are intentionally not deserialized. The extracted MCMR saved-output numbers are not independent fits; no published logical FTQC prediction is shown.
- Neutral-atom raw archive is ~1 GB and not included in the submitted bundle; the paper's decoder and d=5/d=3 comparison have not been independently reproduced.
- Toy scenario outputs have no device-specific calibration; no cross-platform hardware winner, cost or FTQC reliability claim is warranted.

### Defensible README summary

> We developed a reproducible FTQC/QEC resource-estimation analysis prototype with replayable Stim/PyMatching rotated-surface-code memory experiments, controller-latency sensitivity analysis, public device-data ingestion, hardware-native conditional resource models and reproducibility tooling. The repository includes a real IBM repetition-code decoder baseline, an Aurora published-figure-data reproduction and source-traceable Helios notebook statistics. Predictions based on unmeasured architecture coefficients are identified as illustrative, and independently calibrated universal FTQC predictions across four hardware platforms remain an open analysis objective.

### IBM holdout verification update - authentic IBM holdout analysis

- The archived Fez source contains 41 jobs and **two different captured calibration dates**, of which the older single `d3_r3/job_2` is currently excluded due to unsupported QASM measurement chronology. This is an auditable limitation, not permission to invent missing epochs.
- The normalized IBM CSV now yields descriptive logical-error estimates regardless of epoch count, and a predeclared disjoint-physical-chain empirical holdout if genuine chain identifiers are present. The holdout does **not** validate calibrated physical noise or later-epoch generalization.
- The updated `ROADMAP.md` explicitly enumerates all eight end-to-end FTQC analysis acceptance requirements and explains what the zero-of-34 strict audit actually measures.
- `scripts/automation/ibm_epoch_audit.py` produces an immutable source/protocol coverage inventory; `external_validation.runner ibm` writes source-separated results without pretending to predict unsupported code distances, gates or device technologies.

### Source-data update (2026-11-01)

The prior summary above describes earlier documented evidence. The latest source-backed additions are linked from README and `evidence/verified/`:

- **IBM:** one real Fez job successfully mapped physical terminal-data readout to actual qubit-specific state-dependent calibration probabilities, with 8 held-out-from-fitting observed comparisons. This is **not** a circuit-matched QEC noise predictor. Historical cross-chain and calibration-epoch limits remain.
- **Quantinuum Helios-1:** original MCMR 98-bit histograms, four circuit settings with 1,000 shots each, yield 360 qubit/setting *marginal count conditions*; all 360 match the stored authors' marginals. Still no author global-fidelity-fit replay or validated FT logical gates. Separate H2-2 SPAM/RB counts must not be conflated with Helios.
- **Xanadu:** Aurora Figure 3c/3d workbook-derived matrices independently exported with numeric residuals; raw photon quadratures and hardware-matched GKP decoding remain open.
- **Neutral atoms:** checksum-guarded, opt-in source download and safe schema inspection are runnable; measured loss-aware decoder/reproduction of the paper is **not** verified.
- **Native workload:** four *distinct hypothetical engineering scenarios* and non-comparable resource units. No device-calibrated FTQC prediction, no empirical confidence bands.

The strict four-family audit remains 0/34 **accepted** full-stack gates; candidate evidence dossiers are generated but never self-approved.

## Experimental source-processing coverage


**Track A:** architecture/Pareto and d9/d11 studies, 860k recorded simulator trials, controller-cost and idle-noise analyses, plus tests and literature-matched reproduction. Source and historical outputs were not replaced.

**Track B improvements:**

1. IBM readout-only calibration-informed prediction: original QASM terminal data measurements are mapped to physical qubits; state-specific hardware readout probabilities yield a Poisson-binomial majority-error prediction. Observed measured majority failures are independently compared, retaining per-shot Wilson uncertainty. This **does not** produce the still-required circuit-matched syndrome-noise model or a temporal holdout.
2. IBM original decoder accepts a temporary uncompressed TAR cache to avoid repeated decompression; a `--max-ibm-jobs` flag supports explicitly marked smoke testing. Older nonstandard measurement chronology is still excluded pending independent protocol review.
3. Helios paper: a non-executing static parser reconstructs 360 observed marginal trial-count conditions directly from the original MCMR experiment histogram object. Reconstructed marginals are matched to all 360 author-saved marginals. The author global-error fit is still not independently reproduced, and this experiment is not logical FTQC.
4. Quantinuum hardware specifications: independently recalculate 1Q/2Q/SPAM survival counts with Wilson intervals, retaining source-provided H-series/REIMEI identities. **No** H2-2 results are passed off as Helios.
5. Aurora: preserve Figure 3c/3d source workbook numerical reproduction; optionally analyze explicitly unit-mapped plain numeric quadrature arrays, refusing NumPy object pickles. Raw optical figure reconstruction is still pending.
6. Neutral atoms: checksum-verified 997 MB source remains on-demand, with safe numeric-schema reconnaissance and explicit large-download flag. The authors' loss-aware ML paper decoder and suppressions are still pending.
7. Four distinct **hypothetical** native engineering scenarios replace the identical four-label demo, with distinct timing/resource/failure inputs but no counterfeit hardware-calibrated errors. A source-hashed measured-primitive ledger is kept separate from the logical model.
8. Strict 34 acceptance gates unchanged. Canonical reviewer dossiers live under `evidence/gate_review_candidates/`; a current per-run JSON snapshot is generated as `outputs/external_validation/GATE_EVIDENCE_CANDIDATES.json`. No candidate is auto-approved.

**Evidence boundary:** Do not call this an independently calibrated universal-FTQC prediction for all four hardware families. The scientifically useful work is original reproducible simulator architecture work plus increasingly independent physical-source analyses.

Detailed count tables and time-stamped original measurements remain in the source-linked files under `outputs/` and `evidence/verified/`. Simulator samples are not treated as experimental device shots.
