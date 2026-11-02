# Script entry points

Run the following commands from the repository root unless otherwise noted. The shell entry points also resolve the repository root from their own location, so they can be invoked by absolute path from another working directory.

| Directory | Responsibility | Examples |
|---|---|---|
| `scripts/commands/` | Executable shell entry points for standalone studies, evidence imports and controlled publication | `RUN_ARCHITECTURE_STUDY.sh`, `RUN_ALL_VALIDATIONS.sh`, `RUN_MATCHED_HARDWARE_EVIDENCE.sh` |
| `scripts/automation/` | Python orchestration, download coordination, run manifests, evidence snapshots and reviews | `run_pipeline.py`, `source_updates.py`, `package_platform_review.py` |
| `scripts/tools/` | Standalone Python helpers for calibration acquisition, plots, replay checks and publication assembly | `download_2026_qec_calibration.py`, `prepare_results.py`, `verify_scientific_release.py` |

## Recommended commands

```zsh
python3 scripts/automation/run_pipeline.py --profile ci
python3 scripts/automation/run_pipeline.py --profile science
python3 scripts/automation/run_pipeline.py --profile evidence --fetch --review-bundle
```

For individual studies, run `bash scripts/commands/RUN_ARCHITECTURE_STUDY.sh` or another command in `scripts/commands/`. To inspect the planned pipeline without invoking experiments, use `python3 scripts/automation/run_pipeline.py --profile all --fetch --dry-run`.

All generated outputs remain under `outputs/`; logs remain under `logs/runs/`. Original data downloads remain under `data/`. Script relocation does not change model assumptions, scientific acceptance rules, or the distinction between Track A and Track B. The authoritative user instructions are in [Running and reproducing](../docs/guides/RUNNING_AND_REPRODUCING.md).
