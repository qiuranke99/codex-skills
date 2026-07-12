#!/usr/bin/env python3
"""Create/update the repository-local, pinned Python runtime."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from suite_common import REPO_ROOT, SUBSYSTEM_ROOT, SuiteConfigurationError, load_distribution


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _run(command: list[str]) -> None:
    result = subprocess.run(command, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {command[0]}")


def _path_identity(path: Path) -> str:
    return os.path.normcase(str(path.expanduser().resolve(strict=False)))


def validate_venv_identity(venv: Path, python: Path, tested: list[str]) -> str:
    """Prove the interpreter is isolated inside the requested venv."""
    probe_code = (
        "import json,sys; "
        "print(json.dumps({'version':f'{sys.version_info.major}.{sys.version_info.minor}',"
        "'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"
    )
    probe = subprocess.run(
        [str(python), "-c", probe_code],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    try:
        identity = json.loads(probe.stdout.strip()) if probe.returncode == 0 else None
    except json.JSONDecodeError:
        identity = None
    if not isinstance(identity, dict):
        raise RuntimeError(f"existing venv interpreter is unreadable: {python}: {probe.stdout.strip()}")
    version = identity.get("version")
    prefix = identity.get("prefix")
    base_prefix = identity.get("base_prefix")
    if version not in tested:
        raise RuntimeError(f"existing venv interpreter is {version or 'unknown'}; expected {', '.join(tested)}")
    if not isinstance(prefix, str) or not isinstance(base_prefix, str) or prefix == base_prefix:
        raise RuntimeError(f"refusing non-isolated interpreter at {python}; it is not a Python virtual environment")
    if _path_identity(Path(prefix)) != _path_identity(venv):
        raise RuntimeError(
            f"venv interpreter prefix {prefix} does not belong to requested runtime {venv}; refusing pip mutation"
        )
    return version


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", type=Path, default=SUBSYSTEM_ROOT / ".venv")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    try:
        _manifest, requirements, _skills, errors = load_distribution(REPO_ROOT)
        if errors:
            raise SuiteConfigurationError("; ".join(errors))
        tested = requirements["python"]["tested_major_minor"]
        current = f"{sys.version_info.major}.{sys.version_info.minor}"
        if current not in tested:
            raise RuntimeError(f"Python {current} cannot build the production runtime; use {', '.join(tested)}")

        venv = args.venv.expanduser().absolute()
        python = _venv_python(venv)
        if not python.is_file():
            if venv.exists() and any(venv.iterdir()):
                raise RuntimeError(f"refusing to replace a non-venv or damaged directory: {venv}")
            _run([sys.executable, "-m", "venv", str(venv)])
        venv_version = validate_venv_identity(venv, python, tested)
        pillow = requirements["python"]["packages"]["Pillow"]
        _run([str(python), "-m", "pip", "install", "--disable-pip-version-check", f"Pillow=={pillow}"])
        result = {
            "schema_version": "1.0.0",
            "success": True,
            "venv": str(venv),
            "python": str(python),
            "python_major_minor": venv_version,
            "Pillow": pillow,
            "note": "ffmpeg and ffprobe are system executables and are checked separately by preflight",
        }
    except (KeyError, OSError, RuntimeError, SuiteConfigurationError) as exc:
        result = {"schema_version": "1.0.0", "success": False, "error": str(exc)}
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"OK: pinned runtime is ready at {result['venv']}")
        print("Next: install ffmpeg/ffprobe, then run the suite preflight.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
