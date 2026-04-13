#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree is not clean. Commit your repo changes before syncing to Appsmith." >&2
  exit 1
fi

git push
python3 "$ROOT_DIR/scripts/sync_appsmith_repo_to_appsmith.py" --repo-root "$ROOT_DIR"
