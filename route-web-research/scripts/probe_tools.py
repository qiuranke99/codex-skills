#!/usr/bin/env python3
"""Probe the local route-web-research toolchain without installing anything."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_ROOT = Path(os.environ.get("GLOBAL_SEARCH_TOOLCHAIN_ROOT", r"D:\AI\toolchains\global-search"))
DEFAULT_PYTHON = Path(
    os.environ.get("GLOBAL_SEARCH_PYTHON", str(DEFAULT_ROOT / ".venv" / "Scripts" / "python.exe"))
)
DEFAULT_NODE_ROOT = Path(os.environ.get("GLOBAL_SEARCH_NODE_ROOT", str(DEFAULT_ROOT / "node")))

PYTHON_PACKAGES = {
    "firecrawl-py": "firecrawl",
    "crawl4ai": "crawl4ai",
    "browser-use": "browser_use",
    "scrapy": "scrapy",
    "markitdown": "markitdown",
    "scrapling": "scrapling",
    "autoscraper": "autoscraper",
    "curl_cffi": "curl_cffi",
    "duckduckgo-search": "duckduckgo_search",
    "ddgs": "ddgs",
    "playwright": "playwright",
}

NODE_MODULES = ["crawlee", "@mendable/firecrawl-js", "playwright"]
CLI_NAMES = [
    "crawl4ai-doctor.exe",
    "crawl4ai-setup.exe",
    "browser-use.exe",
    "scrapling.exe",
    "scrapy.exe",
    "markitdown.exe",
    "playwright.exe",
]
SECRET_ENV = [
    "FIRECRAWL_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "BROWSER_USE_API_KEY",
    "GOOGLE_API_KEY",
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
]


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 20) -> dict:
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def package_versions(python_exe: Path) -> dict:
    if not python_exe.exists():
        return {"ok": False, "error": f"Python not found: {python_exe}"}

    code = """
import importlib, importlib.metadata as md, json
packages = {
    "firecrawl-py": "firecrawl",
    "crawl4ai": "crawl4ai",
    "browser-use": "browser_use",
    "scrapy": "scrapy",
    "markitdown": "markitdown",
    "scrapling": "scrapling",
    "autoscraper": "autoscraper",
    "curl_cffi": "curl_cffi",
    "duckduckgo-search": "duckduckgo_search",
    "ddgs": "ddgs",
    "playwright": "playwright",
}
out = {}
for dist, module in packages.items():
    item = {"distribution": dist, "module": module}
    try:
        item["version"] = md.version(dist)
    except Exception as exc:
        item["version_error"] = str(exc)
    try:
        importlib.import_module(module)
        item["import_ok"] = True
    except Exception as exc:
        item["import_ok"] = False
        item["import_error"] = f"{type(exc).__name__}: {exc}"
    out[dist] = item
print(json.dumps(out, ensure_ascii=False))
"""
    result = run([str(python_exe), "-c", code], timeout=90)
    if not result["ok"]:
        return result
    try:
        return json.loads(result["stdout"])
    except json.JSONDecodeError:
        return {"ok": False, "raw": result}


def node_modules(node_root: Path) -> dict:
    if not node_root.exists():
        return {"ok": False, "error": f"Node root not found: {node_root}"}
    script = """
const modules = ["crawlee", "@mendable/firecrawl-js", "playwright"];
const out = {};
for (const name of modules) {
  try {
    const pkgPath = require.resolve(name + "/package.json");
    const pkg = require(pkgPath);
    out[name] = { ok: true, version: pkg.version, package_json: pkgPath };
  } catch (err) {
    try {
      require(name);
      out[name] = { ok: true, version: null };
    } catch (err2) {
      out[name] = { ok: false, error: err2.message };
    }
  }
}
console.log(JSON.stringify(out));
"""
    result = run(["node", "-e", script], cwd=node_root, timeout=60)
    if not result["ok"]:
        return result
    return json.loads(result["stdout"])


def cli_paths(python_exe: Path) -> dict:
    scripts_dir = python_exe.parent
    out = {}
    for name in CLI_NAMES:
        local = scripts_dir / name
        found = local if local.exists() else shutil.which(name)
        out[name] = str(found) if found else None
    return out


def browser_check(python_exe: Path) -> dict:
    code = """
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("data:text/html,<title>ok</title><h1>Hello</h1>")
    print(page.title() + "|" + page.locator("h1").inner_text())
    browser.close()
"""
    return run([str(python_exe), "-c", code], timeout=60)


def wsl_curl_impersonate() -> dict:
    if not shutil.which("wsl"):
        return {"ok": False, "error": "wsl.exe not found"}
    script = (
        'export PATH="$HOME/.local/bin:$PATH"; '
        'export LD_LIBRARY_PATH="$HOME/.local/share/global-search/curl-impersonate-v0.6.1:${LD_LIBRARY_PATH:-}"; '
        'for c in curl_chrome116 curl_chrome110 curl_chrome101 curl-impersonate-chrome curl-impersonate-ff; do '
        'if command -v "$c" >/dev/null 2>&1; then printf "%s=%s\\n" "$c" "$(command -v "$c")"; fi; done'
    )
    result = run(["wsl", "-e", "bash", "-lc", script], timeout=30)
    wrappers = {}
    if result.get("stdout"):
        for line in result["stdout"].splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                wrappers[key] = value
    return {"ok": bool(wrappers), "wrappers": wrappers, "raw": result}


def env_keys() -> dict:
    return {name: bool(os.environ.get(name)) for name in SECRET_ENV}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe route-web-research local toolchain")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--browser", action="store_true", help="Launch Chromium to verify browser runtime")
    args = parser.parse_args()

    report = {
        "python": str(DEFAULT_PYTHON),
        "node_root": str(DEFAULT_NODE_ROOT),
        "python_packages": package_versions(DEFAULT_PYTHON),
        "node_modules": node_modules(DEFAULT_NODE_ROOT),
        "cli_paths": cli_paths(DEFAULT_PYTHON),
        "env_keys_present": env_keys(),
        "wsl_curl_impersonate": wsl_curl_impersonate(),
    }
    if args.browser:
        report["browser_runtime"] = browser_check(DEFAULT_PYTHON)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for key, value in report.items():
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
