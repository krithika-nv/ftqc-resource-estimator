#!/usr/bin/env bash
# Use the configured Python interpreter from your zsh PATH; never a hidden local env.
# --preview-only requires no scientific backend and DOES NOT assess feasibility.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH=src
python3 -m ftqc_resource_estimator.idle_coherence "$@"
