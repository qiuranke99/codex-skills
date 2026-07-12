#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
if [[ -n "${AI_TVC_PYTHON:-}" ]]; then
  if [[ -x "$AI_TVC_PYTHON" ]]; then
    exec "$AI_TVC_PYTHON" "$SCRIPT_DIR/setup_runtime.py" "$@"
  fi
  printf '%s\n' "ERROR: AI_TVC_PYTHON is not executable: $AI_TVC_PYTHON" >&2
  exit 126
fi
for PYTHON in python3.12 python3.11; do
  if command -v "$PYTHON" >/dev/null 2>&1; then
    exec "$PYTHON" "$SCRIPT_DIR/setup_runtime.py" "$@"
  fi
done
printf '%s\n' "ERROR: install Python 3.11 or 3.12 before creating the suite runtime." >&2
exit 127
