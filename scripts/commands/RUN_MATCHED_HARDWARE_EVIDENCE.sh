#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH="${PWD}/src${PYTHONPATH:+:${PYTHONPATH}}"
# The IBM archive must be downloaded and checksum-verified by the owner.
python3 -m ftqc_resource_estimator.matched_hardware_evidence "$@"
