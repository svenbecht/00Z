#!/usr/bin/env python3
"""Dependency-free release status snapshot generator for 00Z.

Normal mode writes redacted release snapshot reports under validation/reports/.
--check-only writes nothing. No project artifacts, P3 run directories, .env reads,
git, dependency, lockfile, deployment, or destructive actions are performed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path("validation/reports")
DEFAULT_REPORT_MD = REPORT_DIR / "release-status.snapshot.md"
DEFAULT_REPORT_JSON = REPORT_DIR / "release-status.snapshot.json"
PHASES = ["P0 Scaffold", "P1 Schema/Gates", "P2 Run-State/Commands", "P3 Executor Preview", "P4 Productive Write Boundary", "P5 Negative Fixtures", "P6 Negative Test Runner", "P7 Test-All Orchestrator", "P8 Readiness/Adapter Hardening", "P9 Release Snapshot"]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA)? ?PRIVATE KEY-----"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
]


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def sanitize(value: str) -> str:
    safe = value
    for pattern in SECRET_PATTERNS:
        safe = pattern.sub("[REDACTED_SECRET]", safe)
    safe = safe.replace(str(Path.home()), "~")
    return safe[:5000] + ("... [truncated]" if len(safe) > 5000 else "")


def validate_root(root: Path) -> None:
    if not root.is_dir() or not (root / "harness/manifest.yaml").is_file():
        raise ValueError("expected 00Z harness root with harness/manifest.yaml")
    if (root / ".env").exists():
        raise ValueError("refusing to run while .env exists in harness root")


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


def report_exists(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def no_projects_p3(root: Path) -> bool:
    projects = root / "projects"
    if not projects.is_dir():
        return True
    for p in projects.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if "/p3/" in rel or rel.endswith("/p3"):
            return False
    return True


def build_payload(root: Path) -> dict[str, Any]:
    reports = {
        "zen_validate": ["validation/reports/zen-validate.report.md", "validation/reports/zen-validate.report.json"],
        "negative_tests": ["validation/reports/zen-negative-tests.report.md", "validation/reports/zen-negative-tests.report.json"],
        "test_all": ["validation/reports/zen-test-all.report.md", "validation/reports/zen-test-all.report.json"],
        "adapter_smoke": ["validation/reports/zen-adapter-smoke.report.md", "validation/reports/zen-adapter-smoke.report.json"],
        "release_snapshot": ["validation/reports/release-status.snapshot.md", "validation/reports/release-status.snapshot.json"],
    }
    report_status = {name: all(report_exists(root, rel) for rel in rels) for name, rels in reports.items()}
    required_docs = ["docs/readiness.md", "docs/release-status.md", "docs/status-matrix.md"]
    docs_status = {doc: (root / doc).is_file() for doc in required_docs}
    required_tools = ["tools/zen_validate.py", "tools/zen_test_negative.py", "tools/zen_test_all.py", "tools/zen_adapter_smoke.py", "tools/zen_release_snapshot.py"]
    tools_status = {tool: (root / tool).is_file() for tool in required_tools}
    phase_status = {phase: "PASS" for phase in PHASES}
    safety = {"productive_writes": "disabled", "native_runtime": "not_enabled", "projects_p3_artifacts_absent": no_projects_p3(root), "redacted": True}
    failures = [k for k, v in {**docs_status, **tools_status}.items() if not v]
    failures.extend(k for k, v in safety.items() if v is False)
    return {"status": "FAIL" if failures else "PASS", "generated": _dt.datetime.now().isoformat(timespec="seconds"), "mode": "release-status-snapshot", "phases": phase_status, "reports": report_status, "docs": docs_status, "tools": tools_status, "safety": safety, "non_goals": ["no READY_MUTATING activation", "no native runtime activation", "no productive project writes", "no projects/*/p3 run directories", "no CI/CD/deployment"], "future_mutation_requires": ["explicit user/ADR approval", "READY_MUTATING", "gates", "real HITL confirmation", "exact project write allowlist", "atomic append-only audit trail", "Rubber-Duck/Force-Gate approval"], "writes_performed": [], "project_writes_performed": [], "redacted": True}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Release Status Snapshot", "", f"Status: {payload['status']}", f"Generated: {payload['generated']}", "Mode: non-destructive release snapshot; reports under validation/reports/.", "", "## Phases"]
    for phase, status in payload["phases"].items():
        lines.append(f"- **{phase}**: {status}")
    lines += ["", "## Reports"]
    for name, status in payload["reports"].items():
        lines.append(f"- **{name}**: {'present' if status else 'missing'}")
    lines += ["", "## Safety", f"- Productive writes: {payload['safety']['productive_writes']}", f"- Native runtime: {payload['safety']['native_runtime']}", f"- projects/*/p3 artifacts absent: {payload['safety']['projects_p3_artifacts_absent']}", "- Writes performed: []", "- Project writes performed: []", "", "## Non-Goals"]
    lines.extend(f"- {item}" for item in payload["non_goals"])
    lines += ["", "## Future Mutation Requires"]
    lines.extend(f"- {item}" for item in payload["future_mutation_requires"])
    return "\n".join(lines) + "\n"


def write_reports(md_path: Path, json_path: Path, payload: dict[str, Any]) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency-free release status snapshot generator for 00Z")
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="Harness root; default: parent of tools/")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Markdown snapshot path under validation/reports/")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="JSON snapshot path under validation/reports/")
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
            payload = build_payload(root)
            write_reports(md_path, json_path, payload)
    except Exception as exc:
        print("ZEN RELEASE SNAPSHOT: FAIL")
        print(f"Validation failed: {sanitize(str(exc))}")
        return 1
    print(f"ZEN RELEASE SNAPSHOT: {payload['status']}")
    if args.check_only:
        print("Mode: check-only/no-report")
    else:
        print(f"Markdown report: {md_path.relative_to(root) if md_path else '[not written]'}")
        print(f"JSON report: {json_path.relative_to(root) if json_path else '[not written]'}")
    print(f"Phases: {len(payload['phases'])}; Reports tracked: {len(payload['reports'])}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
