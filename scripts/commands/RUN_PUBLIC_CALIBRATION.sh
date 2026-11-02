#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
# No internet or extra dependencies for bundled source-traceable measured subset.
# Pass --input <your props_manila.json> --raw to validate the downloaded original.
PYTHONPATH=src python3 -m ftqc_resource_estimator.public_calibration "$@"
