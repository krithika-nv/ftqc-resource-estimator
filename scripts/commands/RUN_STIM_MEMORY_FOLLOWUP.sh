#!/usr/bin/env bash
# Reproduce the independently seeded d7/d9 study and two architectural analyses.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -c 'import stim, pymatching, numpy; print("REAL scientific dependencies:",stim.__version__,pymatching.__version__,numpy.__version__)'
python3 -m ftqc_resource_estimator.stim_memory \
  --distances 7,9 --rounds 9 --physical-errors 0.003 --shots 20000 \
  --seed 20261025 --basis X --output outputs/stim_memory/followup/observations.json
python3 -m ftqc_resource_estimator.stim_memory \
  --replay outputs/stim_memory/followup/observations.json
python3 -m ftqc_resource_estimator.memory_analysis \
  --observations outputs/stim_memory/followup/observations.json \
  --physical-error 0.003 --rounds 9 --distances 7,9 \
  --config examples/memory_architecture_scenarios.json \
  --output-dir outputs/stim_memory/followup/analysis
python3 -m ftqc_resource_estimator.memory_analysis \
  --observations outputs/stim_memory/followup/observations.json \
  --physical-error 0.003 --rounds 9 --distances 7,9 \
  --config examples/memory_control_cost_sensitivity.json \
  --output-dir outputs/stim_memory/followup/control_cost_analysis \
  --no-logical-failure-plot
python3 scripts/tools/verify_scientific_followup.py
printf '\nFollow-up and controller sensitivity verified. Original 3/5/7 baseline remains unchanged.\n'
