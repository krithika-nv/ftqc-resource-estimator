# Hardware-aware FTQC architecture: three **illustrative** adapters

**NOT a scientific ranking of photonic, superconducting and trapped-ion platforms.**
No hardware-calibrated fidelity, gate noise, photonic GKP code, loss-to-error mapping, leakage, decoder runtime, or transport topology is implemented.

The same workload labels structure three *different* simplified cost analyses; their outcome numbers are not an apples-to-apples comparison.

The accompanying `PLATFORM_SCOPES.json` marks every scenario as hypothetical, uncalibrated and not cross-platform comparable. The separately imported IBM records apply only to superconducting characterization and have NOT been injected into these hypothetical scheduling profiles.

Common synthetic demand: 4 logical storage patches; 10 memory windows × 5 nominal rounds; d=5.

## Results within each platform (hypothetical input values)

### Photonic

| Scenario | Modeled runtime (µs) | Bottleneck | Accounting unit |
|---|---:|---|---|
| illustrative optical delivery - fewer sources | 124.494 | supply | heralded_resource_state_equivalent |
| illustrative optical delivery - more sources | 70.000 | measurement_and_feedforward | heralded_resource_state_equivalent |

### Superconducting

| Scenario | Modeled runtime (µs) | Bottleneck | Accounting unit |
|---|---:|---|---|
| illustrative fast readout | 77.500 | specified_serial_gate_and_readout_schedule | nominal_data_and_syndrome_qubits |
| illustrative slow readout | 127.500 | specified_serial_gate_and_readout_schedule | nominal_data_and_syndrome_qubits |

### Trapped Ion

| Scenario | Modeled runtime (µs) | Bottleneck | Accounting unit |
|---|---:|---|---|
| illustrative 2 gate zones | 14550.000 | serialized_zoned_gate_and_transport_schedule | nominal_data_and_syndrome_ions |
| illustrative 4 gate zones | 10050.000 | serialized_zoned_gate_and_transport_schedule | nominal_data_and_syndrome_ions |

## Interpretation and limitations

- **Photonic:** independent heralding and path transmissions; a delivered abstract resource does not imply a usable GKP grid state. Mean supply and measurement times are overlapped optimistically; no queue or finite-buffer bottleneck.
- **Superconducting:** assumes ideal layer parallelism, explicit serialized layer counts and independent readout. No connectivity, crosstalk, leakage or decoherence calibrated.
- **Trapped ion:** gate/transport operations are serialized in abstract parallel zones; no explicit ion geometry, heating or scheduling graph.
- **None:** a value for `runtime_us` predicts actual machine latency. The sample scenario values are hypothetical teaching/analysis inputs, not manufacturer specifications.
- **Surface-code decoder:** Stim/PyMatching output, when available, is an *un-calibrated shared circuit reference* and cannot be injected as any of these platforms’ failure rates without a matched noise/channel/schedule validation.

## Reproduce

`PYTHONPATH=src python3 -m ftqc_resource_estimator.hardware_study --config examples/hardware_profiles.json --output-dir outputs/hardware_profiles`

## Source context

- Stim QEC circuit experiment: https://github.com/quantumlib/Stim
- PyMatching decoding: https://pymatching.readthedocs.io/en/stable/
- Xanadu photonic FTQC Blueprint: https://doi.org/10.22331/q-2021-02-04-392
- Fowler et al. surface code: https://doi.org/10.1103/PhysRevA.86.032324

Model arithmetic, organization, tests and analyses are independent implementations; no vendor implementation has been copied.
