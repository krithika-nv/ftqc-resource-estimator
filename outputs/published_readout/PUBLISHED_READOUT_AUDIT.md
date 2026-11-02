# Independently analyzed **published** IBM Nighthawk readout measurements

> These are **reported values from Kan et al. (2026)**, not new experiments or an independently
> reproduced hardware result. We independently recompute arithmetic contrasts only.

- Primary source: https://arxiv.org/html/2610.23840 (Section 2, Fig. 2, preprint as of 28 October 2026).
- Device: IBM Nighthawk r2 `ibm_phoenix`, selected d=3 placement with fused reset.
- Two readout durations: **1.94 µs** standard vs **1.14 µs** short, a **0.80 µs** difference.
- The published logical-error parameter ε is **per syndrome round**, not the total probability of a 9-round memory failure.

| Memory basis | Reported ε, standard | Reported ε, short | Derived reduction |
|---|---:|---:|---:|
| X_memory | 1.67% | 0.98% | 41.3% |
| Z_memory | 0.82% | 0.63% | 23.2% |

## Why a coherence-only idle model is insufficient

The same publication reports a median change in *detector-pair* probabilities, not logical error rates:

| Detector-pair signature | Measured reduction | Coherence-only prediction | Unexplained residual |
|---|---:|---:|---:|
| bit_flip_associated | 0.22 pp | 0.23 pp | -0.01 pp |
| phase_associated | 0.95 pp | 0.22 pp | +0.73 pp |

**Interpretation:** The phase-associated reduction is over four times the coherence-only prediction.
A single effective T2 from an echo/CPMG protocol cannot make the proposed waiting model fully calibrated.
The authors investigate ancilla-state-dependent ZZ phases and other scheduling effects. See paper §2 and appendix.

## What this fixes - and what it does not

- **Fixed:** A published example now grounds actual readout durations AND experimental sensitivity to readout shortening.
- **Fixed:** We avoid treating T2_CPMG as unprotected Ramsey T2; the comparison exposes missing phase physics.
- **Not fixed:** The Willow 32/128/256 channel scenarios remain hypotheses. No credible matching channel-capacity
  measurement or per-qubit free-idle Ramsey T2* was obtained for those same schedules.
- **Not fixed:** These paper values are a *separate device and protocol*; they are not calibration inputs for
  the Willow-inspired Stim baseline, nor can reported ε or detector pairs be inserted as per-qubit Pauli error rates.
- **Next real calibration:** same-device qubit-by-qubit Ramsey data, timestamped readout parallelism and
  durations, placement-dependent noise, and original syndrome-shot data. See `docs/DEVICE_CALIBRATION_REQUIRED.md`.

Source data are rounded; uncertainty intervals and shot counts for these specific summarized contrasts are not
reconstructed here. The source paper contains further statistical analyses and controls.
