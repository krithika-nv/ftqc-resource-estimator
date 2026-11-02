"""Original experiment orchestration around public Stim/PyMatching APIs.

No dependency imports at module scope: classical model and audit tests remain
available without optional scientific packages.  Numerical observations are
created ONLY when the external simulators really run.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform

SCHEMA = "ftqc.rotated_surface_memory.v1"
NOISE_PROFILE = "stim_uniform_circuit_noise_v1"
EXPERIMENT = "memory_fixed_rounds"
DECODER = "pymatching_mwpm_from_decomposed_dem"


def _parse_distances(values: str) -> list[int]:
    result = [int(v.strip()) for v in values.split(",")]
    if len(set(result)) != len(result) or any(v < 3 or v % 2 == 0 for v in result):
        raise ValueError("distances must be distinct odd integers >=3")
    return result


def _parse_errors(values: str) -> list[float]:
    result = [float(v.strip()) for v in values.split(",")]
    if not result or len(set(result)) != len(result) or any(not 0 <= p < 1 for p in result):
        raise ValueError("physical errors must be unique probabilities in [0,1)")
    return result


def simulate_memory(stim, pymatching, *, distance: int, physical_error: float,
                    shots: int, seed: int, rounds: int = 9, basis: str = "X", check_shots: int = 16) -> dict:
    """Use rotated surface memory circuits at a FIXED number of rounds across distances.

    Noise convention: the same numerical p is assigned independently to all
    four noise knobs below, not fitted to hardware. MWPM uses an error model
    from *that same circuit*.  A per-shot API check guards batch shape/order.
    """
    if distance < 3 or distance % 2 != 1 or rounds < 1 or shots < 1 or not 0 <= physical_error < 1:
        raise ValueError("distance odd >=3, rounds/shots positive, p in [0,1)")
    if basis not in {"X", "Z"}:
        raise ValueError("basis must be X or Z")
    circuit = stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis.lower()}", distance=distance,
        rounds=rounds, after_clifford_depolarization=physical_error,
        before_round_data_depolarization=physical_error,
        before_measure_flip_probability=physical_error,
        after_reset_flip_probability=physical_error,
    )
    model = circuit.detector_error_model(decompose_errors=True)
    detector_samples, actual_observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True,
    )
    if detector_samples.shape[0] != shots or actual_observables.shape != (shots, 1):
        raise RuntimeError("unexpected Stim detector/observable shapes")
    if physical_error == 0:
        # A zero-noise DEM need not contain an observable edge, so a MWPM graph
        # can legitimately have zero tracked observables. This is a separate
        # ideal-circuit control, NOT a scored noisy-decoding experiment.
        if detector_samples.any() or actual_observables.any():
            raise RuntimeError("noiseless surface-code memory must not fail")
        predictions = actual_observables.copy()  # exactly all zero
        checked = 0
        actual_decoder = "noiseless_identity_control"
    else:
        decoder = pymatching.Matching.from_detector_error_model(model)
        predictions = decoder.decode_batch(detector_samples)
        if actual_observables.shape != predictions.shape:
            raise RuntimeError("unexpected PyMatching logical observable shape")
        checked = min(shots, max(0, check_shots))
        for i in range(checked):
            if not (decoder.decode(detector_samples[i]) == predictions[i]).all():
                raise RuntimeError("per-shot and batch MWPM outputs disagree")
        actual_decoder = DECODER
    failures = int((predictions != actual_observables).any(axis=1).sum())
    trivial_decoder_failures = int(actual_observables[:,0].sum())  # always-predict-no-flip control
    return {
        "code_family": "rotated_surface", "experiment": EXPERIMENT, "observable_basis": basis,
        "physical_error": physical_error, "distance": distance, "rounds": rounds,
        "shots": shots, "failures": failures, "trivial_decoder_failures": trivial_decoder_failures, "seed": seed,
        "noise_profile": NOISE_PROFILE, "decoder": actual_decoder,
        "circuit_sha256": sha256(str(circuit).encode()).hexdigest(),
        "detector_model_sha256": sha256(str(model).encode()).hexdigest(),
        "detectors": int(circuit.num_detectors), "observables": int(circuit.num_observables),
        "batch_single_agreement_checked_shots": checked,
    }


def produce_data(*, distances: list[int], physical_errors: list[float], shots: int,
                 seed: int = 20261025, rounds: int = 9, basis: str = "X") -> dict:
    try:
        import stim
        import pymatching
        import numpy
    except ImportError as exc:
        raise RuntimeError(
            "Stim/PyMatching/numpy unavailable. Install the optional 'analysis' dependencies "
            "and rerun; no measurements were produced."
        ) from exc
    if shots < 1 or not distances or not physical_errors:
        raise ValueError("distances/errors nonempty; shots >=1")
    obs = []
    for i, (d,p) in enumerate((d,p) for p in physical_errors for d in distances):
        result = simulate_memory(stim,pymatching,distance=d,physical_error=p,shots=shots,
                                 seed=seed+i,rounds=rounds,basis=basis)
        obs.append(result)
        print(f"d={d}, p={p:.6g}, failures={result['failures']}/{shots}")
    return {
        "schema": SCHEMA,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "ftqc_resource_estimator.stim_memory",
        "software": {"stim": stim.__version__, "pymatching": pymatching.__version__,
                     "numpy": numpy.__version__, "python": platform.python_version()},
        "methods": {
            "experiment": EXPERIMENT, "code": "stim surface_code:rotated_memory_"+basis.lower(),
            "basis": basis, "rounds": rounds, "rounds_rule": "fixed number of syndrome rounds across all distances; no interpolation",
            "noise_profile": NOISE_PROFILE,
            "noise_knobs": ["after_clifford_depolarization", "before_round_data_depolarization",
                            "before_measure_flip_probability", "after_reset_flip_probability"],
            "noise_knob_rule": "All four independently set to the numeric physical_error value in each observation",
            "decoder": DECODER, "decoder_model": "circuit.detector_error_model(decompose_errors=True)",
            "failure": "MWPM-predicted logical flip disagrees with Stim-sampled logical observable",
            "confidence": "two-sided 95% Wilson binomial interval in downstream analysis",
            "seed_rule": "seed_base + enumeration index; RNG streams may differ across platforms",
            "seed_base": seed,
            "caveat": "Rotated surface-code memory, NOT logical gates, GKP photonics, hardware predictions, or thresholds",
        },
        "observations": obs,
    }


def replay_audit(manifest: dict) -> None:
    """Recreate the same circuits and samples in the SAME software environment.

    This protects against stale/accidentally edited result files; it is not
    independent evidence about whether the simulated noise matches hardware.
    """
    import stim
    import pymatching
    if manifest.get("schema") != SCHEMA:
        raise ValueError("wrong schema")
    if (manifest.get("software",{}).get("stim") != stim.__version__ or
        manifest.get("software",{}).get("pymatching") != pymatching.__version__):
        raise ValueError("replay requires exact Stim/PyMatching versions")
    for saved in manifest.get("observations", []):
        actual = simulate_memory(stim, pymatching, distance=saved["distance"],
            rounds=saved["rounds"], physical_error=saved["physical_error"],
            shots=saved["shots"], seed=saved["seed"], basis=saved["observable_basis"])
        for field in ("failures", "trivial_decoder_failures", "circuit_sha256",
                      "detector_model_sha256", "detectors", "observables", "rounds"):
            if actual[field] != saved.get(field):
                raise ValueError(f"Stim replay mismatch at d={saved['distance']}: {field}")
    if not manifest.get("observations"):
        raise ValueError("no observations to replay")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sample real Stim rotated surface-code memory and decode with PyMatching")
    parser.add_argument("--distances", default="3,5,7")
    parser.add_argument("--physical-errors", default="0,0.003,0.005")
    parser.add_argument("--shots", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20261025)
    parser.add_argument("--rounds", type=int, default=9)
    parser.add_argument("--basis", choices=["X", "Z"], default="X")
    parser.add_argument("--output", type=Path, default=Path("outputs/stim_memory/observations.json"))
    parser.add_argument("--replay",type=Path,help="Verify the saved counts and circuit hashes in the same installed library versions")
    args=parser.parse_args(argv)
    if args.replay:
        replay_audit(json.loads(args.replay.read_text(encoding="utf-8")))
        print("PASS: all recorded observations replayed with matching seeds, counts and circuit hashes")
        return 0
    results = produce_data(distances=_parse_distances(args.distances),
                           physical_errors=_parse_errors(args.physical_errors),
                           shots=args.shots,seed=args.seed,rounds=args.rounds,basis=args.basis)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {len(results['observations'])} real decoded surface-memory observations to {args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
