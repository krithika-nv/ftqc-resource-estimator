"""Analysis of *matched* surface-code MEMORY measurements, not FT gate costs.

Statistical and architectural assumptions are deliberately visible. Synthetic
JSON test fixtures must never be presented as completed Stim experiments.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path

from .reliability import wilson, cumulative_failure
from .stim_memory import SCHEMA, NOISE_PROFILE, EXPERIMENT, DECODER
from .sample_planning import allowed_memory_error, minimum_shots_if_zero_failures, zero_failures_upper95


@dataclass(frozen=True)
class MemoryScenario:
    name: str
    cycle_us: float
    decode_us_per_window: float
    reserve_fraction: float
    controller_site_equivalents_per_patch: int = 0
    def __post_init__(self):
        if not self.name or self.cycle_us <= 0 or self.decode_us_per_window < 0 or self.reserve_fraction < 0:
            raise ValueError("invalid memory scenario")
        if not all(math.isfinite(v) for v in (self.cycle_us,self.decode_us_per_window,self.reserve_fraction)):
            raise ValueError("scenario must use finite parameters")
        if (not isinstance(self.controller_site_equivalents_per_patch, int) or
                isinstance(self.controller_site_equivalents_per_patch, bool) or
                self.controller_site_equivalents_per_patch < 0):
            raise ValueError("controller overhead must be a nonnegative integer")


@dataclass(frozen=True)
class MemoryWorkload:
    logical_qubits: int
    memory_windows: int
    target_failure: float
    def __post_init__(self):
        if not isinstance(self.logical_qubits,int) or self.logical_qubits < 1 or not isinstance(self.memory_windows,int) or self.memory_windows < 1:
            raise ValueError("qubits and windows must be positive integers")
        if not 0 < self.target_failure < 1:
            raise ValueError("target_failure must be in (0,1)")


def validate_stim_manifest(obj: dict, *, basis="X", physical_error: float, rounds: int,
                           distances: tuple[int,...]) -> dict[int,dict]:
    """Fail closed on missing/mismatched provenance or circuits.

    This checks consistency and provenance fields; it does not cryptographically
    attest that external libraries really ran. Validate independently in CI.
    """
    if obj.get("schema") != SCHEMA or obj.get("generator") != "ftqc_resource_estimator.stim_memory":
        raise ValueError("not a recognized Stim-generated surface memory manifest")
    sw=obj.get("software",{})
    if not all(sw.get(k) for k in ("stim","pymatching","numpy","python")):
        raise ValueError("missing simulator software provenance")
    m=obj.get("methods",{})
    if (m.get("experiment") != EXPERIMENT or m.get("basis") != basis or
        m.get("noise_profile") != NOISE_PROFILE or m.get("decoder") != DECODER or
        m.get("rounds") != rounds or m.get("rounds_rule") != "fixed number of syndrome rounds across all distances; no interpolation" or
        m.get("seed_rule") != "seed_base + enumeration index; RNG streams may differ across platforms"):
        raise ValueError("simulator methods do not match memory benchmark")
    expected_knobs={"after_clifford_depolarization","before_round_data_depolarization",
                    "before_measure_flip_probability","after_reset_flip_probability"}
    if set(m.get("noise_knobs",[]))!= expected_knobs:
        raise ValueError("noise knobs not matched")
    by_d = {}
    for row in obj.get("observations",[]):
        if row.get("physical_error") != physical_error or row.get("observable_basis") != basis:
            continue
        d=row.get("distance")
        if d not in distances:
            continue
        if d in by_d:
            raise ValueError("duplicate experiment at a requested distance; no silent pooling")
        required={"code_family":"rotated_surface","experiment":EXPERIMENT,"rounds":rounds,
                  "noise_profile":NOISE_PROFILE,"decoder":(DECODER if physical_error>0 else "noiseless_identity_control"),"observables":1}
        if any(row.get(k)!=v for k,v in required.items()):
            raise ValueError("experiment attributes do not match logical MEMORY event")
        if not isinstance(row.get("shots"),int) or not isinstance(row.get("failures"),int):
            raise ValueError("invalid shot counts")
        wilson(row["failures"],row["shots"])
        if not isinstance(row.get("trivial_decoder_failures"),int) or not 0 <= row["trivial_decoder_failures"] <= row["shots"]:
            raise ValueError("missing always-predict-no-flip independent control")
        if not isinstance(row.get("seed"),int) or row.get("detectors",0)<=0 or not row.get("circuit_sha256") or not row.get("detector_model_sha256"):
            raise ValueError("missing circuit hashes/seed/detector evidence")
        if row.get("batch_single_agreement_checked_shots",0) < (min(row["shots"],16) if physical_error>0 else 0):
            raise ValueError("batch/single decoder cross-check missing")
        if physical_error==0 and row["failures"]!=0:
            raise ValueError("noiseless control unexpectedly failed")
        by_d[d]=row
    if set(by_d)!=set(distances):
        raise ValueError(f"missing EXACT observations: {set(distances)-set(by_d)}; no interpolation")
    return by_d


def compare_memory(obj: dict, scenarios: list[MemoryScenario], workload: MemoryWorkload,
                   *, basis: str, physical_error: float, rounds: int, distances: tuple[int,...]) -> list[dict]:
    observations=validate_stim_manifest(obj,basis=basis,physical_error=physical_error,rounds=rounds,distances=distances)
    result=[]
    for d in sorted(distances):
        observation=observations[d]
        rate=wilson(observation["failures"],observation["shots"])
        events=workload.logical_qubits*workload.memory_windows
        per_event_budget=allowed_memory_error(workload.target_failure, workload.logical_qubits, workload.memory_windows)
        min_shots_zero=minimum_shots_if_zero_failures(per_event_budget)
        for scenario in scenarios:
            sites_per_patch=2*d*d-1  # data d² + measurement ancillas (d² - 1)
            base_sites=workload.logical_qubits*sites_per_patch
            reserve=math.ceil(base_sites*scenario.reserve_fraction)
            controller_sites=workload.logical_qubits*scenario.controller_site_equivalents_per_patch
            sites=base_sites+reserve+controller_sites
            window_us=rounds*scenario.cycle_us+scenario.decode_us_per_window
            latency=workload.memory_windows*window_us
            result.append({
                "architecture":scenario.name,"distance":d,"physical_error":physical_error,
                "basis":basis,"rounds_per_window":rounds,"shots":rate.observations,"failures":rate.failures,
                "trivial_decoder_failures":observation["trivial_decoder_failures"],
                "nominal_per_event_budget":per_event_budget,
                "minimum_shots_if_zero_failures":min_shots_zero,
                "zero_failure_wilson_upper95":zero_failures_upper95(rate.observations),
                "logical_error_per_memory_window":rate.mean,
                "logical_error_lower95":rate.lower,"logical_error_upper95":rate.upper,
                "workload_failure_mean":cumulative_failure(rate.mean,events),
                "workload_failure_upper95":cumulative_failure(rate.upper,events),
                "feasible_point_estimate":cumulative_failure(rate.mean,events)<=workload.target_failure,
                "feasible_upper95":cumulative_failure(rate.upper,events)<=workload.target_failure,
                "patch_site_equivalents":base_sites,"reserve_site_equivalents":reserve,
                "controller_site_equivalents":controller_sites,
                "total_site_equivalents":sites,"storage_runtime_us":latency,
                "site_us":sites*latency,
                "model_kind":"surface_code_memory_only_stim_pymatching",
                "cost_assumptions":"site/latency/controller proxy accounting is scenario-assumed, not measured; independent memory events; controller proxies are not measured physical qubits",
            })
    return result


def load_memory_scenarios(path:Path)->tuple[MemoryWorkload,list[MemoryScenario]]:
    p=json.loads(path.read_text(encoding="utf-8"))
    workload=MemoryWorkload(**p["workload"])
    return workload,[MemoryScenario(**x) for x in p["memory_architectures"]]


def nondominated(rows: list[dict])->list[dict]:
    feasible=[r for r in rows if r["feasible_upper95"]]
    def dominates(a,b):
        a_metrics=(a["total_site_equivalents"],a["storage_runtime_us"])
        b_metrics=(b["total_site_equivalents"],b["storage_runtime_us"])
        return all(x<=y for x,y in zip(a_metrics,b_metrics)) and any(x<y for x,y in zip(a_metrics,b_metrics))
    return [r for r in feasible if not any(dominates(x,r) for x in feasible if x is not r)]


def write_comparison(rows:list[dict],obj:dict,workload:MemoryWorkload,out:Path,*, basis:str,p:float,rounds:int, plot_logical_failure:bool=True):
    out.mkdir(parents=True,exist_ok=True)
    # When reusing the same observed shot set for controller-cost sensitivity,
    # remove a stale plot left by earlier versions of the pipeline.
    if not plot_logical_failure:
        (out/"memory_logical_failure.png").unlink(missing_ok=True)
    with (out/"memory_tradeoffs.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
    frontier=nondominated(rows)
    report=["# Surface-code MEMORY study - real Stim/PyMatching experiment output", "",
        "**Scope:** memory for an identical fixed number of syndrome rounds across code distances; not a logical gate or photonic FTQC prediction.","",
        f"- Simulator provenance: Stim `{obj['software']['stim']}`, PyMatching `{obj['software']['pymatching']}`.",
        f"- Decoder: MWPM, decomposed detector error model. Basis: {basis}; syndrome rounds: {rounds}; uniform circuit noise p={p}.",
        f"- Workload: {workload.logical_qubits} independent logical patches, {workload.memory_windows} consecutive *{rounds}-round* memory windows.",
        f"- Reliability goal for the entire independent-events proxy: {workload.target_failure:g}.",
        "- Uncertainty: two-sided Wilson 95% per memory experiment; upper endpoint conservatively propagated under independence.",
        "- Latency, patch sites, reserve, and optional controller overhead: assumed, not measured. Controller site-equivalent units are an illustrative cost *proxy*, not extra physical qubit counts.",
        "- The same physical noise and nine-round memory circuit is reused for each control design; faster cycles are **not** simulated with worse noise or independently calibrated.",
        "- Statistical sample-planning fields give the MINIMUM trials that could clear the per-event budget if zero failures occurred; they do not establish power for nonzero rates or simultaneous coverage.","",
        "## Observations and modeled costs","",
        "| Assumed control | d | MWPM fail/shots | trivial fail/shots | pL (memory) | upper 95% | patch+reserve | controller proxy | total site-equivalents | total µs | robust feasible |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        report.append(f"| {r['architecture']} | {r['distance']} | {r['failures']}/{r['shots']} | {r['trivial_decoder_failures']}/{r['shots']} | "
                      f"{r['logical_error_per_memory_window']:.5g} | {r['logical_error_upper95']:.5g} | "
                      f"{r['patch_site_equivalents']+r['reserve_site_equivalents']} | {r['controller_site_equivalents']} | {r['total_site_equivalents']} | {r['storage_runtime_us']:.2f} | "
                      f"{'yes' if r['feasible_upper95'] else 'no'} |")
    report += ["","## Two-objective Pareto set (among conservative feasible points)",""]
    report += [f"- {r['architecture']}, d={r['distance']}: {r['total_site_equivalents']} site equivalents / {r['storage_runtime_us']:.3f} µs" for r in frontier]
    if not frontier:report.append("No observed point passed the upper-interval budget; this is not proof that none can.")
    report += ["", "## What can and cannot be concluded", "",
       "Results test conditional architecture-memory tradeoffs under a common *simulated* circuit and decoder. Changing the assumed cycle time or assigning extra controller cost does not change circuit noise, a simplifying assumption. The controller overhead is a hypothetical normalized site-equivalent proxy, not measured classical electronics or extra physical qubits. All scenarios reuse the same event probabilities; none is independently calibrated hardware. The workload-level upper endpoint is a propagated **per-experiment Wilson endpoint**, not simultaneous confidence coverage or a complete uncertainty budget.",
       "", "## Reproduce", "",
       "```bash", "./scripts/commands/RUN_STIM_MEMORY.sh                # baseline experiment", "./scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh       # distance 7/9 and optional controller-cost study", "```", "",
       "## Methods and source", "",
       "- [Stim](https://github.com/quantumlib/Stim) generated rotated surface-code memory circuits.",
       "- [PyMatching](https://pymatching.readthedocs.io/) detector-error-model matching and decoding API.",
       "- [Fowler et al. (2012)](https://doi.org/10.1103/PhysRevA.86.032324) motivates the surface-code context; numerical values come from *this* run, not the paper."]
    (out/"MEMORY_REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        if plot_logical_failure:
            plot_memory_logical_failure(rows,workload,out,basis=basis,p=p,rounds=rounds,plt=plt)
        if any(r["controller_site_equivalents"] for r in rows):
            fig,ax=plt.subplots(figsize=(8.5,5))
            for r in rows:
                if r["feasible_upper95"]:
                    ax.scatter(r["total_site_equivalents"],r["storage_runtime_us"],
                               color="tab:blue",s=65)
                    ax.annotate(f"{r['architecture']} (d={r['distance']})",
                                (r["total_site_equivalents"],r["storage_runtime_us"]),
                                xytext=(5,5),textcoords="offset points",fontsize=8)
                else:
                    ax.scatter(r["total_site_equivalents"],r["storage_runtime_us"],
                               color="tab:gray",alpha=.45,s=45)
            ax.set_xlabel("Total normalized site-equivalents (assumed controller overhead)")
            ax.set_ylabel("Assumed memory workload latency (microseconds)")
            ax.set_title("Illustrative control cost vs speed - not hardware calibrated")
            ax.grid(alpha=.2);fig.tight_layout()
            fig.savefig(out/"memory_architecture_tradeoff.png",dpi=160);plt.close(fig)
    except ImportError:
        pass


def plot_memory_logical_failure(rows,workload,out,*,basis,p,rounds,plt):
    distances=sorted(set(r["distance"] for r in rows))
    samples={d:next(r for r in rows if r["distance"]==d) for d in distances}
    figure,ax=plt.subplots(figsize=(7.5,4.5))
    ax.errorbar(distances,[samples[d]["logical_error_per_memory_window"] for d in distances],
                yerr=[[samples[d]["logical_error_per_memory_window"]-samples[d]["logical_error_lower95"] for d in distances],
                      [samples[d]["logical_error_upper95"]-samples[d]["logical_error_per_memory_window"] for d in distances]],
                fmt="o-",capsize=4)
    ax.axhline(allowed_memory_error(workload.target_failure,workload.logical_qubits,workload.memory_windows),
               color="gray",linestyle="--",label="Nominal per-event budget")
    ax.legend(loc="best",fontsize=8)
    ax.set_xlabel(f"Code distance d ({rounds} rounds for every code)");ax.set_ylabel(f"Failure probability per {rounds}-round memory experiment")
    ax.set_title(f"Stim + PyMatching rotated surface memory; p={p:g}; {basis}-basis")
    ax.grid(alpha=.25);figure.tight_layout()
    figure.savefig(out/"memory_logical_failure.png",dpi=160);plt.close(figure)

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description="Compare strictly matched, REAL Stim surface-memory measurements")
    parser.add_argument("--observations",type=Path,default=Path("outputs/stim_memory/observations.json"))
    parser.add_argument("--config",type=Path,default=Path("examples/memory_architecture_scenarios.json"))
    parser.add_argument("--output-dir",type=Path,default=Path("outputs/stim_memory/analysis"))
    parser.add_argument("--physical-error",type=float,default=.003)
    parser.add_argument("--basis",choices=["X","Z"],default="X")
    parser.add_argument("--distances",default="3,5,7")
    parser.add_argument("--rounds",type=int,default=9)
    parser.add_argument("--no-logical-failure-plot",action="store_true",
                        help="Reuse the canonical follow-up logical-failure figure when analyzing the same shots")
    args=parser.parse_args(argv)
    obj=json.loads(args.observations.read_text(encoding="utf-8"))
    work,scenarios=load_memory_scenarios(args.config)
    distances=tuple(int(x) for x in args.distances.split(","))
    if len(set(distances))!=len(distances) or any(d<3 or d%2!=1 for d in distances):
        raise ValueError("distinct odd distances >=3 required")
    rows=compare_memory(obj,scenarios,work,basis=args.basis,physical_error=args.physical_error,rounds=args.rounds,distances=distances)
    write_comparison(rows,obj,work,args.output_dir,basis=args.basis,p=args.physical_error,rounds=args.rounds,
                     plot_logical_failure=not args.no_logical_failure_plot)
    print(f"Saved {len(rows)} strictly matched MEMORY-architecture comparisons to {args.output_dir}")
    print(f"Conservatively feasible Pareto points: {len(nondominated(rows))}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
