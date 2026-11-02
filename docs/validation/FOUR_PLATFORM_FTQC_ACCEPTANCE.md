# Four-platform FTQC prediction: scientific acceptance contract

**Project objective (not an achieved result as of 2026-10-31):** Independently calibrated, held-out validated, end-to-end *predictive* models of one defined fault-tolerant logical workload on superconducting, photonic, trapped-ion and neutral-atom hardware.

## Meaning of "end-to-end" (all four families must satisfy)

A single common **logical task**, specified in operations and failure budget, must be compiled into each platform's actual supported *native fault-tolerant* code and gate primitives. The model must propagate sourced physical errors (including measured erasures/leakage/correlations), perform code-appropriate decoding and logical-gate simulation, construct a realistic non-Clifford resource path, account for controller/feedforward/routing/scheduling constraints, and report actual platform-native resource units, latency/throughput, and algorithm failure uncertainty. A parameter must be traceable to a real measurement (or **explicitly labeled extrapolated, with sensitivity analysis**). The end-to-end *hardware* prediction must be checked against a held-out experiment measuring the same corresponding supported protocol. Predictions for unavailable circuit scales remain **extrapolations**, not independently experimentally validated outcomes.

**Cross-hardware comparison:** identical logical workload and failure target, but **not** a fake equality of physical qubits, optical modes, traps, photons, lasers, control channels, or factory site equivalents. Report separate physical resource units and separately stated comparability assumptions.

## Required evidence and model links

1. **Source verification:** raw experimental records; exact provider/device, dates, protocols, code/decoder, hashes, units and measurement ordering. Automatically downloaded repository metadata is not calibration.
2. **Calibration:** fit device/protocol-specific physical/noise parameters only on training epochs; identify unmeasured parameters. Do not transfer repetition-code data to surface-code logical gate predictions.
3. **Independent holdout:** chronologically later hardware results, disjoint jobs and no fit/decoder selection from the held-out partition. Compare probabilistic predictions with failure counts and intervals, not just a fitted curve.
4. **Full FTQC stack:** meaningful error-corrected preparation, memory, entangling logical Clifford, non-Clifford resource and measurement, with validated decoding, causal controller and timing constraints.
5. **Architecture projection:** target probability, duration, physical resources/footprint, resource supply bottlenecks, factory throughput, failure-budget distribution, uncertainty intervals and sensitivity to unmeasured assumptions.
6. **Scientific status:** independent reproduction of named paper observables plus a separately defined held-out architecture or logical-circuit validation. Do not call a reproduced plot or matching nominal vendor number an independent prediction.

## Platform-specific non-interchangeable physics

| Family | Source direction | Mandatory native stack | Why current data alone are insufficient |
|---|---|---|---|
| IBM superconducting | Stein et al., Zenodo 20768087; additional surface-code logical-operation records | Actual circuits/calibration/correlated detector model, surface code, lattice surgery, distillation, physical controller | Repetition-code FiLM/MWPM dataset gives only a subset of surface-code and gate evidence |
| Xanadu photonic | Aurora figure/decoder records, GKP characterization and source-specific optical loss | Loss + squeezing/GKP noise, GKP decoder, entanglement/cluster/fusion resource supply, adaptive homodyne and logical gates | Aurora Fig 3c/3d workbook replot is **not** GKP logical Clifford+T validation |
| Quantinuum trapped ion | Helios paper data and published 2026 logical-code experiments | Native verified ion logical code, gate errors, transport/leakage/crosstalk, active QEC, Clifford+T resource chain | Aggregate physical benchmarks cannot establish logical FTQC throughput or universal-gate performance |
| Neutral atom | Bluvstein & Geim Zenodo 15685795 surface-code QEC | Loss-aware decoder, transport/zone scheduling, replenishment, logical gates, non-Clifford resource path | d3/d5 surface-code suppression is a crucial **subsystem** measurement, not end-to-end universal application validation |

## Available executable components (added to original )

- `src/ftqc_resource_estimator/full_stack_prediction.py`: strict **empirical logical-primitive composition baseline**, using disjoint chronological training and held-out trials, Wilson intervals and serial-duration accounting. It refuses partial primitive sets, protocols mixed across splits, run leakage and unsupported physical-code pooling. **This is an elementary baseline, not a full physical end-to-end FTQC model**. Use it *only* with source-authenticated and paper-matched input. It deliberately marks its outputs as conditional.
- `scripts/automation/audit_ftqc_end_to_end.py`: outputs the exact four-family missing-evidence checklist and checks artifact hashes when evidence is supplied. Its output is a progress gate, **not** a self-certifying scientific review.
- `evidence/validation/four_family_evidence.json`: initially empty. Never set `verified` without submitting hashed, reviewable evidence. Do not manufacture numbers to satisfy the gate.
- `evidence/validation/reference_workload.json`: **illustrative** common logical workload; the counts are a test specification, not data measured from a quantum computer.

Run `python3 scripts/automation/audit_ftqc_end_to_end.py` to write the audit. It deliberately exits with status 2 when requirements are missing (use `|| true` in exploratory shell scripts; do not suppress the failure in publication gates).

## Verification of a full result

A full analysis claim additionally requires independent inspection of the source-to-count extraction, operation definitions, fitting procedure, and statistical calibration; **a hash-consistent manifest is necessary but not sufficient**. No command can turn the current public source inventories into independently validated universal FTQC results on all four platforms.

### Public source references

- [IBM matched repetition-code data](https://doi.org/10.5281/zenodo.20768087)
- [Aurora source data](https://github.com/XanaduAI/xanadu-aurora-data)
- [Helios paper data](https://github.com/Quantinuum/Helios-paper-data)
- [Neutral-atom surface-code data](https://doi.org/10.5281/zenodo.15685795)
- [Quantinuum trapped-ion FT architecture experiment](https://arxiv.org/abs/2609.03194)

## Reading the 34-gate score alongside component progress

**The baseline `0/34` means zero submitted full-stack evidence dossiers in an empty manifest; it does not mean 34 failed experiments or that no components were built.** The audit checks file paths and hashes, not the underlying physical validity. Even a `34/34` file-hash result requires independent methodology review before a hardware-validation claim can be made.

See [the component-progress dashboard](PROJECT_PROGRESS.md) for explicit platform-by-platform engineering work, saved evidence, prior run outcomes, and remaining analysis components. The component inventory and gate acceptance are intentionally **different denominators**, not competing success percentages.

The four families have **separate native gate requirements** (9/8/9/8), executed by one shared audit script. A pass for one family does not transfer to another.
