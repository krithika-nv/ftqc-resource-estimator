#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -m ftqc_resource_estimator.hardware_study --config examples/hardware_profiles.json --output-dir outputs/hardware_profiles
printf '\nThese are hypothetical hardware-profile outputs; they do NOT validate the physical devices or the external Stim backend.\n'
