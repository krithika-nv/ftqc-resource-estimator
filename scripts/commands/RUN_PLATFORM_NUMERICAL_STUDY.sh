#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH="${PWD}/src${PYTHONPATH:+:$PYTHONPATH}"
if [[ $# -eq 0 ]]; then
  echo 'Usage:' >&2
  echo '  ./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh neutral-schedule --geometry-json examples/neutral_atom_geometry_illustrative.json --output-dir outputs/neutral_atom_schedule' >&2
  echo '  ./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh quera --normalized-counts /path/to/verified_counts.csv --output-dir outputs/quera_purity' >&2
  echo '  ./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh xanadu-gkp --density-npy /path/to/verified_density.npy --output-dir outputs/gkp_reconstruction' >&2
  echo '  ./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh xanadu-aurora --workbook /path/to/aurora_plot.xlsx --sheet SHEET --x-column X --y-column Y --unit UNIT --output-dir outputs/aurora_figure' >&2
  echo '  ./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh quantinuum --trusted-csv /path/to/source_verified.csv --output-dir outputs/helios' >&2
  echo '  ./scripts/commands/RUN_PLATFORM_NUMERICAL_STUDY.sh ibm --verified-flat-csv /path/to/verified.csv --output-dir outputs/ibm_heldout' >&2
  exit 2
fi
MODE="$1";shift
case "$MODE" in
  neutral-schedule) python3 -m ftqc_resource_estimator.neutral_atom_schedule "$@" ;;
  quera) python3 -m ftqc_resource_estimator.quera_analysis "$@" ;;
  xanadu-gkp) python3 -m ftqc_resource_estimator.xanadu_analysis gkp "$@" ;;
  xanadu-aurora) python3 -m ftqc_resource_estimator.xanadu_analysis aurora "$@" ;;
  quantinuum) python3 -m ftqc_resource_estimator.quantinuum_analysis "$@" ;;
  ibm) python3 -m ftqc_resource_estimator.ibm_hardware_analysis "$@" ;;
  *) echo "Unknown study: $MODE" >&2;exit 2;;
esac
