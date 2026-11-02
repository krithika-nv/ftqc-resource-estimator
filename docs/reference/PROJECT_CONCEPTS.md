# Project concepts and knowledge map

> Current documentation is authoritative only for the specific claims supported by linked measured data, simulation outputs and tests.

## Scientific and software concepts

**Scope:** Scientific and software concepts implemented, invoked or investigated in this project. This is a study guide rather than evidence that all topics have been experimentally validated. Read `docs/validation/EVIDENCE_AND_RESULTS.md` for evidence status.

### 1. Computational objective and layers

- **Quantum physical information:** physical qubits, continuous-variable modes, basis states, measurement outcomes, quantum channels, coherence, leakage and loss.
- **Quantum error correction (QEC):** redundancy protects a logical degree of freedom by repeatedly measuring stabilizers; measurement outcomes produce a syndrome that informs a classical decoder.
- **Fault tolerance (FT):** circuit construction that suppresses propagation of physical faults into logical failures, encompassing state preparation, measurements, Clifford operations, non-Clifford operations and fault-tolerant control.
- **Fault-tolerant quantum computing (FTQC):** execution of long logical workloads with resource overhead and total logical failure kept within a specified budget.
- **Architecture estimation:** predict physical resource count, control capacity, communication/supply limits, logical error, runtime and uncertainty under explicitly defined physical models.
- **Workload specification:** a common collection of logical operations (preparation, memory cycles, Clifford 1Q/2Q gates, T gates and measurements). Comparing its *logical task* across technologies is more meaningful than equating individual native gates.
- **Model hierarchy:** measured physical characterization → circuit-level noise model → native QEC/decoder → logical operations → resource-state/factory model → routing/scheduling → workload prediction → experimental holdout. Each arrow needs its own evidence.

### 2. Quantum information and noise

**Qubit:** a normalized state in a two-dimensional complex Hilbert space, `|ψ⟩ = α|0⟩ + β|1⟩`, `|α|²+|β|²=1`. **Density matrix:** `ρ` allows ensembles and mixed/noisy states. **Channels:** CPTP maps represent noisy physical evolution, often with Kraus operators. **Entanglement** and tensor products describe multi-qubit states and nonclassical correlations. **Measurement:** POVMs or projective measurements produce classical outcomes, potentially perturbing the quantum state.

**Pauli operators:** `I, X, Y, Z`; bit flips and phase flips form a convenient error basis. A *Pauli channel* is an approximation; **coherent errors, correlated faults, non-Markovian noise, leakage, erasures and loss** may violate it. **T1** captures energy relaxation; **T2** captures transverse coherence and depends on the measurement protocol (echo/CPMG is not automatically free-idle T2). **Depolarizing noise** is a convenient effective model, not universally hardware calibrated.

**Measurement error** includes assignment error/SPAM; **gate errors** may depend on qubit pair and simultaneous operations; **crosstalk** couples otherwise separate operations. **Decoder latency** can create extra idle noise. Real error data are correlated in time and space, so extrapolating a single primitive error rate to an entire algorithm requires validation.

### 3. Stabilizers, codes and decoding

**Stabilizer code:** the protected code space is the joint `+1` eigenspace of commuting stabilizer operators. The *syndrome* records departures from expected stabilizer parity. **Code distance `d`:** minimum weight of an undetectable, nontrivial logical operator; increasing distance may suppress error below threshold but increases hardware cost.

**Repetition code:** protects against one Pauli error type; `d` physical data bits/qubits with `d−1` parity checks. It is a useful real-hardware benchmark but **does not** protect a generic unknown qubit against both X and Z errors. **Surface code:** 2D local checks protecting two Pauli types; **rotated surface-code memory** provides a concrete Stim benchmark. **Logical X/Z:** encoded operations that commute with stabilizers but act nontrivially on the logical state.

**Repeated syndrome rounds:** a syndrome measurement is itself noisy. Detection events often use differences between adjacent rounds: `D_t,j = s_t,j XOR s_(t−1),j`; final data parity can close the graph. **Measurement layout and bit endianness** must come from the executed QASM, not intuition. **MWPM (minimum-weight perfect matching):** matches detection events using edge weights `log((1−p)/p)` under a specified detector-noise model. **PyMatching** is the graph decoder used in this repo. **Stim** efficiently samples stabilizer circuit errors and detector events. **Majority voting** is a baseline with different assumptions; compare only on identical shots/protocols.

**Matching graph boundaries:** possible error chains terminate at spatial/time boundaries. **Logical failure:** decoded result differs from the intended encoded observable. **Phenomenological decoder:** assumes simple data/measurement error priors; **circuit-level decoder:** noise attached to actual gates/measurements with detector error models. **Calibration-weighted decoder:** noise parameters fitted from real-device records. **Machine-learning or loss-aware decoder:** conditions on more features, including atom-loss flags or correlated patterns; it cannot be replaced by majority vote without changing the paper's method.

**Threshold / pseudo-threshold:** regimes where higher distance improves logical failure with controlled physical noise. **Memory experiment versus logical gate:** a protected idle memory alone does not validate fault-tolerant two-qubit gates, magic-state consumption or a universal workload.

### 4. IBM superconducting platform

**Transmon:** superconducting qubit encoded in circuit energy levels, driven by microwave pulses; **couplers/connectivity** constrain where two-qubit operations are possible. **Readout resonator and dispersive measurement** map state-dependent response to classical bits. **QASM 2/3** represent *executed* circuits; IBM QASM3 here uses physical `$n` qubit references and classical bit arrays such as `c_data_<chain>` and `c_syndrome_<chain>`.

The Stein et al. public release includes `info.json`, `calibration.json`, `circuit_state0.qasm`, `circuit_state1.qasm` and `bitstrings.json` per job. In the real Fez data, `bitstrings.json` has a list of two entries, with `metadata.logical_state` and `per_shot_cregs`; per-register shots are explicit bit arrays. **Epoch:** hardware calibration timestamp associated with an experiment. **Shot:** one repeated circuit execution. **Chain:** an independent repetition-code chain on a processor. This repository checks expected register size, executed QASM measurement targets and per-state identity, using a majority baseline and optionally phenomenological MWPM. A rejected QASM order must be separately analyzed, not silently included.

**Calibration parameters:** gate/readout error, T1/T2, gate durations, backend and qubit mapping; they describe device characteristics but do *not automatically* establish logical surface-code or FTQC predictive accuracy. **Held-out epochs:** choose a later, disjoint hardware measurement period after fitting, preventing train/test leakage. **Circuit-matched prediction:** simulate the same gates, qubits, noise and measurement schedule before comparing to raw measured logical failures.

### 5. Xanadu photonic platform

**Photonic encoding:** information in optical modes or photonic qubits; distinguish continuous-variable Gaussian modes from discrete-variable qubits. **Squeezing:** reduces noise in one quadrature at the expense of the conjugate; **GKP code:** embeds a qubit into grid states of an oscillator and uses analog displacement syndrome information. **Homodyne detection** measures optical quadratures; **feedforward** adjusts subsequent processing conditionally on classical measurements.

**Loss / transmission / detector efficiency** are essential physical inputs; **fusion/entanglement generation** and **state supply** determine FT resource throughput. **Cluster/graph-state generation** enables measurement-based quantum computation. **Aurora** supplies published numerical figure data for 3c/3d, which this repo replots and compares. **Matrix RMSE, mean absolute residual, relative Frobenius error** quantify numerical differences between the workbook's experimental and simulated matrices; they are **not** proof of a calibrated GKP logical gate. The much larger optical quadrature datasets require their own independent reconstruction and uncertainty model.

**Resource-state factories:** purified or distilled non-Clifford states may be necessary depending on the architecture; photonic resource modes are not directly equivalent to superconducting physical-qubit counts.

### 6. Quantinuum trapped-ion platform

**Ion qubits:** internal ion states manipulated with laser/microwave fields; **ion transport/shuttling** and zones affect connectivity and parallelism. **Native gate fidelity, leakage, SPAM, idle lifetime, crosstalk, transport cost** enter hardware models. **Mid-circuit measurement and reset (MCMR)** affect control loop latency. **Randomized benchmarking (RB), cycle benchmarking, mirror circuits** estimate different operation-level statistics and can have distinct assumptions. A benchmark's reported infidelity or fit must not be equated with universal logical failure.

The Helios paper-data repo includes Python experiment code, saved notebook outputs and `.p` serialized experiments. The safe notebook reader only extracts five reported MCMR error-channel values with source hash; **it never unpickles or executes the author's experiment code**. Such extracted numbers are *author-cached results*, not independent reanalysis. To reproduce measured statistics from `.p` raw experiments, obtain an independently verified numeric export using a controlled, auditable environment and confirm the authors' fitting routine, trial definitions and uncertainty.

**Logical ion code choices** and **non-Clifford resources** require their own experimental evidence; gate-level characterization does not prove full-stack logical FTQC.

### 7. Neutral-atom platform

**Neutral atom:** trapped individual atoms, often manipulated by optical tweezers and Rydberg interactions. **Rydberg blockade / entangling gates**, **atom loss, erasures, rearrangement/transport, imaging/readout, replenishment** and multiple interaction/storage zones dominate native engineering tradeoffs. **Reconfigurable arrays** permit moving atoms rather than only applying gates on a static coupling graph.

The Bluvstein et al. neutral-atom surface-code record provides a potential matched QEC benchmark: a reported distance-5 versus distance-3 per-round error-suppression factor under specified *loss-aware decoding*. The published factor may be cited as a source result but MUST NOT be attributed to a calculation here until the original shot format, loss-mask policy, source decoder and uncertainty have been independently reproduced. The previous Aquila randomized-measurement/entanglement experiment is scientifically valid but measures another property - not QEC performance on the Harvard-led system.

### 8. Universal fault tolerance and non-Clifford operations

**Clifford group** operations map Paulis to Paulis; circuits containing only stabilizer inputs, Clifford gates and Pauli measurements can often be simulated efficiently classically (Gottesman–Knill). **T = diag(1, exp(iπ/4))** is non-Clifford; together with Clifford gates it supplies a common universal gate set. **Magic-state injection** consumes a high-fidelity resource state to implement a non-Clifford logical gate. **Magic-state distillation** trades noisy copies for fewer, cleaner states, requiring physical/logical patches and scheduling.

**State acceptance probability** controls average number of factory attempts `E[attempts]≈N_T/p_accept` under independent repeated acceptance. **Resource-state error per accepted state** affects computation reliability; it is not identical to acceptance/rejection probability. **Factory lanes** and controller capacity affect throughput. Universal FTQC cannot be validated from QEC memory data alone.

### 9. Resource estimation, scheduling and reliability

**Resource budget:** qubits/ions/atoms/optical modes, ancillas, readout/control resources, factory sites, routing/storage and interconnects; report in each technology's *native units*. **Latency:** gate and cycle durations plus measurement, classical decode, feedforward and transport; not all delays can overlap. **Throughput / bottleneck:** slowest pipeline stage constrains completion. **Pareto frontier:** nondominated tradeoffs in runtime, resources, and/or reliability; an infeasible point must not appear as a valid solution.

For **conditionally independent** logical operation failures `p_i` used `n_i` times, `P_success ≈ ∏_i (1−p_i)^(n_i)`. For a memory with per-round failure `p_L`, `P_survival ≈ (1−p_L)^R` assumes matched rounds and independent failures. These are approximations, not proofs of correlated-noise behavior. The conditional architecture tool includes T-state quality and acceptance, plus **optimistic and pessimistic scheduling envelopes**, explicitly *not a compiler-derived schedule*. It uses identical toy rates for all four hardware families to **avoid suggesting a real cross-platform winner**; native resource units remain distinct.

**Failure budgets:** divide an acceptable algorithm-failure target among memory, gates, measurements, distillation and communication; correlations invalidate simple independent allocation. **Supply demand and expected wait:** factories can be the rate-limiting stage even if computation has fast gates. **Controller-induced idle noise:** limited simultaneous measurements prolong storage and can increase simulated logical errors. The manuscript's control-cost estimates remain assumption-driven pending calibrated timing.

### 10. Statistical methods and scientific validation

**Binomial trials:** for `f` failures in `N` matched shots, estimate `p̂=f/N`; **Wilson interval** retains nonzero uncertainty even when `f=0`. **Uncertainty propagation** should include measured statistical errors and unknown systematics. **Confidence intervals are not identical to Bayesian credibility intervals**. **RMSE/MAE** summarize prediction residuals on matched observations, but calibration also needs a consistent protocol and held-out data.

**Training versus holdout:** choose independent device jobs and preferably later epochs; do not select weights or tune noise parameters on holdouts. **Leakage:** reuse of the same shots or calibration epochs invalidates predictive claims. **Source reproducibility:** source DOI/URL, exact revision, SHA-256, timestamp, decoder version, circuit hash, shot count, fitting specification and license. **Reproduction levels:** rerender published numbers, recompute from author-supplied reduced data, reprocess raw device shots, then independently predict held-out outcomes. Each is valuable but not interchangeable.

**Validation hierarchy:** (1) unit tests; (2) synthetic fixture regression; (3) real Stim+PyMatching simulator replay; (4) external source-data reproduction; (5) source-specific decoder agreement; (6) held-out hardware prediction; (7) full-stack workload prediction cross-checked with matching logical operations. Passing layer 1 is never a claim of layer 7.

### 11. Software engineering and automation concepts

**Analysis repo:** `src/ftqc_resource_estimator/` models and simulation; `external_validation/` real-source adapters; `evidence/validation/` acceptance contracts; `scripts/automation/` downloads, run orchestration, provenance checks; `tests/` unit and regression tests; `outputs/` generated results; `logs/runs/` timestamps, step logs, manifests. Raw vendor files are ignored by Git.

**CLI pipeline:** scripted profiles (`ci`, `science`, `evidence`, `ibm`); partial/blocked results remain visible. **GitHub Actions** runs checks and caches/upload artifacts; **Dependabot** proposes library and workflow updates; upstream source revision updates should be reviewed in PRs and not silently change a scientific baseline. **Provenance manifests** record exact inputs, hashes and output statuses. **Atomic output writes** protect against partial files; **schema guards** fail closed when experimental metadata or QASM ordering is ambiguous. **Pickle risk:** untrusted serialized Python objects can execute code on load; safe extraction uses JSON, CSV and stored notebook output text, not `pickle.load`.

**Claims ledger:** distinguish `measured`, `author_reported`, `source_figure_replot`, `simulated`, `conditional_illustrative`, `not_validated`. **Archiving:** archive reviewed analysis releases/results, not the active GitHub repository; retain original source provenance and a specific version tag.

### 12. Technical discussion and design questions

1. Define the precise workload, failure target and hardware-native resources before comparing devices.
2. Explain why rotated surface-code memory cannot validate a magic-state factory or other codes by itself.
3. Walk through a real IBM shot: QASM register mapping → per-round syndrome → detection events → decoder → logical failure → Wilson interval.
4. Distinguish a phenomenological MWPM prior from a calibration-weighted circuit detector error model.
5. Explain the difference between Aurora workbook replotting and analyzing optical quadrature acquisition data.
6. Explain why the Helios saved notebook numbers are valid *author outputs* but not independently reproduced fit statistics.
7. Describe what the neutral-atom loss-aware decoder must preserve to reproduce the published suppression factor.
8. Show how T-state supply, readout concurrency and idle noise become competing resource bottlenecks.
9. Describe chronological held-out validation and what scientific conclusion would be justified if it succeeds or fails.
10. State limitations proactively: **the repo is analysis software with verified simulations and scoped public experimental evidence, not a certified four-platform calibrated universal FTQC predictor**.

### 13. Suggested primary reading and sources

- Nielsen & Chuang, *Quantum Computation and Quantum Information* - states, gates, stabilizers, circuits, QEC.
- Gottesman, *An Introduction to Quantum Error Correction and Fault-Tolerant Quantum Computation* - stabilizer/FT foundations.
- Fowler et al., *Surface codes: Towards practical large-scale quantum computation* - surface-code methods.
- Gidney, *Stim: a fast stabilizer circuit simulator* - simulator architecture and detector models.
- Higgott and Gidney, *Sparse Blossom: correcting a million errors per core second with minimum-weight matching* - matching methods.
- IBM Stein et al. raw repetition-code dataset: https://doi.org/10.5281/zenodo.20768087
- Xanadu Aurora public figure and optical-data repo: https://github.com/XanaduAI/xanadu-aurora-data
- Quantinuum Helios paper-data repo: https://github.com/Quantinuum/Helios-paper-data
- Neutral-atom surface-code experimental data: https://doi.org/10.5281/zenodo.15685795

**Scope reminder:** The links identify scientific inputs. This document does not claim the repository independently validated every cited paper.

## Knowledge map and review questions

**This document distinguishes demonstrated skills from topics that the repository only references.** It is a project knowledge map, not a credential or independent authorship certificate. See [the evidence ledger](../validation/EVIDENCE_AND_RESULTS.md), [methods](../methods/METHODS.md), [provenance](PROVENANCE_AND_CLAIMS.md), [limitations](../validation/LIMITATIONS.md) and [development history](../methods/METHODS.md).

| Domain | Demonstrated in executable code or documented mathematical investigation | Not yet demonstrated |
|---|---|---|
| **Quantum information and QEC** | Rotated surface-code X memory; stabilizer syndrome sampling; code distance and syndrome rounds; logical memory failure; mathematical repetition-code sanity check; limitations of memory versus logical gates | Novel code construction; complete fault-tolerant logical gates, lattice surgery, distillation, GKP |
| **Decoding and circuit-level simulation** | Stim-generated stabilizer circuits, detector-error models, PyMatching MWPM, seeded Monte Carlo and exact replay; independent backend verification on owner's Mac for original run | New decoder algorithm; circuit calibration to real pulse-level schedules |
| **Probability, reliability and statistics** | Independent-event reliability budgeting, Wilson score uncertainty, sample-size planning, empirical failure rates, propagation and Pareto feasibility under assumptions | Joint-correlated reliability guarantees; family-wise statistical confidence; predictive real-device statistical validation |
| **Quantum hardware physics** | Coherence times T1 and Hahn-echo T2; relaxation-only noise approximation; per-qubit historical device calibration; gate and readout errors/durations, couplings; explicit distinction from Ramsey T2-star | Measured unprotected free-idle Ramsey T2*, calibrated correlated/leakage/ZZ noise, pulse-level timing and crosstalk |
| **Hardware-aware architecture & systems co-design** | Models resource factory throughput, transmission sensitivity, abstract physical-site footprints, controller readout capacity, scheduling latency, cost-versus-latency constraints; different hypothetical platforms' internal sensitivities | Verified readout concurrency and electrical power, complete superconducting/photonic/ion resource forecast, factory/hardware integration |
| **Scientific computing** | Python modules, reproducible JSON/CSV reports, programmatic experiments and plots, schema validation, deterministic tests, versioned data provenance and replay audits | Independently peer-reviewed original scientific method and externally verified hardware claims |
| **Analysis methodology** | Explicit hypotheses, initial failed-feasibility result, follow-up distance-9 result, protocol variants, source attribution, alternate models, documented negative outcomes, calibration evidence classification | Literature-matched quantitative benchmark with held-out real hardware outcome completed for this repo |
| **Experimental data engineering** | Normalize real IBM historical backend-properties fields, preserve timestamp and upstream source, check units and couplings, derive *labeled* conditional noise input, hash files | IBM Runtime account connection, automatic access to live backend, matched job-time shot labels, validated real-QPU prediction |

### A concise technical summary

> This analysis prototype integrates existing QEC circuit simulation and decoding tools with reliability-aware code-distance assessment, resource tradeoffs, and hardware calibration-data ingestion. It explicitly distinguishes observed simulator results, real published hardware measurements, noise-model approximations, and hypothetical architecture scenarios. The current contribution is a reproducible cross-layer *analysis workflow*, not a new quantum error-correcting code, decoder, or validated hardware predictor.

### Concrete defense questions

- Explain why increasing code distance can lower decoded logical-memory error but increase physical-qubit overhead. What changes with repeated syndrome rounds?
- Why are `T1`, Hahn-echo `T2` and Ramsey `T2*` different? What happens if an unknown phase-error channel is approximated as zero?
- Why can an error value from RB calibration not be inserted unchanged as a literal physical error in every circuit Clifford operation?
- Which assumptions make `1-(1-p)^40` usable? What breaks when faults are correlated?
- Why is a d=3 repetition-code demonstration on a five-qubit linear device not evidence for a d=3 *rotated surface-code* implementation?
- How would you validate prediction quality with held-out real QEC shots and timestamps, and what would count as falsification?
