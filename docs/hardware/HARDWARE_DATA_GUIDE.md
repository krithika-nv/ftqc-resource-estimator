# Hardware dataset sources and adapters

> Current documentation is authoritative only for the specific claims supported by linked measured data, simulation outputs and tests.

## Platform-specific dataset adapters

**Goal:** Maintain one portable FTQC *decision methodology* while keeping measured hardware evidence, physical quantities, and models separate for superconducting, photonic, trapped-ion, and neutral-atom systems. **Only source-file inspection and provenance indexing are implemented for the three non-IBM families.** Do not imply physical calibration, figure reproduction or QEC validation from a file inventory. Source original data stays outside Git; users explicitly choose large downloads.

### Scope by platform

| Adapter | Source ID | Upstream primary data | Locally supported import | Scientific gap |
|---|---|---|---|---|
| Superconducting / IBM | `ibm_qec_zenodo_2026` | [IBM/PNNL 2026 paired QEC archive](https://doi.org/10.5281/zenodo.20768087) | Source-file catalog, plus **existing** matched calibration/info/QASM/bitstrings verifier (`scripts/commands/RUN_MATCHED_HARDWARE_EVIDENCE.sh`) | Actual hardware repetition-code decoding, held-out model prediction |
| Superconducting / IBM | `ibm_live_properties` | [IBM backend properties](https://quantum.cloud.ibm.com/docs/en/guides/qpu-information) | File index; **existing** authenticated export / calibration normalizer | Correlated noise, free-idle Ramsey, matched QEC results |
| Photonic / Xanadu | `xanadu_aurora` | [Aurora public repository](https://github.com/XanaduAI/xanadu-aurora-data), [Nature 2025 paper](https://www.nature.com/articles/s41586-024-08406-9) | `.npy` quadrature, optical-switch and decoder-decision array headers; plot `.xlsx` registered but not numerically parsed | Optical-source/loss interpretation and model fit |
| Photonic / Xanadu | `xanadu_gkp` | [GKP public repository](https://github.com/XanaduAI/xanadu-gkp-data), [Nature 2025 paper](https://doi.org/10.1038/s41586-025-09044-5) | `analysis_results.npy` shape/dtype; 14 GB `tar.gz` registered without extraction | GKP characterization reconstruction and fault-tolerance mapping |
| Trapped ion / Quantinuum | `quantinuum_helios` | [Helios paper data](https://github.com/Quantinuum/Helios-paper-data) | `.p` serialized benchmarks **opaque/index-only** (never unpickle); JSON/CSV structure checks where available | Trusted conversion to safe numerical tables, per-experiment matching |
| Trapped ion / Quantinuum | `quantinuum_specifications` | [H1/H2 hardware specifications](https://github.com/Quantinuum/quantinuum-hardware-specifications) | Data file inventory and readable JSON/CSV header checks | Specification is not an execution-matched calibration |
| Neutral atom / QuEra | `quera_aquila_2026` | [Oxford experimental dataset](https://doi.org/10.5287/ora-dow5oapxe) and [RydSFF code](https://github.com/oscars47/RydSFF) | Task JSON metadata, result `.npy` headers, archive member listing | This is **randomized measurement/entanglement analysis**, not neutral-atom QEC failure rate validation |

### Download lightweight source repositories (Zsh)

```zsh
# From repository root; download separately, deliberately:
./scripts/commands/fetch_external_hardware_sources.sh aurora
./scripts/commands/fetch_external_hardware_sources.sh gkp
./scripts/commands/fetch_external_hardware_sources.sh helios
./scripts/commands/fetch_external_hardware_sources.sh ion-specs
./scripts/commands/fetch_external_hardware_sources.sh quera-code
```

These commands clone source repositories under gitignored `data/external_hardware/`. **They do not download all associated giant S3 or Oxford raw experiment archives.** Review each source's license and upstream instructions before acquiring files. Git revisions and complete original source URLs should be recorded alongside any published result.

### Import each platform's real locally downloaded files

```zsh
# IBM 2026 paired QEC measurements (download 2026 archive first, using existing downloader):
./scripts/commands/RUN_MATCHED_HARDWARE_EVIDENCE.sh --archive data/public_calibrations/2026/ibm_fez.tar.gz --backend ibm_fez --max-age-days 365 --output-dir outputs/matched_hardware_evidence/ibm_fez
./scripts/commands/RUN_HARDWARE_DATASET_IMPORT.sh --source ibm_qec_zenodo_2026 --input data/public_calibrations/2026/ibm_fez.tar.gz --output-dir outputs/hardware_dataset_imports/ibm_fez_source

# Xanadu Aurora (cloned source repository, which includes figure workbook); raw quadratures live separately on S3:
./scripts/commands/RUN_HARDWARE_DATASET_IMPORT.sh --source xanadu_aurora --input data/external_hardware/xanadu_aurora --output-dir outputs/hardware_dataset_imports/aurora
# GKP reconstructed state analysis file (cloned source repository), not the 14GB S3 archive:
./scripts/commands/RUN_HARDWARE_DATASET_IMPORT.sh --source xanadu_gkp --input data/external_hardware/xanadu_gkp/analysis_results.npy --output-dir outputs/hardware_dataset_imports/gkp

# Quantinuum Helios: published .p benchmark objects are indexed, NEVER unpickled:
./scripts/commands/RUN_HARDWARE_DATASET_IMPORT.sh --source quantinuum_helios --input data/external_hardware/quantinuum_helios/data --output-dir outputs/hardware_dataset_imports/helios
./scripts/commands/RUN_HARDWARE_DATASET_IMPORT.sh --source quantinuum_specifications --input data/external_hardware/quantinuum_specifications/data --output-dir outputs/hardware_dataset_imports/ion_specs

# QuEra: manually download Oxford experiment archives into gitignored data/external_hardware/quera_data/ first:
./scripts/commands/RUN_HARDWARE_DATASET_IMPORT.sh --source quera_aquila_2026 --input data/external_hardware/quera_data --output-dir outputs/hardware_dataset_imports/quera
```

Every run generates `DATASET_EVIDENCE_MANIFEST.json`, `DATASET_FILES.csv`, `DATASET_REPORT.md`. NumPy allows safe array header inspection (`allow_pickle=False`). Large files (>32 MiB) are **not hashed by default** to avoid lengthy I/O; `--hash-large` opts in. No files are extracted or automatically interpreted as physical calibration. The `--max-files` guard caps inventory work.

### Upstream-specific handling and safety

- **Aurora:** the original source lists 1,440 optical data files around **458 MB each**, plus an approximately **17.5 GB** compressed decoder demonstration. Start with the included publication data workbook and one small sample, not a full download. The workbook is registered, **not parsed** by this importer. [Xanadu Aurora README](https://github.com/XanaduAI/xanadu-aurora-data).
- **GKP:** the source lists a **14.0 GB** compressed raw archive and **19.3 GB** extracted data. The lightweight reconstructed `analysis_results.npy` is a first practical entry point; reading its shape is not tomography validation. [Xanadu GKP README](https://github.com/XanaduAI/xanadu-gkp-data).
- **Helios:** many `.p` files are Python pickles. Python pickle deserialization can execute arbitrary code. These **must remain opaque** in our reproducible, safe source pipeline. To analyze their contents, perform an explicitly trusted-source conversion in a separate quarantined workflow and emit auditable numeric CSV/JSON. No such converter is claimed completed here. [Helios data directory](https://github.com/Quantinuum/Helios-paper-data/tree/main/data).
- **Quantinuum specs:** upstream calls this published H1/H2 product-datasheet data, not run-by-run qubit calibration; do not equate spec values with actual observed shot performance.
- **QuEra:** source paper's data archive is in Oxford, with task metadata, experimental shot results and numerical emulation. It does not establish neutral-atom surface-code performance. [Source README](https://github.com/oscars47/RydSFF).
- **IBM:** experimental records need their calibration timestamps and exact executed repetition-code QASM. Source-file indexing alone is not the matched analysis; use the existing specialized auditor.

### Analysis next steps (not yet executed)

1. On Mac, fetch actual source repositories and generate the first manifests. Record upstream repository commit IDs in a lab notebook.
2. Import a representative Aurora figure table into a carefully cited analysis and match the authors' reported figure **before** propagating to FTQC resource assumptions.
3. Assess GKP reconstructed states against published state-quality metrics under a documented, reproduction-tested model.
4. Convert only trusted Helios benchmarks to safe typed arrays and reconstruct measured benchmark statistics.
5. Link neutral-atom shot results to the **same** experiment/task, timestamps, and calibration record before any inference.
6. Calibrate each platform's own relevant physics and uncertainty; independent held-out experimental predictions are a separate milestone.

### Authorship and licensing

The integration code is project-specific. Published sources and algorithms retain their own authorship/licensing. No upstream analysis dataset is copied into the shipped repository. See [`PROVENANCE.md`](../reference/PROVENANCE_AND_CLAIMS.md) and [`LIMITATIONS.md`](../validation/LIMITATIONS.md).

## Source registry and evidence boundaries

**Scope:** public primary analysis sources and evidence limits. Listing a source does not mean its data have been downloaded, imported or calibrated to the estimator.

| Platform | Provider / dataset | What is actually available | Pipeline status |
|---|---|---|---|
| superconducting | [IBM Quantum / PNNL / ibm_qec_zenodo_2026](https://doi.org/10.5281/zenodo.20768087) | paired calibration, raw repetition-code experiments and executed circuits | existing_matched_ibm_pairing_and_source_indexing |
| superconducting | [IBM Quantum / ibm_live_properties](https://quantum.cloud.ibm.com/docs/en/guides/qpu-information) | current periodic calibration / benchmarking properties | authenticated_export_and_source_indexing |
| photonic | [Xanadu Aurora / xanadu_aurora](https://github.com/XanaduAI/xanadu-aurora-data) | published photonic networking experiment data | source_specific_indexer_available_real_files_not_bundled |
| photonic | [Xanadu GKP / xanadu_gkp](https://github.com/XanaduAI/xanadu-gkp-data) | published GKP source optical-state data (14 GB archive) | source_specific_indexer_available_real_files_not_bundled |
| trapped_ion | [Quantinuum Helios / quantinuum_helios](https://github.com/Quantinuum/Helios-paper-data) | published trapped-ion experimental benchmark data | source_specific_indexer_available_pickle_opaque |
| trapped_ion | [Quantinuum / quantinuum_specifications](https://github.com/Quantinuum/quantinuum-hardware-specifications) | published trapped-ion hardware specifications and benchmarks | source_specific_indexer_available_real_files_not_bundled |
| neutral_atom | [QuEra Aquila / Scholin et al. 2026 / quera_aquila_2026](https://doi.org/10.5287/ora-dow5oapxe) | real Aquila randomized-measurement experiments, task metadata, calibration and simulation analysis | source_specific_indexer_available_real_files_not_bundled |

### Scientific boundary

- IBM processor properties characterize **superconducting** qubits. They cannot parameterize photonic loss, GKP state defects or trapped-ion transport.
- Xanadu Aurora and GKP data address specific **photonic experiments**; they are not automatically logical FTQC benchmarks.
- Quantinuum Helios data and specifications concern **trapped-ion** devices; typical spec values are not shot-matched per-qubit calibrations.
- QuEra Aquila experiments concern **neutral atoms** and randomized measurements, not a directly measured neutral-atom QEC failure curve.
- No cross-platform numeric rankings should be produced without equivalent workloads and separately validated physical mappings.
- The archived 2026 IBM repetition-code data can support a **repetition-code** validation, not a surface-code hardware claim.


See [HARDWARE_DATASET_ADAPTERS.md](HARDWARE_DATA_GUIDE.md) for local source-file imports and physical limits.
