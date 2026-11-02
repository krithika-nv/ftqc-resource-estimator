#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
case "${1:-}" in
  aurora) url=https://github.com/XanaduAI/xanadu-aurora-data.git; name=xanadu_aurora ;;
  gkp) url=https://github.com/XanaduAI/xanadu-gkp-data.git; name=xanadu_gkp ;;
  helios) url=https://github.com/Quantinuum/Helios-paper-data.git; name=quantinuum_helios ;;
  ion-specs) url=https://github.com/Quantinuum/quantinuum-hardware-specifications.git; name=quantinuum_specifications ;;
  quera-code) url=https://github.com/oscars47/RydSFF.git; name=quera_aquila_2026_code ;;
  *) echo "Usage: $0 {aurora|gkp|helios|ion-specs|quera-code}" >&2; exit 2;;
esac
mkdir -p data/external_hardware
if [[ -e "data/external_hardware/$name" ]]; then
  echo "Already present; update manually after reviewing upstream: data/external_hardware/$name"; exit 0
fi
# Download small public SOURCE repositories only. Large raw optical/neutral-atom datasets are separate.
git clone --depth=1 "$url" "data/external_hardware/$name"
echo "Downloaded source repository; this does NOT download all external raw experiment archives."
