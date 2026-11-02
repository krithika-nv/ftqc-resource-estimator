#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
# Publish from authenticated, trusted main-branch GitHub Actions only.
if [[ "${GITHUB_ACTIONS:-}" != "true" || "${GITHUB_REF:-}" != "refs/heads/main" || "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then
  echo 'This publisher runs only in trusted GitHub Actions on main.' >&2
  exit 2
fi
: "${GITHUB_TOKEN:?GitHub Actions token unavailable}"
: "${GITHUB_REPOSITORY:?GitHub repository context unavailable}"
source_dir="${1:-build/publication}"
[[ -f "$source_dir/README.md" && -f "$source_dir/provenance.json" ]] || { echo 'Missing validated publication bundle' >&2; exit 2; }
source_dir="$(cd "$source_dir" && pwd)"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
remote="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
git init -q -b validated-results "$work_dir"
git -C "$work_dir" remote add origin "$remote"
if git -C "$work_dir" ls-remote --exit-code --heads origin validated-results >/dev/null 2>&1; then
  git -C "$work_dir" fetch --quiet --depth=1 origin validated-results
  git -C "$work_dir" checkout -q -B validated-results FETCH_HEAD
fi
# Only allowlisted validated outputs from publication bundle; remove stale results.
find "$work_dir" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cp -R "$source_dir/." "$work_dir/"
git -C "$work_dir" add -A
if git -C "$work_dir" diff --cached --quiet; then
  echo 'No analysis-result changes to publish.'
else
  git -C "$work_dir" -c user.name='github-actions[bot]' -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    commit -q -m "Update validated analysis outputs from ${GITHUB_SHA:-unknown}"
  git -C "$work_dir" push --quiet origin HEAD:refs/heads/validated-results
  echo 'Updated branch validated-results (results only; not source code).'
fi
