#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/sync-from-appsmith.sh /path/to/exported-appsmith.json" >&2
  exit 1
fi

EXPORT_JSON="$1"

python3 "$ROOT_DIR/scripts/sync_appsmith_export_to_repo.py" \
  "$EXPORT_JSON" \
  --repo-root "$ROOT_DIR" \
  --capture-dir live-exports
