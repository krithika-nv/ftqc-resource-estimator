# Controller-induced idle-noise model and provenance

This document preserves the physical assumptions and derivation of the modeled idle-noise experiment. For executed results and current status, consult [evidence and results](../validation/EVIDENCE_AND_RESULTS.md) and the actual simulator reports in repository-root `outputs/idle_coherence/`. Published coherence is not proof of measured controller-induced idle time.

## Published input assumptions
| Quantity | Input | Status | Traceability |
|---|---:|---|---|
| Mean coherence T1 | 68 µs | **Published measurement**, Willow QEC processor | Google Quantum AI and Collaborators (Nature 2025) |
| Mean T2,CPMG | 89 µs | **Published measurement**, echo-based | Same; **NOT** idle Ramsey T2 |
| Surface-code cycle duration | 1.1 µs | **Published measurement** | Same |
| Code family, distance/rounds | Rotated X memory, r=d, d=3/5/7/9 | **Study selection** | Stim generated circuits / Riverlane teaching protocol |
| Four baseline circuit-noise parameters | all 0.003 | **Hypothesis**, not calibrated Willow data | Preserves prior reproducible simulation choices |
| Channel counts | 256 / 128 / 32 shared across 4 patches | **Hypothesis** | No measured hardware support |
| Readout slot | 0.45 µs per batch | **Hypothesis** | No measured hardware support |
| Per-channel controller power | 0.35 W | **Hypothesis, excluded from quantum error channel** | No measured hardware support |
| Waiting-time schedule | max(0, ceil(checks/channels)×slot − 1.1 µs) | **Derived from hypothesis** | Not an actual pulse timing schedule |
| Per-round idle channel | Pauli twirl of exponentials | **Analytical approximation** | Derivation below |

**Primary publication:** Google Quantum AI and Collaborators, *Quantum error correction below the surface code threshold*, Nature 638, 920–926 (2025). https://doi.org/10.1038/s41586-024-08449-y

**Stim reference:** https://github.com/quantumlib/Stim (Circuit.generated / PAULI_CHANNEL_1 / detector sampler APIs)

**PyMatching reference:** https://pymatching.readthedocs.io/ (Matching.from_detector_error_model / decode_batch APIs)

**Related independently implemented teaching protocol:** Riverlane, *Simulating surface codes using Stim*: https://textbook.riverlane.com/en/latest/notebooks/ch5-decoding-surfcodes/simulating-surface-codes-stim.html

## Derivation of the additional idle-noise channel

Let `u = exp(-Δt/T1)` and `v = exp(-Δt/T2_proxy)`. After discarding the non-unital part of amplitude damping (Pauli twirling), the X and Y Pauli transfer eigenvalues are `v`; the Z eigenvalue is `u`. Inverting the Pauli transfer map:

```
P(X) = P(Y) = (1-u)/4
P(Z) = (1+u-2v)/4
P(I) = 1 - P(X) - P(Y) - P(Z)
```

The original baseline four noise knobs are still set to 0.003. The extra channel is inserted **once per round on data qubits** after the generator's first `TICK` at each round start. New decoder error models are generated from each amended circuit so matching receives the additional noise. The algorithm refuses to continue if the expected `REPEAT`/initialization layout changes.

**Scientific caveats:** The conversion drops non-unital relaxation and treats the CPMG echo-based coherence value as if it were an unprotected dephasing scale. This may be too optimistic for a genuine idle. The controller-readout batching model assumes a wait can be attached to data without rescheduling gates and ancilla operations; this is not demonstrated. Decoder latency (e.g. 63 µs measured in the paper) is **not** automatically a per-round data idle, so it is not injected. We do not claim to model the original Willow experiment or original paper's physical-error-channel distribution.
