"""Scientific release gate for the user-requested distance 7/9 follow-up.

Requires the actual installed Stim and PyMatching backends; replays the exact
manifest on this machine, checks the generated analyses, and only then writes
VERIFIED_FOLLOWUP.json. This is NOT independent hardware validation.
"""
from __future__ import annotations
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ftqc_resource_estimator.stim_memory import SCHEMA, replay_audit
from ftqc_resource_estimator.memory_analysis import (
    compare_memory, load_memory_scenarios, validate_stim_manifest)

FOLLOWUP = ROOT / "outputs/stim_memory/followup"


def audit_followup(manifest: dict, *, baseline_csv: Path, sensitivity_csv: Path) -> dict:
    """Offline numerical cross-check. Does not establish source authenticity."""
    if manifest.get("schema") != SCHEMA or len(manifest.get("observations", [])) != 2:
        raise ValueError("follow-up must contain exactly two real-backend records")
    if (manifest.get("methods", {}).get("seed_base") != 20261025 or
            manifest.get("methods", {}).get("basis") != "X" or
            manifest.get("methods", {}).get("rounds") != 9):
        raise ValueError("follow-up protocol or seed base mismatch")
    by_d = validate_stim_manifest(manifest, basis="X", physical_error=.003,
                                   rounds=9, distances=(7, 9))
    if set((x["distance"], x["physical_error"]) for x in manifest["observations"]) != {(7,.003),(9,.003)}:
        raise ValueError("follow-up missing required distance/error pair")
    if [(x["distance"],x["seed"]) for x in manifest["observations"]] != [(7,20261025),(9,20261026)]:
        raise ValueError("follow-up seed ordering changed")
    if any(x["shots"] != 20000 for x in by_d.values()):
        raise ValueError("follow-up requires 20,000 shots per distance")
    configs = [
        (ROOT / "examples/memory_architecture_scenarios.json", baseline_csv),
        (ROOT / "examples/memory_control_cost_sensitivity.json", sensitivity_csv),
    ]
    feasible_counts = []
    for path, csv_path in configs:
        workload, scenarios = load_memory_scenarios(path)
        expected = compare_memory(manifest, scenarios, workload,
                                  basis="X", physical_error=.003, rounds=9, distances=(7,9))
        with csv_path.open(newline="", encoding="utf-8") as f:
            actual = list(csv.DictReader(f))
        if len(actual) != len(expected):
            raise ValueError(f"missing scenario rows: {csv_path}")
        for x, y in zip(expected, actual):
            for key, val in x.items():
                if key not in y:
                    raise ValueError(f"missing analysis field {key}: {csv_path}")
                if isinstance(val,bool):
                    if y[key] != str(val):
                        raise ValueError(f"boolean analysis mismatch: {key}")
                elif isinstance(val,(float,int)):
                    if abs(float(y[key])-float(val)) > 1e-10*max(1,abs(val)):
                        raise ValueError(f"numeric analysis mismatch: {key}")
                elif y[key] != str(val):
                    raise ValueError(f"analysis field mismatch: {key}")
        feasible_counts.append(sum(x["feasible_upper95"] for x in expected))
    return {
        "observations":2,
        "total_shots":40000,
        "distances":[7,9],
        "p":.003,
        "original_config_feasible_rows":feasible_counts[0],
        "controller_cost_sensitivity_feasible_rows":feasible_counts[1],
        "d7_failures":by_d[7]["failures"],
        "d9_failures":by_d[9]["failures"],
    }


def verify() -> dict:
    try:
        import stim
        import pymatching
        import numpy
    except ImportError as exc:
        raise RuntimeError("Real Stim/PyMatching/NumPy required: no simulated results substituted") from exc
    path = FOLLOWUP / "observations.json"
    raw = path.read_bytes()
    manifest = json.loads(raw)
    software=manifest.get("software",{})
    if software.get("stim") != stim.__version__ or software.get("pymatching") != pymatching.__version__:
        raise ValueError("Stim/PyMatching versions changed; cannot replay this manifest")
    result = audit_followup(
        manifest,
        baseline_csv=FOLLOWUP / "analysis/memory_tradeoffs.csv",
        sensitivity_csv=FOLLOWUP / "control_cost_analysis/memory_tradeoffs.csv",
    )
    replay_audit(manifest)
    verification = {
        "status":"PASSED actual Stim/PyMatching same-environment replay and two analyses",
        "verified_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "observation_sha256":sha256(raw).hexdigest(),
        "stim_version":stim.__version__,
        "pymatching_version":pymatching.__version__,
        "numpy_version":numpy.__version__,
        **result,
        "scope":"nine-round rotated surface-code memory; uncalibrated controller-cost sensitivity"
    }
    dest=FOLLOWUP / "VERIFIED_FOLLOWUP.json"
    dest.write_text(json.dumps(verification,indent=2)+"\n", encoding="utf-8")
    return verification

if __name__ == "__main__":
    try:
        result=verify()
    except Exception as exc:
        print(f"FOLLOW-UP SCIENTIFIC GATE FAILED: {exc}",file=sys.stderr)
        raise SystemExit(1)
    print(f"FOLLOW-UP SCIENTIFIC GATE PASSED: {result['total_shots']} real simulator trials, "
          f"{result['controller_cost_sensitivity_feasible_rows']} controller-cost feasible rows")
