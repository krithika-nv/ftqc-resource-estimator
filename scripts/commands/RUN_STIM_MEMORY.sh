#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -c 'import stim, pymatching, numpy; print("Scientific dependencies OK:",stim.__version__,pymatching.__version__,numpy.__version__)' || {
  echo 'MISSING REAL STIM/PYMATCHING: run python3 -m pip install -e ".[analysis]" in an appropriate Python environment. No synthetic results substituted.' >&2
  exit 1
}
python3 -m ftqc_resource_estimator.stim_memory --distances 3,5,7 --rounds 9 --physical-errors 0,0.003,0.005 --shots 20000 --basis X --output outputs/stim_memory/observations.json
python3 -m ftqc_resource_estimator.stim_memory --replay outputs/stim_memory/observations.json
python3 -m ftqc_resource_estimator.memory_analysis --observations outputs/stim_memory/observations.json --physical-error 0.003 --rounds 9 --distances 3,5,7 --output-dir outputs/stim_memory/analysis
python3 scripts/tools/verify_scientific_release.py
printf '\nREAL Stim+PyMatching results: outputs/stim_memory/analysis/MEMORY_REPORT.md\n'
printf 'Verified release evidence: outputs/stim_memory/VALIDATED_RUN.json\n' 
