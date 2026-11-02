#!/usr/bin/env bash
set -euo pipefail
# Run from repository root. Never substitute 2024 data when 2026 download fails.
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH="${PWD}/src${PYTHONPATH:+:${PYTHONPATH}}"
python3 -m ftqc_resource_estimator.modern_calibration "$@"
