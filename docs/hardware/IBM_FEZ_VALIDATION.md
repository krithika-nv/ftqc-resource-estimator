# IBM Fez decoding and matched evidence

> Current documentation is authoritative only for the specific claims supported by linked measured data, simulation outputs and tests.

## Raw-shot decoder

**Status:** decoder implementation and fixture tests complete; **not** yet end-to-end tested against the original 9 MB Zenodo archive in the model environment. Need local source-schema confirmation before making a published performance claim.

Dataset: Stein et al., *Calibration-Conditioned FiLM Decoders...* doi:10.5281/zenodo.20768087. IBM Fez archive (`ibm_fez.tar.gz`) contains jobs, circuit QASM, prepared states, calibration and raw shot registers. We **do not** reproduce the paper's FiLM network or its calibration-weighted MWPM. We provide a decoder control using phenomenological error priors specified on the CLI.

### Three local commands (Homebrew Python, no new environment)

From `ftqc-resource-estimator/`:

```zsh
# Only if the source archive isn't already at data/public_calibrations/2026/ibm_fez.tar.gz:
python3 scripts/tools/download_2026_qec_calibration.py --backend ibm_fez

# One run: inventory -> schema -> QASM checks + MWPM -> decoded CSV -> holdout statistics
python3 scripts/automation/run_pipeline.py --profile ibm

# Create the *single* small ZIP to send back for review
python3 scripts/automation/package_ibm_review.py
```

Send `outputs/IBM_REVIEW_BUNDLE.zip`. If the parser fails, include the unmodified `data/public_calibrations/2026/ibm_fez.tar.gz` (around 9 MB, publicly released) or one complete anonymized job with QASM, `info.json`, `bitstrings.json`, calibration from the same path. Never manually create the decoded CSV.

### What is checked

- Zenodo-published archive MD5, including a recheck before decoding
- Matching info/calibration/QASM/bitstrings for each job
- Explicit paired `c_data_*`/`c_syndrome_*` QASM register declarations
- Register widths `d` and `(d-1)*r`, exactly one assignment per classical bit
- Syndrome measurements in time-major order, final data measurements after syndrome rounds
- Only explicit per-shot `0`/`1` bit lists (packed strings rejected until their bit order is proven)
- Each chain's two prepared logical states, number of shots, measured failure and uncertainty
- Chronological **evaluation grouping** in existing external validation analysis

### Explicit scientific limitations

**This is a phenomenological MWPM baseline, not author-equivalent calibrated MWPM.** Unless independently verified using the original author preprocessing, register-to-chain ordering, source bit-array endianness, and syndrome time-order assumptions remain provisional. The software fails closed on inconsistencies it can detect, but passing the structural tests alone does not prove source semantic equivalence.

The optional majority-vote decoder offers a second control that does not use syndrome. No platform-specific circuit-derived noise model is fitted here; the default 0.01 data-error and 0.02 syndrome-measurement priors are stated *assumptions*, not measured physical rates. Held-out logical-error estimates assess this decoder on held-out records, **not** a calibrated predictive model. A repetition-code study cannot directly validate a surface-code logical layer or full FTQC architecture.

#### Manual troubleshooting (only if needed)

```zsh
python3 -m external_validation.ibm_raw --schema-only
python3 -m external_validation.ibm_raw --decoder majority --max-jobs 2
```

For debugging, check `outputs/external_validation/IBM_SOURCE_SCHEMA.json` and the relevant `logs/runs/<id>/03_ibm_raw_decode.log` (exact number may vary). The schema preview deliberately records field names and shapes without exporting raw shots.

## Matched calibration and QEC evidence

**evidence status (30 October 2026): infrastructure implemented and fixture-tested; no IBM Fez archive or derived experimental logical-error comparison has been executed in this environment.**

### Analysis objective

Can a circuit/protocol-specific, independently specified QEC noise model predict held-out **repetition-code** failure frequencies observed on the *same* IBM superconducting processor at a documented calibration epoch? This is a narrower benchmark than predicting fault-tolerant **surface-code architectures**, logical gates, or a photonic machine.

### Source and evidence categories

- **Raw experimental evidence:** Samuel Stein (2026), [Zenodo 20768087](https://doi.org/10.5281/zenodo.20768087), containing IBM Fez, Kingston and Pittsburgh repetition-code jobs. Each job is documented as holding `info.json`, `calibration.json`, executed state-0/state-1 QASM, and raw `bitstrings.json`. The archive's publication date is not a measurement date. See [reference R9](../reference/REFERENCES.md).
- **Live IBM characterization:** [official backend guide](https://quantum.cloud.ibm.com/docs/en/guides/qpu-information), which documents T1, Hahn-echo T2, benchmarked gate/readout errors, durations and timestamps. It does not expose every physical control calibration or raw QEC shot needed for a matched outcome. See R7/R8.
- **Simulator:** Stim/PyMatching in this repository generates **surface-code memory** evidence under specified synthetic circuit noise. That is **not** the same code family or executed protocol as the archived hardware **repetition code**. The two numbers must never be directly compared as a calibrated prediction.

### Implemented workflow

1. Download `ibm_fez.tar.gz` from Zenodo and verify MD5 `27ce2827dde0713a436179121bfd7173` before using it. This source checksum is for archive integrity, not proof of experimental fidelity.
2. Read the archive with `scripts/commands/RUN_MATCHED_HARDWARE_EVIDENCE.sh`, which **does not extract its files to the repository**. It checks presence and parses metadata for all matched jobs, records SHA-256 values for calibration, info, shot records and both executed QASM files; validates qubit and protocol fields and timestamps; flags stale records separately rather than mislabelling the 2026-published archive as current.
3. Generate `MATCHED_EVIDENCE_INVENTORY.csv`, `EVIDENCE_MANIFEST.json`, and `EVIDENCE_REPORT.md`. This is paired **raw evidence indexing**; no decoder or hardware prediction is performed.
4. Split by calibration timestamp rather than random shots (a *proposed* temporal split; confirm actual submission/execution times). The output explicitly refuses a holdout claim when there are fewer than two distinct epochs.
5. Once independent **repetition-code** decoding and matched circuit-level predictions have been implemented/verified, prepare a CSV with exact snapshot ID, backend, code family, code distance, rounds, logical basis, calibration SHA, raw-shot SHA, held-out membership and separately hashed simulator source.
6. Run `python3 -m ftqc_resource_estimator.hardware_prediction_comparison --predictions ... --evidence-inventory ... --output-dir ...`. The audit rejects mismatched protocol, timestamps through the split, code family, provenance and unsigned predictions. It computes **descriptive** absolute prediction errors, biases, and marginal Wilson intervals on the supplied hardware counts. It **does not generate those counts or predictions**.

### Run on Mac (Zsh, Python 3.14; from repository root)

```zsh
md5 -q data/public_calibrations/2026/ibm_fez.tar.gz
# Expected: 27ce2827dde0713a436179121bfd7173

./scripts/commands/RUN_MATCHED_HARDWARE_EVIDENCE.sh \
  --archive data/public_calibrations/2026/ibm_fez.tar.gz \
  --backend ibm_fez --max-age-days 365 \
  --output-dir outputs/matched_hardware_evidence/ibm_fez

cat outputs/matched_hardware_evidence/ibm_fez/EVIDENCE_REPORT.md

# Existing, separate simulator experiments, not a matched IBM QEC prediction:
./scripts/commands/RUN_LITERATURE_BENCHMARK.sh
./scripts/commands/RUN_IDLE_COHERENCE_STUDY.sh
```

If a full archive has no calibrations within 365 days, the inventory will **still show the historical evidence**, with its actual timestamp and a count of stale snapshots; it will not describe them as a current calibration. The existing modern-calibration *current data* import properly rejects records over the configured cutoff. Do not raise the cutoff solely to obtain a successful “current” import.

### Required future experiment to make hardware prediction claims

- Decode real repetition-code bitstrings with explicit `c_data_*` / `c_syndrome_*` register mapping and documented state/shot order; verify against paper/author decoding conventions and include reference baselines.
- Reproduce executed QASM logically and temporally, including data and ancilla selection, gate directions and gates, reset/readout, noise timing and correlation assumptions. **Do not reuse the synthetic rotated surface-code simulations as a repetition-code result.**
- Construct a noise model using only data from the associated hardware calibration epoch, with missing Ramsey T2*, leakage, crosstalk, and correlated errors separately treated as unmeasured nuisance parameters. Avoid calibration on held-out outcomes.
- Generate independent predictions for a chronological holdout set and report signed residuals, uncertainty intervals, sensitivity to missing parameters, per-device/per-distance/per-basis stratification and failures as well as successes.
- Repeat with a second independent same-device dataset if available before making a strong device-generalization claim.

**Not completed:** raw bitstring decoding, faithful executed-QASM-to-Stim mapping, held-out hardware prediction and device-specific predictive accuracy. Existing matched-evidence code is an essential input gate, not any of these outcomes.
