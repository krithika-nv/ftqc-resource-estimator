# Surface-code MEMORY study - real Stim/PyMatching experiment output

**Scope:** memory for an identical fixed number of syndrome rounds across code distances; not a logical gate or photonic FTQC prediction.

- Simulator provenance: Stim `1.16.0`, PyMatching `2.4.0`.
- Decoder: MWPM, decomposed detector error model. Basis: X; syndrome rounds: 9; uniform circuit noise p=0.003.
- Workload: 4 independent logical patches, 10 consecutive *9-round* memory windows.
- Reliability goal for the entire independent-events proxy: 0.1.
- Uncertainty: two-sided Wilson 95% per memory experiment; upper endpoint conservatively propagated under independence.
- Latency, patch sites, reserve, and optional controller overhead: assumed, not measured. Controller site-equivalent units are an illustrative cost *proxy*, not extra physical qubit counts.
- The same physical noise and nine-round memory circuit is reused for each control design; faster cycles are **not** simulated with worse noise or independently calibrated.
- Statistical sample-planning fields give the MINIMUM trials that could clear the per-event budget if zero failures occurred; they do not establish power for nonzero rates or simultaneous coverage.

## Observations and modeled costs

| Assumed control | d | MWPM fail/shots | trivial fail/shots | pL (memory) | upper 95% | patch+reserve | controller proxy | total site-equivalents | total µs | robust feasible |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fast_control_low_reserve | 3 | 402/20000 | 2966/20000 | 0.0201 | 0.022139 | 70 | 0 | 70 | 50.00 | no |
| balanced_control | 3 | 402/20000 | 2966/20000 | 0.0201 | 0.022139 | 73 | 0 | 73 | 105.00 | no |
| conservative_reserve | 3 | 402/20000 | 2966/20000 | 0.0201 | 0.022139 | 79 | 0 | 79 | 155.00 | no |
| fast_control_low_reserve | 5 | 115/20000 | 4607/20000 | 0.00575 | 0.006897 | 200 | 0 | 200 | 50.00 | no |
| balanced_control | 5 | 115/20000 | 4607/20000 | 0.00575 | 0.006897 | 208 | 0 | 208 | 105.00 | no |
| conservative_reserve | 5 | 115/20000 | 4607/20000 | 0.00575 | 0.006897 | 226 | 0 | 226 | 155.00 | no |
| fast_control_low_reserve | 7 | 53/20000 | 5893/20000 | 0.00265 | 0.0034643 | 396 | 0 | 396 | 50.00 | no |
| balanced_control | 7 | 53/20000 | 5893/20000 | 0.00265 | 0.0034643 | 412 | 0 | 412 | 105.00 | no |
| conservative_reserve | 7 | 53/20000 | 5893/20000 | 0.00265 | 0.0034643 | 447 | 0 | 447 | 155.00 | no |

## Two-objective Pareto set (among conservative feasible points)

No observed point passed the upper-interval budget; this is not proof that none can.

## What can and cannot be concluded

Results test conditional architecture-memory tradeoffs under a common *simulated* circuit and decoder. Changing the assumed cycle time or assigning extra controller cost does not change circuit noise, a simplifying assumption. The controller overhead is a hypothetical normalized site-equivalent proxy, not measured classical electronics or extra physical qubits. All scenarios reuse the same event probabilities; none is independently calibrated hardware. The workload-level upper endpoint is a propagated **per-experiment Wilson endpoint**, not simultaneous confidence coverage or a complete uncertainty budget.

## Reproduce

```bash
./scripts/commands/RUN_STIM_MEMORY.sh                # baseline experiment
./scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh       # distance 7/9 and optional controller-cost study
```

## Methods and source

- [Stim](https://github.com/quantumlib/Stim) generated rotated surface-code memory circuits.
- [PyMatching](https://pymatching.readthedocs.io/) detector-error-model matching and decoding API.
- [Fowler et al. (2012)](https://doi.org/10.1103/PhysRevA.86.032324) motivates the surface-code context; numerical values come from *this* run, not the paper.
