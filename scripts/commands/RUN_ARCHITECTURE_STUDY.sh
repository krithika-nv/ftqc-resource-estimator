#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -m ftqc_resource_estimator.study --config examples/architecture_scenarios.json --output-dir outputs/architecture_study
python3 examples/validate_repetition.py
python3 examples/simulate_source_queue.py
printf '\nStudy artifacts generated in outputs/. Read README.md for model limitations.\n'
