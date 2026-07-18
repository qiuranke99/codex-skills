#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
SUBSYSTEM_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
RELEASE_RECEIPT="$CODEX_HOME_DIR/.ai-tvc-releases/release-receipt.json"
ACTION="${1:-check}"
if [[ "$ACTION" != "check" && "$ACTION" != "sync" ]]; then
  printf '%s\n' "ERROR: first argument must be check or sync" >&2
  exit 64
fi
shift || true

PYTHON_EXECUTABLE="${AI_TVC_PYTHON:-}"
if [[ -z "$PYTHON_EXECUTABLE" && -r "$RELEASE_RECEIPT" ]]; then
  PYTHON_EXECUTABLE="$({
    awk -F '"' '/"python_executable"[[:space:]]*:/ { print $4; exit }' "$RELEASE_RECEIPT"
  } || true)"
fi
if [[ -z "$PYTHON_EXECUTABLE" && -x "$SUBSYSTEM_DIR/.venv/bin/python" ]]; then
  PYTHON_EXECUTABLE="$SUBSYSTEM_DIR/.venv/bin/python"
fi
if [[ -z "$PYTHON_EXECUTABLE" || ! -x "$PYTHON_EXECUTABLE" ]]; then
  printf '%s\n' "ERROR: optional aggregate maintenance runtime is unavailable. Run setup-runtime.sh and aggregate release sync before using the aggregate profile." >&2
  exit 127
fi

export PYTHONDONTWRITEBYTECODE=1
cd "$CODEX_HOME_DIR"
exec "$PYTHON_EXECUTABLE" "$SCRIPT_DIR/release_control.py" "$ACTION" "$@"
