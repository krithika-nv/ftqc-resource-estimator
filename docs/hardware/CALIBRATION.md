# Physical hardware calibration and quality requirements

> Current documentation is authoritative only for the specific claims supported by linked measured data, simulation outputs and tests.

## Calibration methodology

**Current verdict: conditional simulation / NOT calibrated to a named quantum processor.** Better-source metadata alone does not produce physical validation. Read [limitations L09–L17](../validation/LIMITATIONS.md), [methods](../methods/METHODS.md), and [references](../reference/REFERENCES.md).

### What calibration data are public?

| Resource | Available | What it cannot establish by itself |
|---|---|---|
| [IBM Quantum backend properties](https://quantum.cloud.ibm.com/docs/en/guides/qpu-information) [R7] | Authenticated users may inspect/download CSV with qubit `T1`, **Hahn-echo `T2`**, readout length/error, gate metrics and timestamps; Qiskit access e.g. `backend.properties` and `backend.properties(datetime=...)` | Does not expose all pulse calibration; may lack free-induction Ramsey `T2*`, correlated-error tensors or true max simultaneous syndrome readout capacity |
| [IBM benchmarking guide](https://quantum.cloud.ibm.com/docs/en/guides/calibration-jobs) [R8] | Characterization measures and their update policy | Daily benchmarks can drift; backend properties are not full machine control settings |
| [Open IBM repetition-code raw dataset](https://doi.org/10.5281/zenodo.20768087) [R9] | 352 snapshots, per-job qubit calibration, executed QASM, bitstrings, distances 3/5/7/9/11, 1–11 rounds, X/Z memory | Repetition codes instead of full rotated surface-code checks; can validate an **adapter and uncertainty treatment**, not entire surface-code predictions |
| [Kan et al. Nighthawk surface-code preprint](https://arxiv.org/abs/2610.23840) [R6] | Actual observed Nighthawk memory performance, optimized syndrome extraction, readout timing and detector-pair contrasts | Not a complete same-device public parameter matrix for our current idle-coherence model |
| [Google Willow experiment](https://doi.org/10.1038/s41586-024-08449-y) [R5] | Published mean coherence and correction-cycle values | CPMG is not Ramsey; cannot combine with Nighthawk readout and call the result calibrated |

### Acquisition and validation methodology

1. **Select exactly one processor, device version and calibration timestamp.** The IBM QPU accessible to the user can be different from Kan et al.'s Nighthawk. Keep all qubit indices and topology mapping.
2. **Export the official calibration snapshot and record raw provenance.** For IBM, an authenticated account can use the Compute resources calibration CSV or Qiskit `backend.properties` [R7–R8]. Pin units (seconds vs µs) and measured time. Do **not** store credentials in this repository.
3. **Model only reported quantities first:** T1 per qubit, readout length/error and gates. Treat reported Hahn-echo T2 as an *echoed* quantity; if a free-idle Ramsey value is missing, mark it unknown and sweep it as a parameter with explicit uncertainty instead of substituting it.
4. **Obtain a real schedule:** ancilla group readout concurrency, readout pulse/reset duration, time slots, idle placement, echo operations and decoding critical path. Instruction readout duration is **not readout-channel capacity**.
5. **Calibrate data-plane errors and temporal correlations:** matched detector history, cross-talk/spectator effects, leakage and time drift. Use a distinct held-out subset for prediction testing.
6. **Use a data benchmark before a full QPU model:** [R9] provides real per-job calibrations and raw repetition-code shots. Develop an explicitly labeled *repetition-code validation adapter* if pursuing this, rather than repurposing its error curves as surface-code observations.
7. **Predict out of sample:** pre-register metrics (logical failure per memory round, detector signatures, confidence/uncertainty, scheduling footprint), run the simulator without fitting to the test shots, and quantify disagreement with measured data.
8. **Only then claim hardware-calibrated performance for that one configuration.** Claims beyond the measured qubit placement, pulse schedule or timestamp require additional validation.

### Input schema and status check

`examples/device_calibration_template.json` is deliberately incomplete. Run:

```zsh
PYTHONPATH=src python3 -m ftqc_resource_estimator.device_calibration   --input examples/device_calibration_template.json
```

The metadata checker is a **fail-closed completeness screen** only. Even a file with all fields populated cannot itself establish physical calibration; experimental cross-checks are required. Do not edit calibration inputs to pass the gate without the underlying measurements.

### Next science milestone

A relevant independent validation route is to **extend the repetition-code calibration adapter using Zenodo [R9]**, showing the effect of qubit-specific error rates and readout timing on held-out measured code outcomes. Then attempt **surface-code** prediction using a same-device matched circuit and independent public surface-code results, recognizing missing `T2*` and correlation data may cap achievable fidelity. The baseline FTQC resource estimator must not silently import repetition-code logical error as a surface-code logical gate error.

### Implemented first step: Qiskit historical calibration ingestion

The project now imports actual *past IBM hardware characterization* from the source-linked Qiskit IBM Manila snapshot [R11] using `public_calibration.py`. It validates per-qubit T1, Hahn-echo T2, readout assignment asymmetry, readout length, CX gate errors and a five-site coupling path; outputs under `outputs/public_calibration/` are generated without calling a QPU. Source class: **historical measured input**; derived Stim knobs: **approximate conditional model**, not experimentally calibrated physical prediction. A five-qubit chip cannot support the rotated surface-code architecture under discussion. The full original JSON fetch and same-device experimental QEC comparison remain outstanding. [Runbook](CALIBRATION.md) · [L22–L26](../validation/LIMITATIONS.md).


**2026 source priority:** see [FRESH_2026_CALIBRATIONS.md](CALIBRATION.md). IBM Manila May 2024 is a historical test input; do not use as headline data for current quantum hardware. The newest eligible input is a source-verified, *individually dated* calibration for a currently accessible IBM processor.


### Per-platform calibration and claim firewall

IBM sourced calibration may only support a **superconducting** device-specific characterization or conditional proxy; it is not transferable to photonic state/loss or trapped-ion transport calibration. The normalization/importer emits explicit family and validation-status metadata, and `platform_boundaries.py` rejects incompatible evidence-use requests. [See boundary contract](../methods/PLATFORM_BOUNDARIES.md) and [limitation register](../validation/LIMITATIONS.md). For a physically matched validation, independently gather each platform's fault channels, execution schedule, qubit/state placement, calibration timestamps and same-protocol QEC outcomes; **none are supplied for photonic or ion devices here**. IBM data do not automatically calibrate the generic surface-code reference [R7–R9].

## Recent calibration source protocol

**As of October 28, 2026.** Distinguish the **date a dataset was published**, the **timestamp when each device was calibrated**, and the **time at which you downloaded it**. Only the second describes the age of the hardware characterization.

### Goal

Replace the 2024 IBM Manila snapshot as the **primary hardware evidence** in this project. Keep Manila as a historical regression fixture. Import actual dated device calibrations with explicit hashes, device name, time, units and missing-data flags. **No synthetic fallback** is allowed in this pipeline. The importer does not yet validate logical error predictions against hardware shots.

### A. Preferred reproducible public dataset (2026)

Samuel Stein et al., *Calibration-Conditioned FiLM Decoders for Low-Latency Decoding of Quantum Error Correction Evaluated on IBM Repetition-Code Experiments*. Dataset published 2026, DOI [10.5281/zenodo.20768087](https://doi.org/10.5281/zenodo.20768087); manuscript [arXiv:2601.16123](https://arxiv.org/abs/2601.16123). This is **repetition-code** experiment data, **not** a measured surface-code dataset.

The Zenodo dataset [R9](../reference/REFERENCES.md) publicly describes 352 calibration-linked hardware snapshots spanning three IBM devices, codes d=3..11, X/Z basis and syndrome rounds up to 11. Each snapshot pairs `calibration.json` with `info.json`, actual QASM circuits and raw bitstrings. The 2026 dataset release date does **not** establish that every calibration was performed in 2026; inspect the actual timestamp before describing it as current.

The repository's new importer is **tested with synthetic schema fixtures**, but the complete original Zenodo archive could not be downloaded in this execution environment. Thus none of the 352 snapshots is claimed to have been imported here.

#### Run on your Mac (Zsh, Python 3.14)

```zsh
# Download IBM Fez archive (9 MB); verify the Zenodo-published MD5 automatically.
python3 scripts/tools/download_2026_qec_calibration.py --backend ibm_fez

# Parse snapshots with real qubit T1, T2, readout and gate errors, checking dates.
./scripts/commands/RUN_MODERN_CALIBRATION.sh --backend ibm_fez \
  --zenodo-archive data/public_calibrations/2026/ibm_fez.tar.gz \
  --max-age-days 365 --output-dir outputs/modern_calibration/ibm_fez

cat outputs/modern_calibration/ibm_fez/IMPORT_REPORT.md
cat outputs/modern_calibration/ibm_fez/provenance.json
```

**Mixed-age archives (important):** The importer now checks every dated calibration in the archive, skips records older than `--max-age-days`, then selects the newest eligible records first. The report/provenance records the number excluded. If *all* actual calibrations are older than the cutoff, it fails with the newest measured timestamp. A 2026 dataset release is not evidence of 2026 calibration. For genuine current-hardware characterization, use an authenticated IBM backend snapshot. Never increase `--max-age-days` merely to label historical measurements as current.

**If parsing fails:** preserve the error and inspect a real `calibration.json`. Do not loosen the schema or infer unknown values without checking the published original. To avoid importing 41 snapshots at once during development, add `--max-snapshots 1`. The test suite uses clearly labeled synthetic fixtures; passing tests is not proof that the upstream dataset's current schema has been exercised.

**Other datasets:** change backend to `ibm_kingston` (~71 MB) or `ibm_pittsburgh` (~65 MB). The full data archives should stay in ignored `data/public_calibrations/`.

### B. Newest authenticated IBM Quantum data (preferred for operational recency)

IBM Quantum periodically publishes backend characterization/benchmark properties to eligible account holders [R7–R8](../reference/REFERENCES.md). These are **current relative to the calibration timestamp**, not necessarily to the instant of export. Users authenticate **locally** and must not commit tokens or credentials. See [IBM's backend documentation](https://quantum.cloud.ibm.com/docs/en/guides/qpu-information).

```zsh
# Only if qiskit-ibm-runtime is already available with a configured account:
python3 scripts/tools/export_live_ibm_calibration.py --backend ibm_fez \
  --output data/public_calibrations/live_properties.json

./scripts/commands/RUN_MODERN_CALIBRATION.sh --backend ibm_fez \
  --ibm-properties data/public_calibrations/live_properties.json \
  --max-age-days 14 --output-dir outputs/modern_calibration/live_ibm_fez
```

Change `ibm_fez` to a **device you can actually access**. If `qiskit-ibm-runtime` is missing, IBM's compute-resources UI can export calibration CSV; however, that CSV is a **different schema** and this JSON importer does not claim to parse it. The script will fail explicitly rather than pretending to ingest the CSV.

### What is, and isn't, independently checked

* **Checked in code:** source checksums, syntactic/device timestamp validity, recency cutoff, per-qubit T1/T2/assignment probability, units, backend identity, and presence of paired experiment metadata for archived snapshots.
* **Not yet done:** import/decoding of paired raw QEC shots; predictive comparison with held-out experiments; pulse-level calibration, measured controller concurrency, free-idle Ramsey T2*, or multi-qubit correlated errors.
* **Calibration is not a validation result:** a low physical readout-error number does not establish a low logical failure rate. Claims about logical prediction require matched executed circuits, noise schedule, decoder and experimental bitstrings.

#### Provenance/attribution

The publicly released dataset and raw hardware measurements belong to their authors and IBM. Import code is project-specific; no claim of inventing QEC algorithms is made. Always cite the original dataset and specific snapshot timestamp, not just its release year.

## Historical public-calibration imports

**Status:** implemented and offline-executed on a source-linked, *measured-value transcription*. It is not a hardware benchmark, an original IBM full-file checksum, or a validated QPU noise model.

### Data and attribution

- Primary: Qiskit/IBM Quantum [`props_manila.json`](https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/fake_provider/backends/manila/props_manila.json), backend `ibmq_manila`, snapshot **2024-05-27T15:27:23-03:00** [R11].
- Qiskit [Fake Provider docs](https://qiskit.github.io/qiskit-ibm-runtime/apidocs/fake_provider.html) explain that the backend emulator uses historical *real* processor characterization data; the *emulator* is artificial, the archived T1/T2/errors came from real device characterization [R12].
- `examples/public_ibmq_manila_2024_subset.json` contains **selected manually transcribed original values** with backend, date and original URL; it is **not a verbatim copy or integrity-verified entire source file**. Preserve attribution when redistributing this subset.
- We did not access the physical processor or measure its logical failure probability.

### Quick commands - Zsh, no new environment

```zsh
# Offline, using selected published measured fields already in the repo
./scripts/commands/RUN_PUBLIC_CALIBRATION.sh
cat outputs/public_calibration/CALIBRATION_IMPORT_REPORT.md
python3 scripts/tools/plot_public_calibration.py  # optional figure; needs matplotlib

# On a networked Mac: download the *complete, original* source file and parse it
./scripts/commands/download_manila_calibration.sh
cat outputs/public_calibration_from_raw/provenance.json

# Optional: run a genuine Stim/PyMatching SOFTWARE simulation of a d3
# repetition-code noise PROXY (not a prediction of actual device hardware)
./scripts/commands/RUN_PUBLIC_CALIBRATION.sh --simulate
```

### Files

- `src/ftqc_resource_estimator/public_calibration.py`: strict schema parsing and validation; handles curated JSON and official raw Qiskit `props_*.json`. Ensures timestamps, units, assignment-error arithmetic, directed edge topology and physical probability ranges.
- `examples/public_ibmq_manila_2024_subset.json`: measured values *selected* from the archived 2024 IBM source.
- `scripts/commands/RUN_PUBLIC_CALIBRATION.sh`: offline measured-input import and projection.
- `scripts/commands/download_manila_calibration.sh`: uses `curl` to fetch original raw source; fails on HTTP errors or mismatched dated backend metadata; writes independent SHA256 of downloaded bytes.
- `outputs/public_calibration/normalized_calibration.json`: measured per-qubit and directed CX values.
- `outputs/public_calibration/calibration_projection.json`: modeled parameters and all limitations; **not new measurements**.
- `outputs/public_calibration/provenance.json`: SHA256 of the **ingested file**; the bundled subset hash must not be called upstream full-original checksum.
- `outputs/public_calibration/CALIBRATION_IMPORT_REPORT.md` and CSVs: overview of data heterogeneity, missing fields and remaining validation.
- `tests/test_public_calibration.py`: parser tests for units, errors, topology, provenance and scientific scope.

### Mapping to simulated circuit - why still not calibrated

The selected IBM file measures **T1** and **Hahn-echo T2**, not free-idle Ramsey T2*. Accordingly our T1-only relaxation twirl approximates `pX=pY=(1-exp(-t/T1))/4`, where `t` is taken from actual *readout instruction duration* but its application as an idle window is an explicit modeling choice. The qubit-wise values are then compressed into a phenomenological five-site repetition-memory demonstration. Measured directed CX infidelities are not automatically equivalent to Stim's global `after_clifford_depolarization` probability; readout assignment probabilities are asymmetric but compressed to a median knob. Zero reset-flip is a missing/unsupported experimental input, **not** a calibrated zero-reset-error finding.

The five-site historical Manila topology is compatible only with a *toy* d3 repetition-code demonstration here; a rotated-surface-code memory (d3) requires more physical sites and different connectivity. There is no matched historical hardware QEC shot record in this repository. **Do not compare our conditional simulator output to actual Nighthawk/Willow logical error rates as if calibrated.**

### What remains for predictive validation

1. Download/verify upstream full JSON (same source version, date and qubit count).
2. Obtain matched **same-device / same-time** repetition-code hardware bitstrings and exact compiled circuits.
3. Run a pre-specified held-out comparison with confidence intervals, report residuals, and test against stronger baselines.
4. Obtain Ramsey/free-induction dephasing and actual readout concurrency if making idle-control predictions; never infer them from Hahn-echo T2 or instruction duration.

Sources: [R11–R12](../reference/REFERENCES.md), [R9](../reference/REFERENCES.md) (another-processor dataset, **not** a Manila-matched replacement). Limits: [L22–L26](../validation/LIMITATIONS.md).

## Calibration limitations checklist

**Not calibrated.** Do not substitute echo/CPMG coherence for measured Ramsey free-idle `T2*`, infer concurrent readout capacity from instruction duration, or merge Willow coherence with IBM Nighthawk readout values into a fictitious device. The implementation's schema checker **checks metadata completeness only**; it is not hardware-validation proof.

Read the authoritative [public-data and calibration plan](CALIBRATION.md), [limitations register](../validation/LIMITATIONS.md), [references R5–R9](../reference/REFERENCES.md), and `examples/device_calibration_template.json`. Refer to current calibration requirements and evidence records for the supported scope.
