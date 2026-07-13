#!/usr/bin/env python3
"""Positive and adversarial tests for the cross-package suite validator."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from validate_ai_video_suite import PUBLISH_SURFACE, _run, validate_suite
from validate_schema_parity import validate_instance


SUITE_ROOT = Path(__file__).resolve().parents[2]


def assert_has(errors: list[str], needle: str) -> None:
    if not any(needle in error for error in errors):
        raise AssertionError(f"expected {needle!r}, got {errors}")


def process_is_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            exit_code = wintypes.DWORD()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == 259
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def assert_timeout_kills_orphan_tree() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        helper = root / "orphan_pipe.py"
        helper.write_text(
            "import subprocess, sys\n"
            "child = subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(30)'], stdout=sys.stdout, stderr=sys.stderr)\n"
            "print(f'CHILD_PID={child.pid}', flush=True)\n",
            encoding="utf-8",
        )
        started = time.monotonic()
        try:
            _run(
                [sys.executable, str(helper)], root,
                timeout_seconds=0.5, cleanup_timeout_seconds=3,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.monotonic() - started
            output = exc.output.decode("utf-8", errors="replace") if isinstance(exc.output, bytes) else str(exc.output or "")
            match = re.search(r"CHILD_PID=(\d+)", output)
            if match is None:
                raise AssertionError(f"timeout result lost child PID evidence: {output!r}")
            child_pid = int(match.group(1))
            deadline = time.monotonic() + 2
            while process_is_alive(child_pid) and time.monotonic() < deadline:
                time.sleep(0.05)
            if process_is_alive(child_pid):
                raise AssertionError(f"timeout left orphan child process {child_pid}")
            if elapsed > 6:
                raise AssertionError(f"timeout cleanup was not bounded: {elapsed:.3f}s")
        else:
            raise AssertionError("orphan-pipe helper did not time out")


def main() -> int:
    assert_timeout_kills_orphan_tree()
    errors = validate_suite(SUITE_ROOT, run_tests=False, require_discovery=False)
    if errors:
        raise AssertionError(f"valid suite rejected: {errors}")

    path_schema = {
        "type": "string",
        "not": {"anyOf": [{"pattern": "^/"}, {"pattern": "(^|/)\\.\\.(/|$)"}]},
    }
    if validate_instance("safe/file.json", path_schema, path_schema):
        raise AssertionError("schema engine rejected a safe relative path")
    if not validate_instance("../escape.json", path_schema, path_schema):
        raise AssertionError("schema engine failed to enforce not for traversal")
    if not validate_instance("/absolute.json", path_schema, path_schema):
        raise AssertionError("schema engine failed to enforce not for absolute path")

    with tempfile.TemporaryDirectory() as tmp:
        copied = Path(tmp)
        for skill in PUBLISH_SURFACE:
            shutil.copytree(SUITE_ROOT / skill, copied / skill)

        missing = copied / "ai-video-global-look-lock/test_cases.md"
        missing.unlink()
        assert_has(validate_suite(copied, run_tests=False), "required file missing")
        shutil.copy2(SUITE_ROOT / "ai-video-global-look-lock/test_cases.md", missing)

        skill_md = copied / "ai-video-shot-script-director/SKILL.md"
        skill_md.write_text(skill_md.read_text(encoding="utf-8").replace("name: ai-video-shot-script-director", "name: wrong-name", 1), encoding="utf-8")
        assert_has(validate_suite(copied, run_tests=False), "frontmatter name mismatch")
        shutil.copy2(SUITE_ROOT / "ai-video-shot-script-director/SKILL.md", skill_md)

        route_contract = copied / "ai-video-global-look-lock/SKILL.md"
        route_contract.write_text(
            route_contract.read_text(encoding="utf-8").replace(
                "standalone_single_image_to_video: forbidden",
                "standalone_single_image_to_video: removed",
                1,
            ),
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "generation-route boundary marker missing")
        shutil.copy2(SUITE_ROOT / "ai-video-global-look-lock/SKILL.md", route_contract)

        owner_skill_md = copied / "character-final-lock-board/SKILL.md"
        owner_skill_md.write_text(
            owner_skill_md.read_text(encoding="utf-8").replace(
                "name: character-final-lock-board", "name: wrong-owner-name", 1
            ),
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "frontmatter name mismatch")
        shutil.copy2(SUITE_ROOT / "character-final-lock-board/SKILL.md", owner_skill_md)

        metadata = copied / "ai-video-modular-storyboard/agents/openai.yaml"
        metadata.write_text(
            metadata.read_text(encoding="utf-8").replace(
                'short_description: "Build one editable storyboard frame per scripted shot."',
                'short_description: "Too short"',
            ),
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "short_description must contain 25-64 characters")
        shutil.copy2(SUITE_ROOT / "ai-video-modular-storyboard/agents/openai.yaml", metadata)

        owner_wrapper = copied / "character-final-lock-board/scripts/export_ai_video_canon.py"
        owner_wrapper.write_text(
            owner_wrapper.read_text(encoding="utf-8").replace(
                'run_fixed_owner_cli("character_final", Path(__file__))',
                'run_fixed_owner_cli("character_casting", Path(__file__))',
            ),
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "fixed owner export wrapper profile drift")
        shutil.copy2(
            SUITE_ROOT / "character-final-lock-board/scripts/export_ai_video_canon.py",
            owner_wrapper,
        )

        owner_appendix = copied / "scene-canon-asset-pack/SKILL.md"
        owner_appendix.write_text(
            owner_appendix.read_text(encoding="utf-8").replace(
                "## Optional AI-Video Project Canon Export",
                "## Removed Project Canon Export Appendix",
                1,
            ),
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "Project Canon export appendix missing")
        shutil.copy2(SUITE_ROOT / "scene-canon-asset-pack/SKILL.md", owner_appendix)

        private_path = copied / "packaging-product-identity-label-lock-board/private-note.md"
        private_path.write_text(
            "private evidence: " + "/" + "Users/example/secret.json\n",
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "hardcoded local absolute path")
        private_path.unlink()

        swift_path = copied / "packaging-product-identity-label-lock-board/scripts/leaky.swift"
        swift_path.write_text(
            "let privatePath = \"" + "/" + "Users/example/private.json\"\n",
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "hardcoded local absolute path")
        swift_path.unlink()

        secret_path = copied / "multi-angle-product-identity-lock-board/leak.md"
        secret_path.write_text("token=" + "ghp_" + "A" * 30 + "\n", encoding="utf-8")
        assert_has(validate_suite(copied, run_tests=False), "possible secret/private key")
        secret_path.unlink()

        for label, secret in (
            ("aws", "AKIA" + "A" * 16),
            ("slack", "xoxb-" + "B" * 24),
            ("bearer", "Bearer " + "C" * 32),
        ):
            expanded_secret = copied / f"multi-angle-product-identity-lock-board/{label}-leak.md"
            expanded_secret.write_text(secret + "\n", encoding="utf-8")
            assert_has(validate_suite(copied, run_tests=False), "possible secret/private key")
            expanded_secret.unlink()

        binary = copied / "packaging-product-identity-label-lock-board/private-photo.jpg"
        binary.write_bytes(b"not-a-public-source-artifact")
        assert_has(validate_suite(copied, run_tests=False), "unsupported publication file type")
        binary.unlink()

        run_artifact = copied / "packaging-product-identity-label-lock-board/runs/run.json"
        run_artifact.parent.mkdir()
        run_artifact.write_text("{}\n", encoding="utf-8")
        assert_has(validate_suite(copied, run_tests=False), "forbidden generated/cache path")
        shutil.rmtree(run_artifact.parent)

        oversized = copied / "packaging-product-identity-label-lock-board/oversized.md"
        oversized.write_bytes(b"x" * (1024 * 1024 + 1))
        assert_has(validate_suite(copied, run_tests=False), "exceeds 1 MiB review cap")
        oversized.unlink()

        symlink = copied / "packaging-product-identity-label-lock-board/linked-skill.md"
        try:
            symlink.symlink_to("SKILL.md")
        except OSError:
            pass  # Windows may deny unprivileged symlink creation; Unix CI covers this negative.
        else:
            assert_has(validate_suite(copied, run_tests=False), "symlinks are forbidden")
            symlink.unlink()

        packaging_requirements = copied / "packaging-product-identity-label-lock-board/requirements.txt"
        packaging_requirements.write_text(
            packaging_requirements.read_text(encoding="utf-8").replace("Pillow==11.3.0", "Pillow==11.2.0"),
            encoding="utf-8",
        )
        assert_has(validate_suite(copied, run_tests=False), "Pillow pins must remain identical")
        shutil.copy2(
            SUITE_ROOT / "packaging-product-identity-label-lock-board/requirements.txt",
            packaging_requirements,
        )

        bad_python = copied / "material-sensitive-product-master-asset-board/scripts/bad_publish.py"
        bad_python.write_text("def broken(:\n", encoding="utf-8")
        assert_has(validate_suite(copied, run_tests=False), "Python syntax error")
        bad_python.unlink()

        bad_json = copied / "single-face-character-lock-board/bad_publish.json"
        bad_json.write_text("{not-json}\n", encoding="utf-8")
        assert_has(validate_suite(copied, run_tests=False), "invalid JSON")
        bad_json.unlink()

        cache = copied / "character-casting-lock-board/__pycache__/bad.pyc"
        cache.parent.mkdir()
        cache.write_bytes(b"bad")
        assert_has(validate_suite(copied, run_tests=False), "forbidden generated/cache path")

    print(
        "PASS: suite validator accepts the 13-package publication surface and rejects "
        "six/owner frontmatter drift, suite-wide generation-route marker drift, "
        "owner wrapper/appendix drift, private paths, secrets, invalid Python/JSON, "
        "Swift leaks, expanded secrets, unsupported binaries, run/temp artifacts, "
        "oversized files, symlinks, Pillow-pin drift, metadata drift, owner caches, "
        "and bounded orphan-safe child-test timeout cleanup"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
