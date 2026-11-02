# Provenance, scientific claims and figure checks

> Current documentation is authoritative only for the specific claims supported by linked measured data, simulation outputs and tests.

## Method and source provenance

### Classification

This repository is an **analysis prototype integrating established simulation/decoding algorithms with architecture, uncertainty and controller-sensitivity analyses**. It is neither a verbatim reproduction of one published code repository nor a claimed invention of the surface code, matching algorithm or underlying statistical estimators.

### Sources and credit

- **Third-party algorithms:** Stim [R2] supplies stabilizer circuits and detector sampling; PyMatching [R3] supplies MWPM decoding. Riverlane's public tutorial [R4] provides a substantially similar rotated-X memory protocol, including four noise knobs and `rounds=distance`; its scientific methodology is explicitly credited. See [REFERENCES.md](REFERENCES.md).
- **Conceptual literature:** Fowler et al. [R1], Litinski [R10]; Google/Willow source [R5]; Kan et al.'s experimental measurements [R6]. Published IBM figures are **secondary, credited numerical summaries**, not our experimental data.
- **Project-specific code and analysis:** reliability-budget linkage to an assumed 40-event workload, conditional resource and scheduling comparisons, independent observation/replay gates, noise-channel scenario sweeps, evidence ledger, and fail-closed release logic.
- **Originality claim boundary:** this integration is independently assembled within this project; scientific novelty against all prior art has **not** been established. An internet spot check is not a complete code-uniqueness or license audit. Do not claim originality of third-party algorithms or a first demonstration.

### How to speak about the project

Appropriate: “I evaluated reliability-constrained code-distance choices using Stim/PyMatching memory experiments, then studied conditional controller scheduling and idle-noise tradeoffs, with separate assumptions and published hardware benchmarks.”

Not appropriate: “I invented a QEC decoder,” “I validated a Willow simulator,” “our readout performance is better than IBM,” or “this code reproduces Kan et al.'s full hardware experiment.”

### Attribution and analysis integrity checks

1. Cite the established algorithms, tutorial protocol, Wilson statistics and every sourced hardware number [R1–R13].
2. Review the source code, third-party dependencies and scientific methods before publication.
3. Regenerate the exact experiment on the owner's system and inspect the output before authorizing its publication.
4. Distinguish a **method replication**, **secondary literature arithmetic**, **new conditional sensitivity study**, and **genuinely measured hardware experiment**.
5. Preserve original author PDFs under their own licenses; do not commit paywalled or copyrighted source material without permission.

For a fuller scientific preprint or analysis submission, perform a dedicated prior-art and dependency-license audit; current project metadata alone does not certify either.

### New  data provenance boundary

The `ibmq_manila` May 27, 2024 hardware property values in `examples/public_ibmq_manila_2024_subset.json` originate from **Qiskit's public archived backend-properties record** [R11]; these measurements are **not** original measurements by this project's author. The offline parser, strict data-contract checks and conditional Stim integration are project-specific implementations. The complete original upstream file has **not** been redistributed or fully SHA-authenticated in this handoff; an independent download command is provided. Neither this source nor a simulation generated from its averages certifies hardware predictive accuracy. Source attribution, measurement definitions, and limitations are in [PUBLIC_CALIBRATION_IMPORT.md](../hardware/CALIBRATION.md).

###  modern data source and method attribution

The 2026 Fez/Kingston/Pittsburgh archive belongs to Stein and collaborators [R9]. The importer is project-specific code; the earlier stage was tested with schema fixtures, **not** the full authenticated Zenodo raw archive in that delivery. IBM's authenticated live QPU characterization interface is described in [R7–R8]; it does not grant authorship of IBM hardware measurements. Historical Manila snapshots [R11–R12] remain explicitly labeled archived examples. Wilson score intervals [R13] are established statistical methods.


### Explicit physical-platform attribution boundary

- The per-family sensitivity arithmetic is an **independent, hypothetical implementation** in `hardware_profiles.py`. No published vendor performance was recreated or measured by these scenarios. Consult [PLATFORM_BOUNDARIES.md](../methods/PLATFORM_BOUNDARIES.md).
- IBM dated characterization input is **third-party measured hardware data** [R7–R9, R11]; the import/normalization code and claim guard are project-specific implementations. Neither imports nor synthetic tests demonstrate new experimental measurements or a calibrated IBM QEC noise model.
- Stim/PyMatching and the surface-memory protocols remain established third-party software/methods [R1–R4]. This software uses them to ask conditional architecture/reliability questions; it does not claim original surface-code or decoder algorithms.

## Figure and claim checks

**This file is included by `scripts/tools/prepare_results.py`; do not remove or rename it.** See the full [evidence ledger](../validation/EVIDENCE_AND_RESULTS.md), [limitations](../validation/LIMITATIONS.md) and [references](REFERENCES.md).

| Figure / result | Input provenance | Supported claim | Unsupported claim |
|---|---|---|---|
| `outputs/architecture_study/feasible_tradeoffs.png` | Hypothetical architecture scenarios, heuristic logical error | Two nondominated **model** configurations under stated choices | Calibrated superconducting/photonic hardware costs |
| `outputs/stim_memory/analysis/memory_logical_failure.png` | Owner-executed 180k Stim/PyMatching baseline, fixed nine rounds | Decoded memory logical failure at stated p and distances | Device logical-gate error or full FTQC overhead |
| `outputs/stim_memory/followup/...` | Owner-executed 40k separately seeded d7/d9 | Under assumed 40-independent-event budget, d9 passes per-experiment upper Wilson screen | Hardware threshold; simultaneous 95% whole-system guarantee |
| `outputs/controller_capacity_preview/*.png` | Synthetic concurrency/cost/latency inputs | Conditional capacity/scheduling sensitivity | Actual controller channels, power, QPU timing |
| `outputs/idle_coherence/inputs_only/*.png` | Published Willow T1, T2_CPMG combined with **hypothetical** controller parameters | Input extra-Pauli-event probability under a Pauli twirl | Observed logical memory failure; calibrated unprotected idle |
| `outputs/published_readout/published_readout_comparison.png` | Kan et al., arXiv:2610.23840v1, Fig.2; rounded published Nighthawk values | **Secondary arithmetic redrawing**, logical ε per *round* | Our own hardware measurement; derived independent single-qubit Pauli rates |
| Planned `outputs/literature_benchmark/*` and `outputs/idle_coherence/idle_logical_failure.png` | Real backend must execute first | No scientific performance claim yet | Complete comparison or calibrated idle decision before replay |

### Claim checks

- **Never convert a detector-pair percentage-point change into a per-qubit Pauli event rate.** Kan et al. [R6] distinguishes those observables.
- **Never mix Willow and IBM Nighthawk values into a named calibrated processor.** Same-device scheduling, free-idle Ramsey and crosstalk are absent [R5–R8].
- **Never infer readout channel counts from readout instruction duration**, or power watts from qubit counts.
- **Never describe existing Stim/PyMatching algorithms as original code inventions** [R2–R4].
- **evidence status:** old owner-provided baseline has real replay metadata. The new additional benchmark and idle-noise study still need external backend execution and full validated publication. GitHub Action is configured, not reported as executed.

This is a methods-focused analysis prototype; its negative and infeasible outcomes must remain in the report. All claims are conditional on explicitly fixed input models and event definitions.
