#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -m ftqc_resource_estimator.published_readout_evidence --output-dir outputs/published_readout
