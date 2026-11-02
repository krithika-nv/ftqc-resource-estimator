#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
mkdir -p data/public_calibrations
url='https://raw.githubusercontent.com/Qiskit/qiskit-ibm-runtime/main/qiskit_ibm_runtime/fake_provider/backends/manila/props_manila.json'
# Fetch the *actual original* JSON on a networked machine. Never substitute a fixture.
curl --fail --location --show-error --silent "$url" --output data/public_calibrations/props_manila.json
PYTHONPATH=src python3 -m ftqc_resource_estimator.public_calibration \
  --input data/public_calibrations/props_manila.json --raw \
  --output-dir outputs/public_calibration_from_raw
