#!/usr/bin/env python3
"""Dependency-free local test-all orchestrator for 00Z.

Runs only non-destructive checks:
- tools/zen_validate.py --check-only
- tools/zen_test_negative.py --check-only
- read-only/dry-run executor smoke tests

Normal mode writes only redacted reports under validation/reports/;
--check-only writes nothing. No project artifacts, P3 run directories, .env reads,
git, dependency, lockfile, deployment, or destructive actions are performed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path("validation/reports")
DEFAULT_REPORT_MD = REPORT_DIR / "zen-test-all.report.md"
DEFAULT_REPORT_JSON = REPORT_DIR / "zen-test-all.report.json"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA)? ?PRIVATE KEY-----"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
]
REDACTION = "[REDACTED_SECRET]"


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def sanitize(value: str) -> str:
    safe = value
    for pattern in SECRET_PATTERNS:
        safe = pattern.sub(REDACTION, safe)
    safe = safe.replace(str(Path.home()), "~")
    if len(safe) > 5000:
        safe = safe[:5000] + "... [truncated]"
    return safe


def validate_root(root: Path) -> None:
    if not root.is_dir() or not (root / "harness/manifest.yaml").is_file():
        raise ValueError("expected 00Z harness root with harness/manifest.yaml")
    if (root / ".env").exists():
        raise ValueError("refusing to run while .env exists in harness root")
    for required in ["tools/zen_validate.py", "tools/zen_test_negative.py", "tools/zen_execute.py"]:
        if not (root / required).is_file():
            raise ValueError(f"required tool missing: {required}")


def safe_report_path(root: Path, value: str | None, default: Path, expected_suffix: str) -> Path:
    candidate = Path(value) if value else default
    path = candidate.resolve(strict=False) if candidate.is_absolute() else (root / candidate).resolve(strict=False)
    reports_root_raw = root / REPORT_DIR
    reports_root = reports_root_raw.resolve(strict=False)
    if reports_root_raw.exists() and reports_root_raw.is_symlink():
        raise ValueError("validation/reports must not be a symlink")
    try:
        path.relative_to(reports_root)
    except ValueError:
        raise ValueError("report path must stay under validation/reports/")
    if path.suffix != expected_suffix:
        raise ValueError(f"report path must use {expected_suffix} suffix")
    if path.exists() and path.is_symlink():
        raise ValueError("report file must not be a symlink")
    if not is_within(path.parent, root):
        raise ValueError("report parent must stay inside harness root")
    return path


def run_command(root: Path, name: str, argv: list[str], expected_exit: int, required_markers: list[str]) -> dict[str, Any]:
    proc = subprocess.run(argv, cwd=root, text=True, capture_output=True, check=False)
    stdout = sanitize(proc.stdout)
    stderr = sanitize(proc.stderr)
    markers = {marker: marker in stdout for marker in required_markers}
    passed = proc.returncode == expected_exit and all(markers.values())
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "argv": argv,
        "exit_code": proc.returncode,
        "expected_exit": expected_exit,
        "markers": markers,
        "stdout_excerpt": stdout[:1500],
        "stderr_excerpt": stderr[:1500],
    }


def check_no_project_artifacts(root: Path) -> dict[str, Any]:
    hits: list[str] = []
    projects = root / "projects"
    if projects.is_dir():
        for p in projects.rglob("*"):
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:
                continue
            if "/p3/" in rel or rel.endswith("/p3"):
                hits.append(rel)
    return {"name": "no_projects_p3_artifacts", "status": "PASS" if not hits else "FAIL", "hits": hits[:50]}


def build_payload(root: Path) -> dict[str, Any]:
    checks = [
        run_command(root, "validate_check_only", [sys.executable, "tools/zen_validate.py", "--check-only"], 0, ["ZEN VALIDATE: PASS", "Mode: check-only/no-write"]),
        run_command(root, "negative_check_only", [sys.executable, "tools/zen_test_negative.py", "--check-only"], 0, ["ZEN NEGATIVE TESTS: PASS", "Mode: check-only/no-report"]),
        run_command(root, "executor_status_dry_run", [sys.executable, "tools/zen_execute.py", "--command", "ZEN STATUS"], 0, ["ZEN EXECUTE DRY-RUN: PASS", '"writes_performed": []']),
        run_command(root, "executor_explain_boundary", [sys.executable, "tools/zen_execute.py", "--explain-project-write-boundary"], 0, ["ZEN PROJECT WRITE BOUNDARY: DISABLED", '"project_writes_performed": []']),
        run_command(root, "executor_attempt_project_write_blocked", [sys.executable, "tools/zen_execute.py", "--attempt-project-write"], 2, ["BLOCKED: productive_project_write_boundary_disabled", '"project_writes_performed": []']),
        check_no_project_artifacts(root),
    ]
    failures = [check for check in checks if check["status"] != "PASS"]
    return {
        "status": "FAIL" if failures else "PASS",
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "local-test-all-non-destructive",
        "root": str(root),
        "summary": {"PASS": sum(1 for c in checks if c["status"] == "PASS"), "FAIL": len(failures)},
        "checks": checks,
        "writes_performed": [],
        "project_writes_performed": [],
        "redacted": True,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ZEN Test-All Report",
        "",
        f"Status: {payload['status']}",
        f"Generated: {payload['generated']}",
        "Mode: non-destructive local orchestration; reports under validation/reports/.",
        "",
        "## Summary",
        f"- PASS: {payload['summary']['PASS']}",
        f"- FAIL: {payload['summary']['FAIL']}",
        "- Writes performed: []",
        "- Project writes performed: []",
        "",
        "## Checks",
    ]
    for check in payload["checks"]:
        if "exit_code" in check:
            lines.append(f"- **{check['name']}**: {check['status']} exit={check['exit_code']} expected={check['expected_exit']}")
        else:
            lines.append(f"- **{check['name']}**: {check['status']}")
    return "\n".join(lines) + "\n"


def write_reports(md_path: Path, json_path: Path, payload: dict[str, Any]) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency-free local test-all runner for 00Z")
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="Harness root; default: parent of tools/")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Markdown report path under validation/reports/")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="JSON report path under validation/reports/")
    parser.add_argument("--check-only", action="store_true", help="Run without writing reports")
    args = parser.parse_args()

    try:
        root = Path(args.root).resolve()
        validate_root(root)
        md_path = safe_report_path(root, args.report_md, DEFAULT_REPORT_MD, ".md") if not args.check_only else None
        json_path = safe_report_path(root, args.report_json, DEFAULT_REPORT_JSON, ".json") if not args.check_only else None
        payload = build_payload(root)
        if not args.check_only and md_path is not None and json_path is not None:
            write_reports(md_path, json_path, payload)
    except Exception as exc:
        print("ZEN TEST ALL: FAIL")
        print(f"Validation failed: {sanitize(str(exc))}")
        return 1

    print(f"ZEN TEST ALL: {payload['status']}")
    if args.check_only:
        print("Mode: check-only/no-report")
    else:
        print(f"Markdown report: {md_path.relative_to(root) if md_path else '[not written]'}")
        print(f"JSON report: {json_path.relative_to(root) if json_path else '[not written]'}")
    print(f"Summary: PASS={payload['summary']['PASS']} FAIL={payload['summary']['FAIL']}")
    for check in payload["checks"]:
        if check["status"] != "PASS":
            print(f"FAIL {check['name']}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
