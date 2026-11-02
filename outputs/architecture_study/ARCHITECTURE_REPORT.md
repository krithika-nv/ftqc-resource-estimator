# Architecture comparison - reproducible example

**Interpretation boundary:** This is a **toy surface-patch and abstract resource-delivery model**. It is not an estimation of Xanadu hardware, photonic GKP logical-error performance, magic-state factories, or total FTQC cost.

- Logical qubits: **24**
- Sequential logical layers: **4000**
- Modeled logical locations: **96000**
- Target failure: **0.01**
- Reliability: **unfitted heuristic (NO statistical uncertainty)**

## Architecture inputs

### fast_control_supply_limited
- Syndrome round: 0.5 μs; decoder delay: 1 μs
- Resource factories: 1; attempt rate: 10/μs/factory
- Preparation success: 0.4; segments: (0.7, 0.8, 0.8)
- Delivery probability: 0.1792
- Extra patch reserve fraction: 0.05; assumed factory site-equivalents per factory: 100

### slow_control_high_supply
- Syndrome round: 1.3 μs; decoder delay: 3 μs
- Resource factories: 2; attempt rate: 14/μs/factory
- Preparation success: 0.8; segments: (0.97, 0.98)
- Delivery probability: 0.7605
- Extra patch reserve fraction: 0.08; assumed factory site-equivalents per factory: 400

### balanced_midrange
- Syndrome round: 0.7 μs; decoder delay: 1.5 μs
- Resource factories: 1; attempt rate: 25/μs/factory
- Preparation success: 0.75; segments: (0.92, 0.97)
- Delivery probability: 0.6693
- Extra patch reserve fraction: 0.07; assumed factory site-equivalents per factory: 650

## Minimum model-feasible code distance

| Architecture | d | Site equivalents | Runtime (ms) | Bottleneck | Modeled failure |
|---|---:|---:|---:|---|---:|
| fast_control_supply_limited | 11 | 6174 | 53.57 | supply | 0.009554 |
| slow_control_high_supply | 11 | 7047 | 69.20 | compute | 0.009554 |
| balanced_midrange | 11 | 6839 | 36.80 | compute | 0.009554 |

## Pareto set (site count and latency, model-reliability constraint)

2 non-dominated scenarios found within the scanned distances.

- `fast_control_supply_limited`, d=11: 6174 site equivalents; 53.57 ms; supply-limited
- `balanced_midrange`, d=11: 6839 site equivalents; 36.80 ms; compute-limited

## What the study demonstrates

1. For a fixed **assumed** reliability model, faster syndrome cycles need not reduce runtime when the resource supply is the bottleneck.
2. High success probability helps delivery throughput, but the cost of more physical factories and slower control can reverse the preferred design.
3. The selected design depends on the **specified resource accounting** and a fixed workload; Pareto results are not intrinsic rankings of FTQC platforms.

## Missing physics and uncertainty

- The assumed logical-error formula is not calibrated to a quantum code simulation or hardware.
- An error rate **per logical layer** is treated as independent across every logical qubit-layer; correlated failures and different gate types are omitted.
- Resource failures are treated as **heralded**, costing attempts/time rather than logical errors.
- `max(compute_us, supply_us)` assumes perfect overlap, no buffer starvation, and no start-up cost.
- Factory site equivalents are analyst-specified accounting proxies, not a physical factory layout.
- A real surface-code memory experiment cannot be used as a logical-gate rate without a matched schedule.
- No numerical thresholds or photonic resource estimates are extracted from the cited papers.

## Reproduce

```bash
PYTHONPATH=src python3 -m ftqc_resource_estimator.study --config examples/architecture_scenarios.json --output-dir outputs/architecture_study
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Figures generated: True. Matplotlib optional; all CSV and Markdown outputs are standard-library.

## Analysis context (not model calibration)

- Fowler et al. (2012), *Surface Codes: Towards Practical Large-Scale Quantum Computation*. https://doi.org/10.1103/PhysRevA.86.032324
- Horsman et al. (2012), *Surface Code Quantum Computing by Lattice Surgery*. https://doi.org/10.1088/1367-2630/14/12/123011
- Zhou, Cain, Lukin (2025), *Opportunities in Full-Stack Design of Low-Overhead Fault-Tolerant Quantum Computation*. https://doi.org/10.1038/s43588-025-00895-6
- Microsoft QRE documentation (conceptual layer decomposition only). https://learn.microsoft.com/azure/quantum/intro-to-resource-estimation
