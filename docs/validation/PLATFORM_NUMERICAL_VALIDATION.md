# Platform-specific numerical validation

## Scientific contract

The central estimator remains a cross-platform **decision methodology**, not a universal physical noise model. This module suite provides four executable and separately scoped numerical pipelines. **All published raw datasets are external.** The numerical analyses have controlled fixture tests. Source-backed IBM, Aurora and Helios partial results are described in [evidence and results](EVIDENCE_AND_RESULTS.md). These limited reproductions do **not** certify universal FTQC architecture predictions or the original author-level fitted statistics for all platforms.

The assays are useful and fully executable, but they are not equivalent to a validated FTQC model. Source-specific data transformation and protocol verification are required before interpreting their outputs as measured hardware science. Never relabel a fixture result as measured experimental evidence.

## 1. Superconducting - IBM 2026 paired repetition-code experiment

**Primary source:** Samuel Stein et al.'s experimental data [R9](../reference/REFERENCES.md), [Zenodo 20768087](https://doi.org/10.5281/zenodo.20768087); the [source description](https://github.com/Samuelstein1224/calibration-conditioned-decoding/blob/main/experiment_data/README.md) documents `info.json`, `calibration.json`, `bitstrings.json`, and executed `circuit_state*.qasm`. The raw bitstrings contain per-chain `c_data_*`/`c_syndrome_*` measurement registers. They are not simply the final data bits.

**Evidence pipeline:** `scripts/commands/RUN_MATCHED_HARDWARE_EVIDENCE.sh` checks that calibration, executed QASM and raw shots are paired. The new `ibm_hardware_analysis.py` uses source-verified **normalized final-data bitstrings** with snapshot IDs, independent source SHA-256 hashes, dated calibration, logical state, and readout probability. It computes observed final-bit majority error, Wilson intervals and an independently derived readout-only Bernoulli null prediction:

\[P_{\mathrm{majority},d}(p)=\sum_{k=(d+1)/2}^{d}\binom{d}{k}p^k(1-p)^{d-k}.\]

**Why this is not the requested full hardware prediction:** this is **final-data-bit majority**, NOT a syndrome-history decoder. The null predictor neglects data, gate, preparation and correlated errors. The raw Zenodo file must be inspected and its register mapping and timing independently verified before producing a real normalized CSV; never infer bit order from file naming. The timestamp grouping is a held-out **calibration-epoch** partition, not independently verified prospective execution-time prediction. The IBM source data are repetition codes, so they cannot validate surface-code architecture.

Example after you independently verify and export data:

```zsh
./scripts/commands/RUN_MATCHED_HARDWARE_EVIDENCE.sh --archive data/public_calibrations/2026/ibm_fez.tar.gz --backend ibm_fez --max-age-days 365 --output-dir outputs/matched_hardware_evidence/ibm_fez
./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh ibm --verified-flat-csv data/external_hardware/ibm_fez_verified_final_data.csv --backend ibm_fez --output-dir outputs/platform_numeric/ibm
```

**Required CSV columns:** `snapshot_id,backend,calibration_utc,calibration_sha256,executed_qasm_sha256,bitstrings_sha256,code_family,distance,logical_state,final_data_bitstring,count,readout_flip_probability`. Each record is the **count** of that terminal data bitstring for a known logical input state. Verify the mapped physical-qubit readout probability in *the same calibration*, including whether readout is asymmetric; a uniform `readout_flip_probability` is a baseline proxy. All three hashes must be real 64-character SHA-256 values.

**Completion gate:** independently decode raw syndrome history, reconstruct the executed QASM, match per-qubit temporal calibration, validate against held-out hardware observations (including error bars), and document any unidentifiable noise. The new code does **not** claim these steps were completed.

## 2. Photonic - Xanadu Aurora and GKP

**Sources:** [Aurora dataset](https://github.com/XanaduAI/xanadu-aurora-data) and [Nature 2025 paper](https://www.nature.com/articles/s41586-024-08406-9) [R14]; [GKP dataset](https://github.com/XanaduAI/xanadu-gkp-data) [R15].

The new `xanadu_analysis.py` supports two distinct calculations:

**Aurora publication workbook:** read an explicitly named worksheet and its exact numeric x/y columns from the *original* publication `.xlsx`. This produces a hashed source-point table suitable for independent figure digitization and later comparison. It does **not** assume that every sheet is a specific paper figure or calculate an undocumented optical metric.

```zsh
./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh xanadu-aurora \
  --workbook data/external_hardware/xanadu_aurora/PUBLICATION_PLOT.xlsx \
  --sheet 'EXACT_SHEET_NAME' --x-column 'EXACT_X_HEADER' --y-column 'EXACT_Y_HEADER' \
  --unit 'EXACT_REPORTED_UNIT' --output-dir outputs/platform_numeric/aurora
```

Inspect the downloaded workbook and replace these explicitly marked sheet/header placeholders with its true metadata. No assumptions about units or figures are made.

**GKP reconstructed-state calculation:** given a **numeric square density matrix in `.npy` format** from a trusted export of the published reconstruction, validate Hermiticity, trace, positivity and compute purity `Tr(rho²)`, mean photon number at the chosen Fock cutoff, and parity-convention origin Wigner value `W(0)=2/pi Tr(rho (-1)^n)`.

```zsh
./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh xanadu-gkp \
  --density-npy data/external_hardware/xanadu_gkp/verified_numeric_density_matrix.npy \
  --output-dir outputs/platform_numeric/gkp
```

The upstream `analysis_results.npy` might be a **structured/object dictionary** rather than a single numeric density matrix. This program **will not unpickle it**. A source-reviewed export of one PNR-conditioned reconstructed matrix is necessary. Further comparison with specific published states/figures requires matching the PNR outcome, normalization, Fock cutoff and reconstruction method. We do not invent such a match.

## 3. Trapped ion - Quantinuum

**Sources:** [Helios paper data](https://github.com/Quantinuum/Helios-paper-data) [R16], and [official performance-validation guidance](https://docs.quantinuum.com/systems/user_guide/hardware_user_guide/performance_validation.html) [R16]. Hardware data and product specifications are different evidence types.

`quantinuum_analysis.py` groups **source-verified, measured trial counts** and computes success rates and Wilson 95% intervals without loading untrusted Python pickle objects. Use independent trusted source conversion for opaque `.p` data; a file name or specification table cannot be silently interpreted as measured shots. **Do not represent hardware specification max thresholds as binomial counts.**

```zsh
./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh quantinuum \
  --trusted-csv data/external_hardware/quantinuum_helios/verified_hardware_counts.csv \
  --output-dir outputs/platform_numeric/helios
```

**Required CSV headers:** `source_id,processor,experiment,successes,shots,data_kind,provider`. `provider=Quantinuum`; `data_kind=executed_hardware_shots`. Keep a separate provenance worksheet mapping each row to the published table, paper figure, original experimental file, exact processing and control conditions. Wilson intervals apply to trial counts with a binomial interpretation; correlated samples need different uncertainty treatment. Without a numeric verified export, this module does not reproduce a published Helios figure.

## 4. Neutral atom - QuEra Aquila

**Sources:** [2026 experimental manuscript](https://arxiv.org/abs/2604.24854) and [RydSFF code](https://github.com/oscars47/RydSFF), plus [Oxford data](https://doi.org/10.5287/ora-dow5oapxe). They study **disorder-induced entanglement and randomized measurements**, not a calibrated neutral-atom FTQC error-correction code [R17].

`quera_analysis.py` computes an independent **two-copy second-moment kernel** from per-randomization per-bitstring count histograms, using ordered distinct pairs to remove shot self-pair bias:

\[K_U =\frac{2^N}{M_U(M_U-1)}\sum_{x,y}n_{U,x}(n_{U,y}-\delta_{xy})(-2)^{-d_H(x,y)}.\]

Averaging this kernel estimates purity **only under an appropriately justified local unitary 2-design**, and QuEra's actual Hamiltonian-based randomized protocol must not be assumed equivalent. The output is deliberately marked `KERNEL_DIAGNOSTIC_ONLY_PROTOCOL_NOT_VERIFIED` and never claims reconstructed entanglement of the original experiment.

```zsh
./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh quera \
  --normalized-counts data/external_hardware/quera_aquila/verified_randomization_counts.csv \
  --output-dir outputs/platform_numeric/quera
```

**Required CSV:** `randomization_id,bitstring,count`. Each randomized setting needs at least two independent shots with consistent qubit count. The upstream source may use a different estimator and randomization protocol. A faithful paper reproduction must reconstruct the **actual source's** estimator and uncertainty propagation and match times/disorder parameters, not simply run this local-2-design diagnostic.

`neutral_atom_schedule.py` additionally implements a deterministic **illustrative** pairwise-exclusion parallel entangling-gate scheduler. Given atom positions, a stated exclusion radius, and two-body gate duration it generates independent layers, conserves operation order on shared atoms, and reports modeled latency. It is a genuine implementation, but its toy constraint is **not a measured Rydberg blockade model, transport scheduler, QEC implementation or calibrated neutral-atom FTQC architecture**.

```zsh
./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh neutral-schedule \
  --geometry-json examples/neutral_atom_geometry_illustrative.json \
  --output-dir outputs/neutral_atom_schedule_illustrative
```

## Validation status and next acceptance criteria

| Study | This build genuinely executed | Not yet established |
|---|---|---|
| IBM | Exact mathematical readout-only majority model and controlled two-epoch test fixtures | Real Fez raw decoding, device-matched numerical prediction, prospective independent holdout |
| Xanadu | Valid numeric-density-matrix checks, Wigner/purity identities and workbook parsing **on test fixtures** | Original Aurora/GKP source numerical results and an exact published figure/panel match |
| Quantinuum | Binomial aggregation and Wilson calculations **on test fixtures** | Actual Helios source-value numerical analysis, safe trusted conversion, paper result match |
| QuEra | Distinct-shot randomized kernel checks and physical-layout toy scheduler | Original randomized protocol reconstruction, Aquila data measurements, calibrated neutral-atom QEC |

The source dataset may be downloaded onto the owner's Mac. This runtime had no access to the upstream large files or owner's local Fez archive. **No vendor experimental outcomes have been fabricated or reported as reproduced.** The tests use clearly labeled controlled synthetic fixtures; their role is validating code behavior, not supporting published physical conclusions.

## Methods and authorship

The project uses established equations and libraries; its implementation has automated tests and requires independent review. Source formats and equations are not claims of novel quantum algorithm development. Numerical outputs always include a source SHA-256. The original vendor data, paper figures and any author-supplied scripts retain their own licenses and require attribution. See [LIMITATIONS.md](LIMITATIONS.md), [PROVENANCE.md](../reference/PROVENANCE_AND_CLAIMS.md), and [REFERENCES.md](../reference/REFERENCES.md).
