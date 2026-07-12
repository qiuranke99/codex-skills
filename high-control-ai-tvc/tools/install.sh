#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
ACTION="${1:-install}"
if [[ $# -gt 0 ]]; then
  shift
fi

find_python() {
  local candidate
  if [[ -n "${AI_TVC_PYTHON:-}" ]]; then
    if [[ -x "$AI_TVC_PYTHON" ]]; then
      printf '%s\n' "$AI_TVC_PYTHON"
      return 0
    fi
    printf '%s\n' "ERROR: AI_TVC_PYTHON is not executable: $AI_TVC_PYTHON" >&2
    return 126
  fi
  if [[ -x "$SCRIPT_DIR/../.venv/bin/python" ]]; then
    printf '%s\n' "$SCRIPT_DIR/../.venv/bin/python"
    return 0
  fi
  for candidate in python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  printf '%s\n' "ERROR: Python 3.11 or 3.12 is required." >&2
  return 127
}

PYTHON="$(find_python)"
case "$ACTION" in
  install|adopt|status|uninstall)
    exec "$PYTHON" "$SCRIPT_DIR/manage_skills.py" "$ACTION" "$@"
    ;;
  audit|preflight)
    exec "$PYTHON" "$SCRIPT_DIR/preflight.py" "$@"
    ;;
  *)
    printf '%s\n' "Usage: tools/install.sh [install|adopt|status|audit|uninstall] [options]" >&2
    exit 64
    ;;
esac
