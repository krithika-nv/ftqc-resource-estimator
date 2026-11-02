# Analysis methods and executable map

**Status:** numerical analysis prototype, not complete FTQC architecture simulator. For model validity, read [LIMITATIONS.md](../validation/LIMITATIONS.md). Sources are keyed to [REFERENCES.md](../reference/REFERENCES.md).

## 1. Reliability-constrained decision

For `N = logical_patches × memory_windows = 4 × 10 = 40` hypothetically independent memory events and total failure target `P_target=0.10`, the per-event error budget is `1 - (1 - P_target)^(1/N) ≈ 0.0026305469`. A *conservative model-feasibility* decision compares the **upper endpoint** of a marginal two-sided 95% Wilson interval of simulated decoded memory failures against that budget. This propagation assumes identical, independent windows and **is not a simultaneous confidence guarantee**. The interval is Wilson’s score method [R13]; the surface-code protocol is cited in [R1, R4]. [L01–L03](../validation/LIMITATIONS.md).

The older abstract architecture calculator separately uses `p_L = A (p/p_th)^((d+1)/2)` as an *unfitted illustrative heuristic*, not an observed physical surface-code error rate. Do not substitute the memory experiment for its logical-gate assumptions. See `src/ftqc_resource_estimator/model.py`, `reliability.py` and `architecture.py` [L04–L06](../validation/LIMITATIONS.md).

## 2. Study matrix - implementations and outputs

| Entry point | Modules / configuration | Output | Scientific scope |
|---|---|---|---|
| `scripts/commands/RUN_ARCHITECTURE_STUDY.sh` | `study.py`; `examples/architecture_scenarios.json`; repetition/queue scripts | `outputs/architecture_study/`, sanity CSVs | Mathematical/heuristic and finite-queue sanity checks |
| `scripts/commands/RUN_HARDWARE_STUDY.sh` | `hardware_study.py`, `hardware_profiles.py`; `examples/hardware_profiles.json` | `outputs/hardware_profiles/` | Separately assumed optical, superconducting, ion schedules; **no cross-platform ranking** |
| `scripts/commands/RUN_STIM_MEMORY.sh` | `stim_memory.py`, `memory_analysis.py`; noise `p=0,.003,.005`, `d=3,5,7`, **9 fixed rounds**, X basis, 20k each | `outputs/stim_memory/` | **180k** real simulated shots owner executed; generated rotated surface-code circuits [R2–R4] |
| `scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh` | same modules + `memory_control_cost_sensitivity.json`; `p=.003`, `d=7,9`, **9 fixed rounds**, 20k each | `outputs/stim_memory/followup/` | **40k** owner-executed shots; new replay certificate pending regeneration |
| `scripts/commands/RUN_LITERATURE_BENCHMARK.sh` | `literature_benchmark.py`; `d=3,5,7,9`, `rounds=d`, p=0/.003/.005/.007/.009 | `outputs/literature_benchmark/` | **400,000 simulator shots executed and replay-verified in the October 31 local run logs**; protocol-aligned subset of Riverlane [R4], not a published numerical-figure reproduction |
| `scripts/commands/RUN_CONTROLLER_CAPACITY.sh` | `controller_capacity.py`; `examples/controller_capacity_hypotheses.json` | `outputs/controller_capacity/` | Separate abstract patch qubits, readout channels, timing and power; **all controller coefficients hypothetical** |
| `scripts/commands/RUN_IDLE_COHERENCE_STUDY.sh --preview-only` | `idle_coherence.py`; `examples/idle_coherence_study.json` | `outputs/idle_coherence/inputs_only/` | Additional **assumed physical Pauli-channel input**, not a logical error estimate |
| `scripts/commands/RUN_IDLE_COHERENCE_STUDY.sh` | same; `d=3,5,7,9`, `rounds=d`, 3 controllers × 20k shots | `outputs/idle_coherence/` | **240,000 simulator shots executed and replay-verified in the October 31 local run logs** [R5]; hardware controller parameters remain hypothetical |
| `scripts/commands/RUN_PUBLISHED_READOUT_AUDIT.sh` | `published_readout_evidence.py`; fixed source record | `outputs/published_readout/` | **Secondary calculations** on rounded Nighthawk preprint values [R6] |
| `python3 -m ftqc_resource_estimator.device_calibration --input ...` | `device_calibration.py`; `examples/device_calibration_template.json` | missing-fields report | **No device-calibrated prediction** is certified |

All external simulations must be replayed against recorded seeds, counts and circuit hashes. `scripts/commands/RUN_ALL_VALIDATIONS.sh` runs the full set; `scripts/tools/prepare_results.py --mode full` additionally requires saved real-backend certificates. Missing evidence is an error, not a signal to fabricate output.

## 3. Literature comparison method

Riverlane's online tutorial [R4] explicitly sets `rounds=distance` with `stim.Circuit.generated('surface_code:rotated_memory_x')`, a four-knob depolarizing/reset/measurement noise model, and PyMatching on a detector error model. Our `literature_benchmark.py` is a **smaller protocol-aligned replication**, not a pixel-accurate replication of every published data point. Exact results require matching full parameter grid, decoder, seed policy, shots, uncertainty and version details; those are not asserted here.

## 4. Controller-idle channel method

A Willow-inspired *input scenario* [R5] uses mean `T1 = 68 µs`, `T2_CPMG = 89 µs`, cycle duration 1.1 µs (published measurements), **plus separately hypothetical** 32/128/256 concurrent readout channels, 0.45 µs batch duration and 0.35 W per channel. For added stipulated delay `Δt`, `u=exp(-Δt/T1)` and `v=exp(-Δt/T2_proxy)`. The Pauli-twirled event weights are `p_X=p_Y=(1-u)/4`, `p_Z=(1+u-2v)/4`. This drops the non-unital part of amplitude damping; using CPMG as free-induction `T2*` is **not calibrated**. Each modified Stim circuit must regenerate the decoder error graph. [L09–L13](../validation/LIMITATIONS.md).

**Do not interpret the Nighthawk 1.14/1.94 µs observed readout instructions [R6] as an actual 0.45-µs Willow readout slot, or infer controller channel concurrency from instruction duration.** Read [PHYSICAL_CALIBRATION.md](../hardware/CALIBRATION.md).

## 5. Statistical and comparison policy

- Use explicit independent Bernoulli shot counts and Wilson score intervals [R13]; zero failures do not imply zero underlying failure.
- Never compare the nine-round and distance-scaled protocols as matched wall-time experiments.
- Never use one memory noise observation as proof of an arbitrary logical-gate failure probability.
- Record configurations and source/decoder versions; separate run outcomes from literature quotations and assumptions.
- Numerical repeatability of code is **not** physical validation. [R1–R9, R13; LIMITATIONS](../validation/LIMITATIONS.md).

## 6. Importing measured public IBM properties (new)

`public_calibration.py` takes IBM's archived May 2024 **Manila backend-properties snapshot** [R11], validates units, qubit indices, directed CX pairs, per-qubit readout assignment arithmetic and chronology, and writes transparent normalized JSON/CSV with a source SHA256. The bundled curated input is a **selected transcription**; for a complete original, run `scripts/commands/download_manila_calibration.sh` on a networked machine. A missing raw file is not silently replaced by fabricated data.

For a measured readout duration `t_readout` and measured T1 per qubit, it projects **relaxation-only** twirled event probabilities `p_X=p_Y=(1-exp(-t_readout/T1))/4`; the wait duration's placement is a model assumption. Crucially it **does not** replace unknown unprotected Ramsey T2* with backend Hahn-echo T2. Gate error and readout assignment measurements become *median phenomenological* circuit-noise parameters and are not claimed to represent a pulse-level IBM calibration. The optional Stim/PyMatching runnable model generates only a **d=3 repetition-code** memory proxy using 5 physical sites. This is neither a rotated-surface-code QPU forecast nor an out-of-sample calibration validation. [Import runbook](../hardware/CALIBRATION.md), [L22–L26](../validation/LIMITATIONS.md), [R11–R12](../reference/REFERENCES.md).

## 7. Modern 2026 calibration-source importer ( no full archive imported here)

`scripts/tools/download_2026_qec_calibration.py`, `scripts/commands/RUN_MODERN_CALIBRATION.sh` and `modern_calibration.py` implement source-checksum verification, per-snapshot normalization, backend/timestamp requirements and fail-closed rejection of incompatible records. The source is Stein’s **repetition-code** dataset [R9], not Nighthawk or a rotated-surface-code validation dataset. On an internet-enabled Mac the real archive must be downloaded, parsed, and the resulting report inspected before claiming real 2026 data ingestion. The authenticated path uses IBM backend properties [R7–R8], not an open anonymized dataset. The historical Manila adapter remains a separate regression test [R11–R12].


## Portability boundary ( explicit analysis-contract extension)

The *decision logic* (Wilson screening bounds [R13], experiment identity, reliability targets and non-dominance) is portable, while the physical meaning of a resource and a noise channel is not. `hardware_profiles.py` defines deliberately separate platform-specific native-unit scenarios; `modern_calibration.py` imports measured IBM **superconducting** characterization, and `platform_boundaries.py` rejects attempts to represent it as photonic, trapped-ion or validated logical-QEC calibration. See [PLATFORM_BOUNDARIES.md](PLATFORM_BOUNDARIES.md). Source data are attributed to IBM and the 2026 Zenodo release [R7–R9]. **The core abstract estimator does not consume these calibrations automatically.**
