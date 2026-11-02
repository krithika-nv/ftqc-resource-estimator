#!/usr/bin/env bash
# Scientific dependencies intentionally not needed: no fake Stim results created.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -m unittest discover -s tests -v
bash scripts/commands/RUN_PUBLISHED_READOUT_AUDIT.sh
python3 -m ftqc_resource_estimator.sample_planning --target-failure 0.1 --logical-qubits 4 --memory-windows 10 --shots 20000
printf '\nLOCAL CHECKS FINISHED. This is NOT a Stim/PyMatching scientific release.\n'
