# Real hardware calibration import - ibmq_manila

**Snapshot:** 2024-05-27T15:27:23-03:00 (historical IBM backend properties).
**Source:** https://raw.githubusercontent.com/Qiskit/qiskit-ibm-runtime/main/qiskit_ibm_runtime/fake_provider/backends/manila/props_manila.json
**SHA256 of ingested source bytes:** `0b1eb4a7a5de2009e2af5f0dfc013459f13f7531709599a121da5c7dcb2f661c`
**Input provenance:** CURATED_PUBLISHED_SUBSET; the bundled subset is a transcription, not a SHA-verified copy of the entire upstream raw JSON.

## Measured properties (NOT guessed)

- Number of characterized physical qubits: 5.
- Median T1: 144.673 µs.
- Median Hahn-echo T2: 54.361 µs. **Not Ramsey T2-star.**
- Median readout duration: 5.351 µs.
- Median readout error: 2.1900%; mean 3.7320%.
- Mean directed CX gate error: 0.9955% across 8 calibrations.

## Calibration-informed, explicitly unvalidated simulator input (NOT hardware-validated)

`calibration_projection.json` contains a **five-qubit d=3 repetition-code demonstration**, derived from published qubit and gate metrics. The T1-only waiting channel uses the measured readout duration as a *hypothesized* wait. It does not assume T2 echo equals free-idle Ramsey. Gate RB error mapped onto Stim's generic after-Clifford depolarization is a **proxy**, not a physical equality. No readout channel count is inferred from gate/readout timings.

### Not established

- No matched real-device QEC shots or experimentally verified logical-failure predictions.
- No contemporaneous or 2026 calibration; the snapshot is from 2024.
- No full surface-code validation: this machine has only five physical qubits.
- No free-idle Ramsey T2*, no measured cross-talk, no schedule/concurrency model.

**Next:** Compare a specifically matched open hardware repetition-code dataset against this proxy, with timestamps and held-out shots. See `docs/PHYSICAL_CALIBRATION.md` and `docs/LIMITATIONS.md`.
