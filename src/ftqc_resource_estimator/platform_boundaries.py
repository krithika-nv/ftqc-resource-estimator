"""Cross-platform evidence-use contracts, separate from all resource arithmetic.

This module does NOT convert IBM characterization into vendor logical fidelity.
It guards the *claim* and family attached to a calibration record.
Importers remain source-specific and the mathematical core stays hardware-neutral.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

FAMILIES = frozenset({"photonic", "superconducting", "trapped_ion", "neutral_atom"})
SUPPORTED_IBM_PREFIXES = ("ibm_", "ibmq_")
ALLOWED_PURPOSES = frozenset({"characterization", "conditional_noise_proxy"})


def backend_family(backend_name: str) -> str:
    """Recognize *only* IBM superconducting backends with an explicit name.

    Do not infer a hardware family from generic numbers like a T1 or gate duration.
    """
    if not isinstance(backend_name, str) or not backend_name.strip():
        raise ValueError("explicit backend_name is required")
    if backend_name.startswith(SUPPORTED_IBM_PREFIXES):
        return "superconducting"
    raise ValueError("unrecognized backend: no supported hardware-family mapping")


def check_calibration_use(calibration: dict, *, target_family: str,
                          purpose: str = "characterization") -> dict:
    """Fail closed on cross-platform use or premature hardware-validation claims.

    A successful conditional proxy is permission to EXPLORE assumptions, not an
    independently validated prediction. Future validation will require a new,
    audited workflow with matched device/circuit/calibration/outcome evidence.
    """
    if target_family not in FAMILIES:
        raise ValueError(f"unsupported target hardware family: {target_family!r}")
    if purpose not in ALLOWED_PURPOSES:
        raise ValueError("unsupported evidence purpose; verified hardware prediction "
                         "requires separate matched experimental validation")
    if not isinstance(calibration, dict):
        raise ValueError("calibration record must be a mapping")
    name = calibration.get("backend_name")
    source_family = backend_family(name)
    declared_family = calibration.get("hardware_family", source_family)
    if declared_family != source_family:
        raise ValueError("calibration hardware_family conflicts with source backend")
    if target_family != source_family:
        raise ValueError(f"cross-platform calibration rejected: {name} is "
                         f"{source_family}, not {target_family}")
    timestamp = calibration.get("calibration_timestamp_utc")
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError("dated calibration_timestamp_utc required")
    if calibration.get("data_classification") != "MEASURED_DEVICE_CHARACTERIZATION_ONLY":
        raise ValueError("record is not certified as measured characterization")
    # A caller must not turn this conditional use into a validated logical-error claim.
    if calibration.get("logical_error_hardware_prediction_validated") is not False:
        raise ValueError("unexpected logical-prediction validation field")
    return {
        "backend_name": name,
        "calibration_timestamp_utc": timestamp,
        "source_hardware_family": source_family,
        "permitted_target_family": target_family,
        "permitted_purpose": purpose,
        "evidence_class": "measured_device_characterization",
        "physical_calibration_of_ftqc_model": False,
        "hardware_logical_error_prediction_validated": False,
        "cross_platform_generalization_permitted": False,
        "note": ("A source-characterized superconducting device is usable for "
                 "characterization or conditional, model-dependent noise proxies only. "
                 "It cannot validate photonic/ion hardware or surface-code logical fidelity."),
    }


def scenario_scope(family: str) -> dict:
    """Metadata-only adapter boundary; no performance-unit conversion."""
    if family not in FAMILIES:
        raise ValueError(f"unsupported scenario family: {family}")
    return {
        "hardware_family": family,
        "scenario_model_status": "HYPOTHETICAL_UNCALIBRATED",
        "device_calibration_used": False,
        "logical_error_hardware_prediction_validated": False,
        "can_rank_against_other_families": False,
        "resource_units_comparable_across_families": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit proposed use of measured calibration")
    parser.add_argument("--calibration", type=Path, required=True,
                        help="normalized JSON or modern-calibration snapshots.json")
    parser.add_argument("--target-family", choices=sorted(FAMILIES), required=True)
    parser.add_argument("--purpose", default="characterization")
    args = parser.parse_args(argv)
    obj = json.loads(args.calibration.read_text())
    if isinstance(obj, list):
        if len(obj) != 1 or "normalized" not in obj[0]:
            parser.error("select exactly one imported snapshot before checking evidence use")
        obj = obj[0]["normalized"]
    result = check_calibration_use(obj, target_family=args.target_family, purpose=args.purpose)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
