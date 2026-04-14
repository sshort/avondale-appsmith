#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PUSH_GIT=0
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push-git)
      PUSH_GIT=1
      shift
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ "$PUSH_GIT" -eq 1 ]]; then
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Working tree is not clean. Commit your repo changes before syncing with --push-git." >&2
    exit 1
  fi
  git push
fi

python3 "$ROOT_DIR/scripts/sync_appsmith_repo_to_appsmith.py" --repo-root "$ROOT_DIR" "${ARGS[@]}"
