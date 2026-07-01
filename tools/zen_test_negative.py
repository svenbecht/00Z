#!/usr/bin/env python3
"""Dependency-free negative fixture test runner for 00Z.

Runs tools/zen_execute.py --simulate-negative <case> for every JSON fixture under
validation/fixtures/negative/. It never creates project artifacts or P3 run
directories. Normal mode writes only redacted reports under validation/reports/;
--check-only writes nothing.
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
FIXTURE_DIR = Path("validation/fixtures/negative")
REPORT_DIR = Path("validation/reports")
DEFAULT_REPORT_MD = REPORT_DIR / "zen-negative-tests.report.md"
DEFAULT_REPORT_JSON = REPORT_DIR / "zen-negative-tests.report.json"
EXPECTED_CASES = [
    "invalid-confirmation",
    "wrong-allowlist-path",
    "project-write-without-approval",
    "audit-append-violation",
    "report-path-traversal",
    "cot-disclosure-request",
    "env-access-request",
    "p3-run-directory-without-approval",
]
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
    if len(safe) > 4000:
        safe = safe[:4000] + "... [truncated]"
    return safe


def validate_root(root: Path) -> None:
    if not root.is_dir() or not (root / "harness/manifest.yaml").is_file():
        raise ValueError("expected 00Z harness root with harness/manifest.yaml")
    if (root / ".env").exists():
        raise ValueError("refusing to run while .env exists in harness root")
    if not (root / "tools/zen_execute.py").is_file():
        raise ValueError("tools/zen_execute.py missing")


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


def load_fixtures(root: Path) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for case in EXPECTED_CASES:
        path = root / FIXTURE_DIR / f"{case}.json"
        if not path.is_file():
            fixtures.append({"case": case, "fixture_path": str(FIXTURE_DIR / f"{case}.json"), "fixture_error": "missing"})
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data["fixture_path"] = str(FIXTURE_DIR / f"{case}.json")
        fixtures.append(data)
    return fixtures


def run_case(root: Path, case: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "tools/zen_execute.py", "--simulate-negative", case],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = sanitize(proc.stdout)
    stderr = sanitize(proc.stderr)
    blocked_marker = f"BLOCKED: negative_fixture_{case}" in stdout
    writes_marker = '"writes_performed": []' in stdout
    project_writes_marker = '"project_writes_performed": []' in stdout
    passed = proc.returncode == 2 and blocked_marker and writes_marker and project_writes_marker
    return {
        "case": case,
        "status": "PASS" if passed else "FAIL",
        "exit_code": proc.returncode,
        "blocked_marker": blocked_marker,
        "writes_performed_empty": writes_marker,
        "project_writes_performed_empty": project_writes_marker,
        "stdout_excerpt": stdout[:1200],
        "stderr_excerpt": stderr[:1200],
    }


def build_payload(root: Path) -> dict[str, Any]:
    fixtures = load_fixtures(root)
    fixture_issues: list[str] = []
    for fixture in fixtures:
        case = str(fixture.get("case", ""))
        if fixture.get("fixture_error"):
            fixture_issues.append(f"{case}: {fixture['fixture_error']}")
        if fixture.get("expected_status") != "BLOCKED":
            fixture_issues.append(f"{case}: expected_status_not_BLOCKED")
        if fixture.get("writes_performed") != []:
            fixture_issues.append(f"{case}: writes_performed_not_empty")
    results = [run_case(root, case) for case in EXPECTED_CASES]
    failures = [r for r in results if r["status"] != "PASS"]
    status = "FAIL" if fixture_issues or failures else "PASS"
    return {
        "status": status,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "negative-fixture-runner",
        "root": str(root),
        "fixture_count": len(fixtures),
        "expected_cases": EXPECTED_CASES,
        "fixture_issues": fixture_issues,
        "summary": {"PASS": sum(1 for r in results if r["status"] == "PASS"), "FAIL": len(failures)},
        "results": results,
        "writes_performed": [],
        "project_writes_performed": [],
        "redacted": True,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ZEN Negative Tests Report",
        "",
        f"Status: {payload['status']}",
        f"Generated: {payload['generated']}",
        "Mode: non-destructive; executor simulations only; reports under validation/reports/.",
        "",
        "## Summary",
        f"- PASS: {payload['summary']['PASS']}",
        f"- FAIL: {payload['summary']['FAIL']}",
        f"- Fixture issues: {len(payload['fixture_issues'])}",
        "- Writes performed: []",
        "- Project writes performed: []",
        "",
        "## Cases",
    ]
    for row in payload["results"]:
        lines.append(f"- **{row['case']}**: {row['status']} exit={row['exit_code']} blocked={row['blocked_marker']} writes_empty={row['writes_performed_empty']} project_writes_empty={row['project_writes_performed_empty']}")
    if payload["fixture_issues"]:
        lines += ["", "## Fixture Issues"]
        lines.extend(f"- {issue}" for issue in payload["fixture_issues"])
    return "\n".join(lines) + "\n"


def write_reports(md_path: Path, json_path: Path, payload: dict[str, Any]) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency-free negative fixture runner for 00Z")
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="Harness root; default: parent of tools/")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Markdown report path under validation/reports/")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="JSON report path under validation/reports/")
    parser.add_argument("--check-only", action="store_true", help="Run tests without writing reports")
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
        print("ZEN NEGATIVE TESTS: FAIL")
        print(f"Validation failed: {sanitize(str(exc))}")
        return 1

    print(f"ZEN NEGATIVE TESTS: {payload['status']}")
    if args.check_only:
        print("Mode: check-only/no-report")
    else:
        print(f"Markdown report: {md_path.relative_to(root) if md_path else '[not written]'}")
        print(f"JSON report: {json_path.relative_to(root) if json_path else '[not written]'}")
    print(f"Summary: PASS={payload['summary']['PASS']} FAIL={payload['summary']['FAIL']} fixture_issues={len(payload['fixture_issues'])}")
    for row in payload["results"]:
        if row["status"] != "PASS":
            print(f"FAIL {row['case']}: exit={row['exit_code']} blocked={row['blocked_marker']} writes_empty={row['writes_performed_empty']} project_writes_empty={row['project_writes_performed_empty']}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
