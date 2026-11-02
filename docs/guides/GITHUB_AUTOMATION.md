# GitHub Actions, experimental data and output policy

The executable definitions in `.github/workflows/` are authoritative. This guide explains the intended operational boundaries, not proof of a successful GitHub-hosted run.

## CI and automation

| Workflow | Trigger | Scope |
|---|---|---|
| `tests.yml` | Push, pull request, manual | Regression tests across the declared Python matrix, with log artifacts |
| `stim-memory.yml` | Main-branch push, weekly, manual | Track A real Stim/PyMatching simulation, Pareto studies and replay checks |
| `source-updates.yml` | Weekly, manual | Approved upstream source-revision checks, guarded source downloads and evidence inventory; reviewable source PRs |
| `validated-results.yml` | Manual only | Publication of independently reviewed simulator results; does not establish hardware validation |
| `.github/dependabot.yml` | Weekly | Dependency and GitHub Action update PRs; no scientific certification or automatic acceptance |

No GitHub Actions cache is configured currently; fetchers can reuse existing files within a runner, but newly provisioned hosted runners may download sources again. Workflow success needs to be checked in the repository Actions tab after pushing. A green unit-test check does not prove that large experimental datasets were downloaded, processed and scientifically reproduced.

## Data and artifacts

- **Tracked in Git:** executable source, tests, small source-hashed evidence receipts, configuration, documentation, selected figures and reviewed upstream revision records.
- **Ignored local downloads:** `data/public_calibrations/`, `data/external_hardware/`, `data/verified/`. Third-party experimental archives and cloned sources are not source-control dependencies.
- **Ignored execution logs:** `logs/runs/<run-id>/`.
- **Generated reports:** `outputs/` including `outputs/FOUR_PLATFORM_REVIEW_BUNDLE.zip`. Outputs included in Git are scoped and have provenance. Unreviewed hardware outputs are not automatically promoted.
- **GitHub artifacts:** logs and appropriately scoped reports with finite retention. Use longer-lived, immutable external storage for independently reviewed scientific datasets and results when needed.

### Controlled data retrieval

```zsh
python3 scripts/automation/run_pipeline.py --profile evidence --fetch --review-bundle
python3 scripts/automation/run_pipeline.py --profile evidence --fetch --download-large-neutral --review-bundle
```

Downloads use approved source destinations, verify supplied checksums where available, and may skip inputs that exceed size limits. Large neutral-atom data require explicit opt-in. These workflows do not execute untrusted Python pickle files, auto-approve measured-data interpretations, or transform hardware specifications into measured shot counts. Review source licenses and preprocessing before reuse.

Upstream revision changes can open reviewable PRs. Do not enable blind auto-merge for source-data or model changes. Dependabot and source PRs do not replace protocol verification. GitHub's `GITHUB_TOKEN` may not trigger a further downstream workflow on its own when creating PRs; require an observed CI run before accepting a change.

## Scientific acceptance versus software health

`ci`, `science`, `ibm`, `evidence` and `all` are described in [Running and reproducing](RUNNING_AND_REPRODUCING.md). The experimental runner records blocked sources rather than inventing files. Its candidate gate dossiers under `evidence/gate_review_candidates/` default to **pending review** and do not increase the 34-gate acceptance score without independent, protocol-matched validation.

For the evidence standard, see [four-platform acceptance](../validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.md) and [limitations](../validation/LIMITATIONS.md).

## GitHub repository settings

Enable Actions and Dependabot. Protect `main` using required CI and review. Scope write permissions for source-update PRs narrowly, and keep the results-publication workflow manually triggered. **Do not archive the active repository** because GitHub repository archiving makes it read-only. Archive workflow artifacts and independently reviewed scientific records instead.
