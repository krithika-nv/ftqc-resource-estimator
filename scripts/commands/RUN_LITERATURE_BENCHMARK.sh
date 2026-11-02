#!/usr/bin/env bash
# Real Stim/PyMatching distance-scaled rounds benchmark matched to Riverlane's published tutorial.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -c 'import stim,pymatching,numpy; print("REAL backends",stim.__version__,pymatching.__version__,numpy.__version__)'
python3 -m ftqc_resource_estimator.literature_benchmark "$@"
