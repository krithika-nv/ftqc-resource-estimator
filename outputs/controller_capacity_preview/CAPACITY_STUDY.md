# Capacity-constrained control envelope - independent architecture extension

**Status:** UNVERIFIED owner-supplied manifest; analysis is not a validation certificate
**Scientific boundary:** abstract readout-channel scheduling bound, NOT a waveform/circuit-level schedule; Stim error rates are held fixed, so extra wait/decoherence and controller noise have NOT been simulated.
**Physical accounting:** patch qubits and controller-channel/power proxies are reported in **separate columns**; electronic channels and watts are not added to physical qubits.
**Inputs:** all example readout timing and power coefficients are HYPOTHETICAL, not measurements from quantum hardware.

## Scenario results

| d | Controller | Physical patch qubits | Readout channels | Batches / round | Controller power proxy (W) | Memory time (us) | Reliability feasible |
|---:|---|---:|---:|---:|---:|---:|---|
| 7 | wide_parallel_readout | 388 | 256 | 1 | 89.60 | 57.5 | False |
| 7 | medium_parallel_readout | 388 | 128 | 2 | 44.80 | 95.0 | False |
| 7 | constrained_parallel_readout | 388 | 32 | 6 | 11.20 | 268.0 | False |
| 9 | wide_parallel_readout | 644 | 256 | 2 | 89.60 | 89.0 | True |
| 9 | medium_parallel_readout | 644 | 128 | 3 | 44.80 | 135.5 | True |
| 9 | constrained_parallel_readout | 644 | 32 | 10 | 11.20 | 430.0 | True |

## Feasible nondominated points (qubits, power, latency independently)

- d=9, wide_parallel_readout
- d=9, medium_parallel_readout
- d=9, constrained_parallel_readout

An electronic readout channel is NOT a physical qubit or universal readout architecture. Real readout multiplexing, gate scheduling, readout duration, controller bandwidth, correlated errors, classical decoder pipeline, and waiting-time decoherence must be calibrated and incorporated into circuit simulation before any performance claim.
An operational extension would build a matching error channel with duration-dependent idle errors and independently measured controller throughput; this project does not yet implement that calibration.
