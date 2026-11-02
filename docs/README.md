# Documentation

Start with the [project README](../README.md). The [roadmap](../ROADMAP.md) tracks open work. Documentation here separates executed software/simulations, measured-device evidence, and unvalidated FTQC extrapolations.

## Run and reproduce

- [Running and reproducing](guides/RUNNING_AND_REPRODUCING.md): commands, profiles (`ci`, `science`, `ibm`, `evidence`, `all`), inputs and outputs.
- [GitHub automation](guides/GITHUB_AUTOMATION.md): workflows, source retrieval, evidence publication, caches and retention.

## Architecture and methods

- [Analysis methods](methods/METHODS.md): mathematical models, Pareto studies and experiment protocols.
- [Platform and evidence boundaries](methods/PLATFORM_BOUNDARIES.md): hardware-native scope and assumptions.
- [Idle-noise method and provenance](methods/IDLE_NOISE_METHOD.md): published inputs versus simulated controller assumptions.

## Hardware calibration

- [Calibration requirements](hardware/CALIBRATION.md): physical parameters, timestamps, uncertainty and importing procedures.
- [Dataset sources and adapters](hardware/HARDWARE_DATA_GUIDE.md): data acquisition, formats, source restrictions.
- [IBM Fez QEC validation](hardware/IBM_FEZ_VALIDATION.md): original shots, QASM mapping, decoding and holdout limitations.

## Results and scientific acceptance

- [Evidence and experiment results](validation/EVIDENCE_AND_RESULTS.md): source-linked implemented results and limitations.
- [Progress inventory](validation/PROJECT_PROGRESS.md): engineering components versus scientific gates.
- [Four-platform acceptance contract](validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.md): strict, independently assessed evidence gates.
- [Platform-specific numerical validation](validation/PLATFORM_NUMERICAL_VALIDATION.md): numerical schemas and platform limitations.
- [Limitations](validation/LIMITATIONS.md): authoritative scope and calibration boundaries.

## Reference

- [Project concepts and knowledge map](reference/PROJECT_CONCEPTS.md): QEC, architecture, physics and terminology.
- [Provenance and claim checks](reference/PROVENANCE_AND_CLAIMS.md): data attribution and figures.
- [Bibliography](reference/REFERENCES.md): cited sources.
