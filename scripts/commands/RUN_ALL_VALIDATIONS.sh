#!/usr/bin/env bash
# Run hardware sensitivity and independent QEC experiments.
# For the entire Track A including architecture/Pareto, use --profile science.
# Unit tests are run once by the central automation runner or separately by CI.
# FAIL CLOSED: missing Stim/PyMatching must not produce a success message.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
bash scripts/commands/RUN_HARDWARE_STUDY.sh
bash scripts/commands/RUN_PUBLISHED_READOUT_AUDIT.sh
bash scripts/commands/RUN_PUBLIC_CALIBRATION.sh
bash scripts/commands/RUN_STIM_MEMORY.sh
bash scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh
bash scripts/commands/RUN_LITERATURE_BENCHMARK.sh
bash scripts/commands/RUN_CONTROLLER_CAPACITY.sh
bash scripts/commands/RUN_IDLE_COHERENCE_STUDY.sh
printf '\nALL REPRODUCIBILITY GATES PASSED: local mathematics + real Stim/PyMatching experiment.\n'
