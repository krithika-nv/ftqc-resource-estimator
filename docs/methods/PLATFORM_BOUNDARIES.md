# Hardware-independent core, hardware-specific adapters and evidence boundaries

**Status: architecture separation implemented and locally tested in .** This document specifies the allowed use of platform-specific measurements. It does **not** claim calibrated hardware prediction.

## Analysis goal and layered architecture

The project asks **how specified reliability targets, code distance, resources and control schedules affect the feasibility of a proposed quantum-error-correction memory architecture**, and which measured inputs would be necessary to make those estimates predictive. The term **hardware-agnostic** applies to the **decision methodology** (reliability budgets, uncertainty, constraints and Pareto filtering), not to interchangeable physical units, common fault mechanisms or a universal calibrated model.

| Layer | Implemented modules | What is portable | What must stay separate |
|---|---|---|---|
| 1. Abstract decision core | `model.py`, `reliability.py`, `pareto.py`, `sample_planning.py`, and aspects of `architecture.py` / `study.py` | Workload budgets, confidence bounds, distance selection under *stated* error model, dominance tests | The `architecture.py` heralded-resource supply and threshold heuristic contain **optical-inspired/phenomenological assumptions**; neither is an empirically universal FTQC law [R1, R2, R13] |
| 2. Platform scenario adapters | `hardware_profiles.py`, `hardware_study.py` | A consistent *question* and synthetic workload labels | Photonic resource-state equivalents, superconducting data/syndrome qubits, and trapped-ion ions are **different units**. Latencies are not comparable performance benchmarks |
| 3. Real-data intake | `modern_calibration.py`, legacy `public_calibration.py`, `platform_boundaries.py` | Reproducible provenance, units, timestamps, strict validation, explicit family and allowed-use checks | IBM measurements identify **superconducting** devices only, not photonic or trapped-ion parameters [R7–R9, R11] |
| 4. Scientific reference and validation | `stim_memory.py`, `memory_analysis.py`, `literature_benchmark.py`, `idle_coherence.py`, release scripts | Circuit-level synthetic QEC reference, simulation/replay, statistical analysis | A generic rotated surface-code simulation is **not** automatically calibrated to any platform; public IBM repetition-code data cannot validate a large surface-code architecture [R1–R4, R9] |

## Explicit boundaries enforced by code

- `platform_boundaries.backend_family` recognizes named IBM devices as **superconducting**; unrecognized backends fail rather than guessing.
- `platform_boundaries.check_calibration_use` accepts measured, dated IBM characterization for `superconducting` **characterization** or **conditional noise-proxy** analysis. Attempts to use it for `photonic`, `trapped_ion`, or validated hardware logical-failure predictions raise an error.
- `modern_calibration.normalize_backend_properties` adds `hardware_family=superconducting` to recorded IBM hardware fields; `publish_import` writes `ADAPTER_SCOPE.json` with the prohibited uses. No live IBM data are bundled.
- The scenario study writes `outputs/hardware_profiles/PLATFORM_SCOPES.json`. Every result remains `HYPOTHETICAL_UNCALIBRATED`, and numerical results do **not** combine across platforms.
- These are **software claim guards**, not proof that a future scientist cannot accidentally misuse the values elsewhere. The generic core does not ingest calibration data automatically. Future simulation adapters must explicitly adopt these contracts and verify compatible circuits/hardware outcomes.

## Platform-specific input checklist

| Platform | Relevant inputs | Current evidence | Missing for device-level prediction |
|---|---|---|---|
| **Superconducting** | Per-qubit T1, echo T2, gate/readout error and duration, coupling, timestamp | Dated IBM data importer and published hardware study; source-linked historical example and 2026/near-live import tools [R6–R9, R11] | Free-idle Ramsey T2*, matched pulse/syndrome schedule, correlated faults/leakage, calibration at shot time, independent QEC outcomes |
| **Photonic** | Heralded state generation, loss by component, detector efficiency, fusion success, feedforward and storage physics | Hypothetical throughput model; no Xanadu calibration | Component- and protocol-matched photonic error/loss model, encoded resource and decoder measurements (no photonic calibration source bundled) |
| **Trapped ion** | Entangling gates, trap zones, shuttling times/errors, readout, heating and crosstalk | Hypothetical zoned-schedule model, no device calibration | Same-device transport and interaction graph, gate/readout noise, correlated errors and measured QEC outcomes |

## Example checks (no new packages, no remote access)

Run tests and the hypothetical hardware-profile sensitivity:

```zsh
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_platform_boundaries.py" -v
./scripts/commands/RUN_HARDWARE_STUDY.sh
cat outputs/hardware_profiles/PLATFORM_SCOPES.json
```

After **successfully importing** an authentic dated IBM Fez snapshot, the following will print its strictly scoped calibration-use declaration:

```zsh
PYTHONPATH=src python3 -m ftqc_resource_estimator.platform_boundaries \
  --calibration outputs/modern_calibration/ibm_fez/snapshots.json \
  --target-family superconducting --purpose characterization
```

Import one selected snapshot using `--max-snapshots 1` in `scripts/commands/RUN_MODERN_CALIBRATION.sh`. The CLI accepts exactly **one selected snapshot**. For a multi-snapshot import, first select a snapshot explicitly and save its `normalized` object as JSON; it refuses to guess which dated record to use. Deliberately trying `--target-family photonic` rejects the IBM record. The importer, the scope report and the validation contract do **not** mean the surface-code model is fitted or hardware-validated.

## Analysis integrity and interpretation

This project currently demonstrates a generalizable **analysis workflow** with physically distinct adapters, not a universal vendor performance ranking. The original analysis emphasis is on transparent code-distance/reliability decisions and the interface between control constraints and QEC outcomes. External methods, such as Stim circuit generation and PyMatching MWPM, are cited in [REFERENCES.md](../reference/REFERENCES.md); see [LIMITATIONS.md](../validation/LIMITATIONS.md), [PROVENANCE.md](../reference/PROVENANCE_AND_CLAIMS.md) and [EXPERIMENTS_AND_EVIDENCE.md](../validation/EVIDENCE_AND_RESULTS.md) for current evidence claims.
