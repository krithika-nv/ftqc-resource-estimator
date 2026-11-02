# References and scientific attribution - canonical bibliography

**Bibliography and methods audit:** 30 October 2026. This is the sole numbered source list for active documentation. **R1–R17 are unique sources**; the 2026 Stein dataset is cited once as R9 (with its companion paper), and IBM current-backend documentation is cited once as R7. The historic 2024 Manila fixture is R11, not current hardware evidence. Primary source metadata and source scope were checked where accessible; a link being present does **not** verify the complete downloaded dataset or establish device-model fidelity.

## Numbered bibliography

| ID | Citation and primary link | Precisely what it supports / boundaries |
|---|---|---|
| **R1** | Fowler, A. G., Mariantoni, M., Martinis, J. M., & Cleland, A. N. (2012). *Surface codes: Towards practical large-scale quantum computation*. *Physical Review A*, **86**, 032324. [DOI](https://doi.org/10.1103/PhysRevA.86.032324). | General surface-code context; **none** of our simulated numerical results were taken from this paper. |
| **R2** | Gidney, C. (2021). *Stim: a fast stabilizer circuit simulator*. *Quantum*, **5**, 497. [DOI](https://doi.org/10.22331/q-2021-07-06-497); [source code](https://github.com/quantumlib/Stim). | Third-party stabilizer circuit generator, detector sampler and error-model API. |
| **R3** | Higgott, O., & Gidney, C. (2025). *Sparse Blossom: Correcting a million errors per core second with minimum-weight matching*. *Quantum*, **9**, 1600. [DOI](https://doi.org/10.22331/q-2025-01-20-1600); [PyMatching documentation](https://pymatching.readthedocs.io/en/stable/). | Required algorithmic attribution for **PyMatching v2**, the external MWPM decoder; no claim to have developed this decoder. |
| **R4** | Riverlane / Deltakit. *Simulating surface codes using Stim*. [Open textbook tutorial](https://textbook.riverlane.com/en/latest/notebooks/ch5-decoding-surfcodes/simulating-surface-codes-stim.html), accessed 30 October 2026. | Public protocol with rotated-X memory, four circuit-noise parameters, `rounds=distance`, Stim and PyMatching; **protocol-aligned subset only**, not a complete numerical figure reproduction. |
| **R5** | Google Quantum AI and collaborators (2025). *Quantum error correction below the surface code threshold*. *Nature*, **638**, 920–926. [DOI](https://doi.org/10.1038/s41586-024-08449-y). | Published Willow means `T1=68 µs`, `T2_CPMG=89 µs` and QEC cycle ≈1.1 µs. **CPMG is not Ramsey/free-idle T2\*.** |
| **R6** | Kan, S., Hoyt, A., Garner, S., et al. (2026). *Demonstration of Logical Error Suppression in a Surface Code Memory on a Cloud-Accessible IBM Superconducting Processor*. [arXiv:2610.23840v1](https://arxiv.org/abs/2610.23840), submitted 16 October 2026; [DOI](https://doi.org/10.48550/arXiv.2610.23840). **Preprint as of this audit.** | Nighthawk r2 surface-memory measurements, readout comparisons and detector-related findings; our plot is **secondary arithmetic using cited values**, not original hardware data or shot reproduction. |
| **R7** | IBM Quantum (2026). *View backend details / QPU information*. [Official guide](https://quantum.cloud.ibm.com/docs/en/guides/qpu-information); [IBMBackend properties API](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/ibm-backend). | Authenticated, timestamped backend characterization and benchmark metrics; does **not** imply public access to all pulse-level control or same-device free-idle noise parameters. Former duplicate backend-documentation entries were consolidated here. |
| **R8** | IBM Quantum (2026). *Monitor, calibrate, and benchmark*. [Official guide](https://quantum.cloud.ibm.com/docs/en/guides/calibration-jobs). | Distinction between frequently updated backend *benchmark/characterization* values and unreleased low-level hardware control parameters; calibration drift. |
| **R9** | Stein, S. (2026). *Calibration-Conditioned FiLM Decoders for Low-Latency Decoding of Quantum Error Correction Evaluated on IBM Repetition-Code Experiments - Datasets*. *Zenodo*, . [Dataset DOI](https://doi.org/10.5281/zenodo.20768087). Companion paper: Stein, S., Kan, S., Liu, C., et al. (2026), [arXiv:2601.16123](https://arxiv.org/abs/2601.16123). | 352 public **repetition-code** experiment snapshots, paired calibration, executed QASM and raw shots from Fez/Kingston/Pittsburgh. Actual calibration timestamps must be verified after import. Former duplicate dataset and manuscript entries were consolidated here. |
| **R10** | Litinski, D. (2019). *A game of surface codes: Large-scale quantum computing with lattice surgery*. *Quantum*, **3**, 128. [DOI](https://doi.org/10.22331/q-2019-03-05-128). | Future FTQC/lattice-surgery architectural context; not implemented in this repository. |
| **R11** | Qiskit / IBM Quantum. Historical *ibmq_manila* backend properties snapshot (internal timestamp 27 May 2024). [Upstream JSON](https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/fake_provider/backends/manila/props_manila.json); [raw file](https://raw.githubusercontent.com/Qiskit/qiskit-ibm-runtime/main/qiskit_ibm_runtime/fake_provider/backends/manila/props_manila.json). | Historical device-characterization values; **only a selected transcription** is bundled, not a verified complete upstream raw file. Regression fixture, not representative 2026 hardware. |
| **R12** | IBM Quantum / Qiskit. *Fake Provider* and *FakeManilaV2*. [Fake-provider guide](https://qiskit.qotlabs.org/docs/api/qiskit-ibm-runtime/fake-provider); [FakeManilaV2](https://qiskit.qotlabs.org/docs/api/qiskit-ibm-runtime/fake-provider-fake-manila-v2). | Explains historical backend-property snapshots used for simulations; using historical real-device properties **does not make a simulation an observed hardware result**. |
| **R13** | Wilson, E. B. (1927). *Probable inference, the law of succession, and statistical inference*. *Journal of the American Statistical Association*, **22**(158), 209–212. [DOI](https://doi.org/10.1080/01621459.1927.10502953). | Source of Wilson score interval; using a **marginal** interval does not guarantee simultaneous coverage or predictive validity for a multi-event hardware workload. |

## Source-to-claim map

| Claim / method | Sources | Local evidence or required caution |
|---|---|---|
| Surface-code memory, generated circuits, detector error graph, MWPM | R1–R4 | Saved simulated shots and experiment settings in `../outputs/stim_memory/`, verified separately from third-party theory |
| 40-event independent workload and reliability budget | R13 for statistical interval; workload is **project-defined**, not sourced from a real chip | `METHODS.md`, `EXPERIMENTS_AND_EVIDENCE.md`, `LIMITATIONS.md` L01–L03 |
| `rounds=d` noise protocol | R4 | Our benchmark is smaller than the published tutorial's full grid and completed locally with 400,000 simulator shots; not a full reproduction of the paper's figures |
| Willow coherence and QEC timing | R5 | Mean T2_CPMG is not unprotected Ramsey T2\*; controller channel numbers are **hypothetical** |
| Nighthawk readout/logical-memory values | R6 | Secondary arithmetic in `../outputs/published_readout/`; not our real-device measurement |
| Current IBM calibration availability and drift | R7–R8 | Account access, per-property timestamps, concurrency/free-idle limits remain |
| 2026 calibration-plus-raw-shots dataset | R9 | Fez archive processed in the owner's local run; ~1.09 million decoded chain-shots, with narrower source-matched validation limits |
| Historic Manila calibration and simulation proxy | R11–R12 | Five physical qubits, outdated, not a scaled rotated-surface-code validation |
| Roadmap toward full logical FTQC architectures | R1, R10 | Lattice surgery and logical-gate FTQC not implemented |

## Citation and authorship rules

1. Cite **this bibliography** for external methods, original papers and vendor-characterization facts; cite a specific `outputs/` report, manifest, count or SHA when quoting **this project's own** experimental outcomes.
2. Never confuse simulated logical failure per memory experiment, hardware logical failure **per round**, and detector-pair signatures.
3. An external dataset's **publication date is not its calibration date**. Report the actual processor, snapshot timestamp, protocol, code family and missing measurements.
4. Third-party Stim/PyMatching and published protocols are credited; scientific novelty and internet-wide code uniqueness are **not established**. See [PROVENANCE.md](PROVENANCE_AND_CLAIMS.md).
5. The publication status of the Kan preprint and the live availability of IBM devices may change. Recheck both before external publication.

## Zotero

Kan et al. RIS import: [`../references/kan2026_nighthawk.ris`](../../references/kan2026_nighthawk.ris). It has not been imported into the user's Zotero account by this repository.

## Additional primary hardware-platform evidence sources (30 October 2026)

- **R14** - Xanadu Aurora:** XanaduAI, *Aurora data*, the publicly accessible dataset for the *Scaling and networking a modular photonic quantum computer* experiments. [Source data and download instructions](https://github.com/XanaduAI/xanadu-aurora-data). Photonic networking experiment data, **not** a direct calibrated photonic FTQC logical-error model.
- **R15** - Xanadu GKP:** XanaduAI, *Integrated photonic source of GKP qubits: data*. [Dataset and processing code](https://github.com/XanaduAI/xanadu-gkp-data). Public optical-state tomography/data, roughly 14 GB compressed; **not** imported in this repository.
- **R16** - Quantinuum Helios:** Ransford, A. et al. (2026), *A 98-qubit trapped-ion quantum computer with all-to-all connectivity*, *Nature* **655**, 81–86, [DOI](https://doi.org/10.1038/s41586-026-10676-4); [Helios analysis data](https://github.com/Quantinuum/Helios-paper-data); [public hardware specifications](https://github.com/Quantinuum/quantinuum-hardware-specifications). Specific trapped-ion QCCD benchmarks, **not** source-equivalent to IBM device calibrations.

These references identify platform-specific sources. **Aurora published figure-data matrices and Helios MCMR raw counts have been reanalyzed**, but original optical-signal processing, GKP logical calibration and neutral-atom loss-aware QEC reproduction remain incomplete. See [EVIDENCE_STATUS.md](../validation/EVIDENCE_AND_RESULTS.md).

- **R17** - QuEra Aquila randomized-measurement experiment:** Scholin, O. et al. (2026), *Dataset for Randomised measurements of a disorder-induced entanglement transition in a neutral atom quantum processor*, University of Oxford repository, [data DOI](https://doi.org/10.5287/ora-dow5oapxe), [experiment and analysis source](https://github.com/oscars47/RydSFF). **Use:** evidence-only neutral-atom file adapter, not measured neutral-atom surface-code validation.


## Stage 18 numerical-analysis source-to-method notes

- **[R9] IBM Zenodo 2026:** Raw calibrated repetition-code experiments; new `ibm_hardware_analysis.py` is a *distinct independent final-data majority null baseline*, not the source decoder or paper's FiLM/MWPM benchmark. Source files/registrations must be independently mapped before use.
- **[R14–R15] Xanadu Aurora and GKP:** `xanadu_analysis.py` implements generic mathematical extraction and density-matrix diagnostics; no numeric equality to source paper is claimed until author data and PNR/figure identity are verified.
- **[R16] Quantinuum:** `quantinuum_analysis.py` computes binomial intervals from *verified executed-shot* counts, not from the hardware specification data sheets. Helios `.p` source data require trusted conversion and paper-level provenance.
- **[R17] QuEra Aquila:** `quera_analysis.py` contains an independent randomized local-2-design kernel, **not a confirmed reproduction of the original Hamiltonian-based randomized measurement protocol**. Its neutral-atom geometry scheduler is a hypothetical algorithmic study, not source-hardware calibration.

See [Stage 18 complete scientific contract](../validation/PLATFORM_NUMERICAL_VALIDATION.md).
