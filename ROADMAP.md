# Technical roadmap - implementation and validation

## Two-track project plan

**Track A - Completed and reproducible (protect and maintain).** Preserve the original architecture Pareto analysis; distance-9 Stim/PyMatching memory follow-up; controller-cost Pareto configurations; distance-11 illustrative architecture study; distance-scaled literature-aligned benchmark; and controller-induced idle-noise simulations. Treat scenario assumptions, simulation shots, published figure data, and hardware shots as distinct evidence classes. Regression-test and independently replay these studies; do not replace their results with the four-platform experiments. See the [README Track A navigation](README.md#track-a-architecture-modeling-and-simulations).

**Track B - Experimental calibration and prediction (ongoing).** Develop the IBM superconducting, Xanadu photonic, Quantinuum trapped-ion, and neutral-atom evidence pipelines into independently calibrated native noise/QEC/logical-gate models, integrated resource/scheduling predictions and genuinely held-out validation. Eight separate acceptance requirements are tracked below; the current conditional four-family output is illustrative. See the [README Track B navigation](README.md#track-b-hardware-calibration-and-validation-in-progress) and [evidence ledger](docs/validation/EVIDENCE_AND_RESULTS.md).

**Project evidence policy:** Both tracks remain visible in GitHub. Track A can be cited as reproducible simulator-backed analysis within its scoped assumptions; Track B claims require source-specific measurements and individual evidence gates. Never interpret successful unit tests or source downloads as proof of four calibrated FTQC models.

## Current deliverable

Reproducible Stim+PyMatching FTQC/QEC prototype; calibrated-data ingestion groundwork; source-linked IBM, Aurora and Helios evidence at explicitly limited validation levels; a common workload run through four **illustrative** hardware-native architecture envelopes; tests, CI, artifact/log archive and concept guide. This is an inspectable project snapshot, not the completion of all science.

## Eight validation requirements - explicit completion checklist

**Reading the status:** "Can implement now" means the software, analysis, or source-specific reproduction is feasible with published records. It does **not** mean physical calibration and external predictive validation are already achieved. A four-platform claim requires separately checked evidence for each family. These tasks map onto Milestones 1–5 below and the 34 gates in `docs/validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.md`.

| # | Acceptance requirement | Work doable now from available public evidence | Still required before the claim can be called verified | Status |
|---|---|---|---|---|
| 1 | Four authentic calibration datasets | Import and provenance-check IBM gate/readout/coherence snapshots, published Xanadu Aurora/GKP observables, Helios benchmark records, and neutral-atom loss/QEC records | Confirm physical parameter coverage, measurement units, uncertainty, same-device/protocol matching; obtain parameters that published datasets do not expose | **Partial** |
| 2 | Four native noise models | Implement separate superconducting circuit-level noise, photonic Gaussian/GKP/loss noise, trapped-ion gate/transport/leakage noise, neutral-atom gate/loss/erasure noise; test each with controlled fixtures | Fit to actual device-specific measurements and independently check predictive adequacy, including correlations and drift | **Models feasible; calibration incomplete** |
| 3 | Four native QEC pipelines | Existing Stim/PyMatching surface-memory simulations; real IBM repetition-code decoding; reproduce GKP, Helios logical protocols and neutral-atom author decoding where source format permits | Match actual paper protocol, code, rounds, loss policy and decoder and reproduce source figures with statistical uncertainty | **Partial; IBM repetition code decoded** |
| 4 | Fault-tolerant logical Clifford and non-Clifford operations | Build explicit platform-native logical operation definitions and T/magic-state production/injection/distillation flows; bound hypothetical factories and track missing rates | Experimental logical gate and non-Clifford evidence on each hardware platform; verify native protocols, including factory fidelity and throughput | **Conditional model only** |
| 5 | Physical architecture and causal scheduling | Implement native cost units, parallelism, routing, readout/feedback, loss/replenishment, resource factories, controllers, uncertainty; existing architecture Pareto and controller sensitivity studies remain | Substitute independently measured timing/quality where available and validate scheduling assumptions against a hardware experiment | **Illustrative model working** |
| 6 | Independent experimental holdouts | Use genuine distinct calibration epochs when matched protocols exist; evaluate disjoint within-job physical chains as a narrower holdout; train/holdout segregation, residuals, confidence intervals and provenance | Support old Fez d3/r3 Z chronology or use verified additional snapshots; validate across independent later epochs, not fabricated shot-level splits; extend to other families | **Cross-chain feasible; temporal hardware validation not established** |
| 7 | Same logical workload across four families | Executable common-workload conditional model with native resource units, logical failure budgets and sensitivity ranges | Hardware-calibrated and held-out-tested primitive inputs for each platform, realistic native compilation and measured bottlenecks | **Illustrative comparison working** |
| 8 | End-to-end automated reproducibility | GitHub Actions unit tests, Stim suite, source download checks, checksum and inventory, per-run logs, review bundles and upstream update PRs | Deterministic pinned external releases, safe large-data transport, paper-specific pipelines and reviewed scientific publication gates on hosted runners | **Automation framework built; live science steps incomplete** |

### Delivery priorities - software completeness versus experimental evidence

This table groups the eight requirements above into **parallel workstreams**. Priority refers to what we can implement and verify in software now; it does **not** certify a hardware-calibrated result or override the independent evidence gates.

| Workstream | Requirement IDs | Development priority | Immediate deliverable | Scientific boundary |
|---|---|---|---|---|
| **Software completeness - primary implementation focus** | **2, 4, 5, 7, 8** | **High - implement and integrate now** | Four platform-native noise-model interfaces; conditional Clifford/non-Clifford resource flows; controller/routing/factory scheduling; common-workload reporting; end-to-end download/test/report automation | Passing code tests establishes implementation correctness within assumptions, **not** independently calibrated physics or hardware predictions |
| **Experimental evidence - advance in parallel** | **1, 3, 6** | **High scientific importance - source-data dependent** | Authenticated calibration imports; paper-matched QEC/decoder reproductions; genuinely disjoint train/holdout measurements and uncertainty reports per platform | Only promote a result after source/protocol/decoder matching, independent evaluation, and review; not all needed measurements are currently public |

**Scope rule:** Both workstreams contribute to **Track B**. Protect Track A's completed d=9/d=11, Pareto, literature-benchmark, and controller-idle studies. Track B remains incomplete until its independent hardware evidence requirements are met for **each** family.

### Track B extension - calibration intelligence, AI-assisted interpretation, and QEC pre-decoding (planned)

**Motivation and scientific boundary.** IQM reported using NVIDIA Ising calibration models with its calibration software to assist in calibrating a 20-qubit superconducting chip (21 October 2026). NVIDIA's QCalEval is a benchmark for *interpreting calibration charts*, not for certifying calibration fidelity, deriving every physical noise parameter, or validating FTQC architecture predictions. Its described 243 charts span 22 experiment types; 57 are from real hardware, and the rest are simulated. NVIDIA also publishes Ising neural *pre-decoders* for surface and color codes. These are relevant analysis inputs, **not evidence that this project already uses AI calibration or has achieved improved logical fidelity**. Treat IQM as an additional **superconducting device profile**, not a fifth platform. Never transfer IQM calibration values to IBM Fez or to other devices.

**Central analysis question:** When a measured physical calibration parameter changes, how much does the *held-out predicted* logical error, decoder latency, physical resource requirement, architecture runtime, or Pareto frontier change? Can we rank candidate hardware improvements by expected FTQC benefit under measurement uncertainty, rather than merely by improvements to isolated qubit metrics?

| Phase / priority | Analysis scope and implementation | Reproducible deliverable | Verification / promotion gate |
|---|---|---|---|
| **CI-1 - High, nearest-term** | **Calibration evidence quality gate.** Parse per-device, per-qubit and per-coupler experiment records; normalize measured parameter, value, unit, physical indices, measurement method, timestamp, uncertainties, raw/derived distinction and source. Evaluate physical bounds, missing fields, covariance or correlation availability, fit residuals and stale/mismatched records. Flag which calibration inputs are *usable*, *restricted*, or *rejected*. | Versioned calibration schema and importer; rule-based QA with test fixtures; `calibration_quality.json` with evidence hashes, reasons, uncertainty and review status; platform-specific adapters, initially IBM. | Recompute a known fit or parameter from trusted numerical records; test malformed/stale/contradictory inputs; independently review provenance and QASM/device mapping. A passing schema check **does not** demonstrate physical accuracy. |
| **CI-2 - Medium, opt-in** | **QCalEval / Ising calibration-chart benchmark.** Reproduce a documented subset of QCalEval's chart-description, experiment-status, reasoning, fit-reliability, parameter-extraction and diagnostic tasks. Compare a classical numeric-fit or rule-based baseline, a general vision-language baseline where permitted, and NVIDIA Ising Calibration. Keep real-hardware and simulated-chart subsets separate. | Pinned benchmark split and licensing record; model identifiers and inference settings; structured predictions; per-task accuracy and parameter-error tables, false-acceptance rates, examples of incorrect diagnoses, and resource cost. | Held-out chart evaluation with no label leakage; human-checked calibration parameter extraction (units, uncertainty, confidence and measurement support); ambiguous chart interpretations are explicitly rejected or escalated. Benchmark scores **cannot** be used as qubit-noise calibration accuracy or FTQC validation. |
| **CI-3 - High scientific value, after project freeze** | **Neural QEC predecoder benchmark.** Test available NVIDIA Ising surface-code predecoders as a candidate front-end to PyMatching; retain unmodified PyMatching as the baseline. Use *identical* Stim circuits, code distances, rounds, basis, detector ordering, physical-noise assumptions, shot sets and decoding conditions. Expand to correlated/non-uniform noise only with a valid model/input contract. Color-code experiments belong in a separate, code-matched study rather than being compared as if they were surface codes. | Reproducible `baseline` vs `Ising predecoder + global decoder` experiments with logical-error Wilson intervals, paired comparisons, p50/p95/p99 decoder latency, throughput, CPU/GPU usage and model/source hashes. | Verify detector-event and correction conventions, no train/test leakage and reproducible matched trials; demonstrate any claimed improvement with uncertainty and actual hardware or simulator timing measurements. Published pretrained checkpoints may not match our circuit/noise model; GPU access or model terms may limit execution. |
| **CI-4 - High impact, after CI-1** | **Calibration-to-architecture sensitivity.** Feed only accepted, device-matched calibration evidence into the applicable superconducting noise layer; propagate uncertainty through physical-to-logical predictions, controller/readout/decoder scheduling and the existing Track A d=9/d=11 Pareto machinery. Extend by native mappings to photonic GKP, trapped-ion leakage/transport and neutral-atom erasure/loss *only after those adapters are independently calibrated*. | Traceable parameter-to-prediction dependency ledger; local and global sensitivity calculations, uncertainty bands, predicted bottleneck shifts and Pareto ranking for candidate improvements (e.g., readout, two-qubit gate, cycle time or decoder latency). | Held-out physical and logical observables, matched protocols and independently checked correlations; uncertainty propagation distinguishes sampled statistical intervals from assumed parameter ranges. Do not label a ranking actionable for hardware without validation. |
| **CI-5 - Exploratory, lowest priority** | **Human-supervised calibration recommendation agent.** Optionally propose the next measurement/sweep or tuning variable from a constrained action catalog. Use deterministic rules and simulated/archived datasets first; require explicit approval and a reversible audit record before any real-device action. | Offline recommendation replay with action provenance, uncertainty, stopping criteria, rejected proposals and side-by-side expert/rule-based control. | No unattended hardware control; independently confirm parameter-improvement attribution and absence of degraded neighboring qubits or unacceptable stability effects before claiming value. |

**Required data and interface contract.** Each calibration observation must carry `device_id`, `hardware_family`, `physical_targets`, `experiment_type`, `measured_at_utc`, `source_uri`, `source_sha256`, `quantity`, `value`, `unit`, `uncertainty` (or an explicit missingness flag), `fit_method`, `quality_status`, `review_status` and any correlated-error/measurement-context information. Chart-extracted values are *proposals* until confirmed against numerical experiment records or a trustworthy calibration report. Never fill an unknown uncertainty or correlation with a fabricated estimate. Archive model version, prompt/configuration, runtime and deterministic review decisions with each assessment.

**Connection to the eight requirements and 34 evidence gates.** CI-1 strengthens requirements **1, 2, 6 and 8** (provenance, noise calibration, held-out evaluation, automation); CI-2 supports **1 and 8** as a tool-evaluation activity, but does not itself pass a full-stack gate; CI-3 strengthens **3, 5 and 6** (QEC decoding, latency, held-out comparisons); CI-4 strengthens **2, 5, 6 and 7** (noise-to-architecture mapping and common workload); CI-5 is exploratory and cannot substitute for any of the eight. File QA, benchmark success and model downloads **never auto-approve** a scientific gate. Submit per-device, per-protocol candidate dossiers with explicit independent review before promoting any evidence to the existing 34-gate acceptance ledger.

**GitHub implementation and release policy.** Add future external-source downloads under ignored `data/external_hardware/` with pinned revisions, checksums, licenses and disk budgets. Keep AI inference and large GPU/model downloads in **manual/opt-in** jobs, not required PR CI. Publish compact anonymized/sanitized evaluation summaries, numerical figures and source manifests as artifacts; use a review PR for source/model upgrades and never automatically accept newly extracted calibration values. CI-1 rule-based QA may run in regular CI after it has deterministic small fixtures. **Do not postpone or relabel the  project release for this extension:** all CI-1 through CI-5 tasks are currently *planned*, while Track A's existing experiments and Track B's existing verified evidence stay unchanged.

**Primary sources (checked 2026-11-01):**
- IQM, *What happened when we let AI calibrate a quantum chip using NVIDIA Ising* (21 October 2026): https://iqm.tech/blog/what-happened-when-we-let-ai-calibrate-a-quantum-chip-using-nvidia-ising/
- NVIDIA, QCalEval benchmark scripts and dataset instructions: https://github.com/NVIDIA/QCalEval
- NVIDIA, Ising model family, tools and model catalog: https://github.com/NVIDIA/Ising
- NVIDIA, Ising QEC decoder training/inference recipes: https://github.com/NVIDIA/ising-decoding

### Immediate prioritized work (project branch)

- [x] Retain d=9 surface-code/Stim analysis, d=11 illustrative Pareto frontiers and architecture unit accounting. Do not call site-equivalents physical qubits.
- [x] Decode supported Fez repetition-code raw measurements; record every excluded QASM protocol.
- [x] Analyze full decoded data descriptively even with only one supported calibration epoch.
- [x] Add predeclared, source-separated physical-chain holdouts, labeled as *within-epoch empirical transfer*, not a temporally independent calibrated prediction.
- [x] Audit original archive calibration timestamps and identify exactly which paper protocol could enable the true temporal holdout.
- [ ] Reconstruct the unsupported original Fez `d3_r3/job_2` circuit semantics using the authors' methodology; independently validate syndrome parity and readout chronology before decoding. **Never bypass the guard without protocol validation.**
- [ ] Evaluate earlier versus later **matched** `d=3, r=3, Z` measurements, training only on earlier calibration; compare errors and intervals. Independently check execution order.
- [ ] Download/analyze Kingston and Pittsburgh datasets to find additional verified repeated calibration/protocol subsets. Train/holdout **within each physical backend** first; do not pool distinct processors as one calibration.
- [ ] Independently reproduce named photonic, trapped-ion and neutral-atom QEC/logical measurements; source-verify all numerical exports.
- [ ] Add native calibrated physical-to-logical models, logical Clifford+T flows, resource factories and held-out end-to-end validation per platform.

### Why the strict audit can report 0/34

`evidence/validation/four_family_evidence.json` intentionally starts empty. The 34 checks correspond to **full-stack scientific evidence contracts**; they are not a count of functioning modules, lines of code or completed source inspections. The gate requires verified, source-hashed artifacts **and** separate scientific review. Do not mark gates as verified just because simulated experiments, the IBM raw decoder, an Aurora replot or an empirical chain holdout passes. Small source-data studies should have their own scoped evidence receipts until the scientific protocol is independently checked.

### IBM authentic holdout taxonomy

1. **Source-descriptive:** decoded logical failure rates with matching shot, basis, distance, rounds, calibration timestamp and decoder, plus Wilson intervals. This can always run on recognized shots.
2. **Within-job physical-chain:** choose the highest chain index *before examining outcomes*, fit the empirical failure probability on all other chain indices for the same `(backend, job, calibration, distance, rounds, basis, state, decoder model)`, and test the withheld chain. Real disjoint physical-chain measurements, **not** temporally independent, and shared correlated hardware noise may invalidate iid interval interpretation.
3. **Different calibration epochs:** fit on earlier **same-protocol** jobs, compare with later disjoint jobs; no reuse of test data to select decoder or tune priors. Distinct stored calibration timestamps must be confirmed to represent actual experiment chronology. The Fez archive has one older `d3_r3/job_2` Z job whose QASM currently requires unsupported chronology handling, and 40 later jobs.
4. **Circuit-matched calibrated prediction:** independent training fits a calibrated detector/circuit noise model; frozen predictions and decoder are then evaluated against unseen logical-failure measurements. Neither the within-job baseline nor a chronological split alone establishes this level.

Run `python3 scripts/automation/ibm_epoch_audit.py` after downloading Fez; audit output `outputs/external_validation/IBM_CALIBRATION_EPOCHS.json` is included in the review bundle. The IBM statistical step writes both descriptive summaries and authentic available cross-chain/temporal comparisons without failing merely because one holdout class cannot be evaluated.

## Milestone 1 - matched experimental validation

1. **IBM:** finish full Fez extraction with an auditable exclusion report; independently check syndrome ordering and detector parity against authors' code; fit detector error model to training snapshots; compare predicted failures on later holdout snapshots, with intervals and residuals; do not transfer repetition-code calibration into surface-code FTQC without matching experiments.
2. **Xanadu:** reprocess original Aurora optical quadratures or GKP conditioned-state data and reproduce a named paper observable with uncertainty; fit loss/squeezing and feedforward parameters and hold out experimental records.
3. **Quantinuum:** safely derive a trusted numeric export of a named Helios benchmark from the authors' `.p` experiments through an auditable controlled procedure; independently compute the statistic, then select native FT logical-code measurements for model calibration.
4. **Neutral atoms:** download and audit the published loss-aware surface-code data, reproduce distance-3 vs distance-5 logical failure per round with matching paper decoder, loss policy and uncertainty; isolate the Harvard/QuEra analysis processor from commercial Aquila claims.

## Milestone 2 - physical-to-logical native code models

Document device noise/correlations/erasures, compile matched executed circuits, validate syndrome and decoder implementation with raw data. Build platform-native physical-to-logical QEC models and logical Clifford observables with independent calibration/validation splits.

## Milestone 3 - non-Clifford and universal computation

Specify each platform's native logical T/injection path, accepted magic-state quality, distillation inputs, output error and verified logical operation protocol. Simulate and benchmark those primitives without substituting unverified assumed T rates.

## Milestone 4 - causal architecture and resources

Replace toy timing and site budgets with sourced gate/round durations, transport, optical feedforward, atom loss/replenishment and controller parallelism; implement actual scheduling/compilation and physical resource allocation with uncertainty, finite factories and supply constraints. Use the **same logical workload**, not the same physical-gate schedule.

## Milestone 5 - external validation and release

Freeze source revisions and train-only calibration. Evaluate disjoint later hardware measurements, publish honest residuals and model uncertainty, document extrapolation boundaries. Only then publish four independent platform-native end-to-end conditional predictions; reserve "validated FTQC prediction" for matched observables actually checked against hardware.

## Release governance

Raw vendor data and large archives stay out of Git, with SHA-256 manifests. Save CI logs as GitHub Actions artifacts. Publish versioned release outputs and provenance after review; don't archive the active GitHub repository. Never auto-merge scientific data updates or adjust held-out splits without review.


## Experimental validation additions (without modifying earlier milestones)

| Analysis area | Added implementation now | Next genuine scientific gap |
|---|---|---|
| IBM physical calibration | Per-qubit state-dependent readout Poisson-binomial majority baseline, observed hardware residuals and confidence intervals | Full native circuit-level correlated detector/noise calibration, frozen matched train/holdout predictions |
| Quantinuum Helios | Non-executing raw MCMR histogram reader and independent 360-condition count verification against saved marginals | Reproduce authors' constrained-fidelity global fit and verify held-out logical QEC data |
| Quantinuum specs | Independently reanalyzed H-series / REIMEI JSON survival-count datasets, device identities separate | Match native Helios physical and logical protocols, no cross-device calibration conflation |
| Neutral atoms | Opt-in checksum-verified full Zenodo archive download; safe shot-format survey | Source-specific atom-loss/erasure parsing and author-matched loss-aware trained decoder; d3/d5 per-round result |
| Photonics | Aurora Figure 3c/3d workbook replot preserved; optional verified-units numerical quadrature interface | Process original author optical records and reproduce named paper observable, GKP native noise calibration |
| Native workload | Four separate, clearly hypothetical hardware-specific profiles; evidence-backed physical primitive ledger independent of workload math | Validate physical-to-logical mappings, error correlations, factories, scheduling against independent hardware records |
| Acceptance | Thirty-four gate candidate dossiers with artifact SHA-256, explicit reviewer requirements, no auto-approval | Independently review and approve qualifying artifacts, separately per hardware family |

The repo's **Track A** simulator results remain unchanged. **Track B** partial measurements do not automatically satisfy 34 full-stack acceptance contracts. The best verified near-term external result is an independently recomputed Helios MCMR count dataset, plus IBM measured readout-only predictions; both are narrower than FTQC stack validation.
