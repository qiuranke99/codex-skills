#!/usr/bin/env bash
set -euo pipefail

FORMAT="json"
while (($#)); do
  case "$1" in
    --format)
      shift
      if (($# == 0)); then
        printf '%s\n' "ERROR: --format requires json" >&2
        exit 64
      fi
      FORMAT="$1"
      ;;
    *)
      printf '%s\n' "ERROR: unsupported argument: $1" >&2
      exit 64
      ;;
  esac
  shift
done
if [[ "$FORMAT" != "json" ]]; then
  printf '%s\n' "ERROR: only --format json is supported" >&2
  exit 64
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
PACKAGE_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"

export PYTHONDONTWRITEBYTECODE=1
PYTHON_EXECUTABLE=""
if [[ -n "${AI_AD_REFERENCE_PYTHON:-}" ]]; then
  if [[ ! -x "$AI_AD_REFERENCE_PYTHON" ]] || ! "$AI_AD_REFERENCE_PYTHON" -I -B -c \
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    printf '%s\n' "ERROR: AI_AD_REFERENCE_PYTHON must name a Python 3.10+ executable" >&2
    exit 127
  fi
  PYTHON_EXECUTABLE="$AI_AD_REFERENCE_PYTHON"
else
  candidates=(
    python3.12
    python3.11
    python3.10
    "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
    python3
    python
  )
  for candidate in "${candidates[@]}"; do
    resolved=""
    if [[ "$candidate" == */* ]]; then
      if [[ -x "$candidate" ]]; then
        resolved="$candidate"
      fi
    elif command -v "$candidate" >/dev/null 2>&1; then
      resolved="$(command -v "$candidate")"
    fi
    if [[ -n "$resolved" ]] && "$resolved" -I -B -c \
      'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' \
      >/dev/null 2>&1; then
      PYTHON_EXECUTABLE="$resolved"
      break
    fi
  done
fi
if [[ -z "$PYTHON_EXECUTABLE" ]]; then
  printf '%s\n' "ERROR: Python 3.10 or newer is required for package-local contract tests" >&2
  exit 127
fi

"$PYTHON_EXECUTABLE" -I -B -c \
  'import runpy, sys; sys.path.insert(0, sys.argv[1]); runpy.run_path(sys.argv[2], run_name="__main__")' \
  "$SCRIPT_DIR" "$SCRIPT_DIR/test_contract.py" >&2

printf '%s\n' '{"gate_mode":"standalone_package","package_contract_ready":true,"proof_scope":"package_contract_only","ready_for_skill_workflow":true}'
