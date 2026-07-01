#!/usr/bin/env python3
"""Dependency-free adapter smoke checks for 00Z.

Checks Pi/Claude adapter files and docs by text contracts only. Normal mode writes
redacted reports under validation/reports/; --check-only writes nothing.
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
DEFAULT_REPORT_MD = REPORT_DIR / "zen-adapter-smoke.report.md"
DEFAULT_REPORT_JSON = REPORT_DIR / "zen-adapter-smoke.report.json"
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
    return safe[:4000] + ("... [truncated]" if len(safe) > 4000 else "")


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


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def check_adapter(root: Path, adapter: str) -> dict[str, Any]:
    yaml_path = root / "adapters" / adapter / "adapter.yaml"
    doc_path = root / "adapters" / adapter / ("AGENTS.md" if adapter == "pi" else "CLAUDE.md")
    issues: list[str] = []
    if not yaml_path.is_file():
        issues.append("adapter_yaml_missing")
        yaml_text = ""
    else:
        yaml_text = text(yaml_path)
    if not doc_path.is_file():
        issues.append("adapter_doc_missing")
        doc_text = ""
    else:
        doc_text = text(doc_path)
    required_yaml = [
        "runtime_implemented: true",
        "native_runtime_implemented: false",
        "productive_project_writes_enabled: false",
        "blocked_response_prefix: \"BLOCKED:\"",
        "warn_response_prefix: \"WARN:\"",
        "pass_response_prefix: \"PASS:\"",
        "env_files_blocked: true",
        "no_chain_of_thought_disclosure: true",
        "tools/zen_adapter_smoke.py",
        "docs/readiness.md",
    ]
    for marker in required_yaml:
        if marker not in yaml_text:
            issues.append(f"yaml_marker_missing={marker}")
    required_doc = ["BLOCKED:", "WARN:", "PASS:", "no-CoT", "no-env", "no-project-write", "native_runtime_implemented: false", "docs/readiness.md", "tools/zen_adapter_smoke.py"]
    for marker in required_doc:
        if marker not in doc_text:
            issues.append(f"doc_marker_missing={marker}")
    return {"adapter": adapter, "status": "PASS" if not issues else "FAIL", "issues": issues}


def build_payload(root: Path) -> dict[str, Any]:
    checks = [check_adapter(root, "pi"), check_adapter(root, "claude")]
    readiness = root / "docs/readiness.md"
    if not readiness.is_file():
        checks.append({"adapter": "readiness", "status": "FAIL", "issues": ["docs/readiness.md missing"]})
    else:
        rtext = text(readiness)
        markers = ["tools/zen_validate.py --check-only", "tools/zen_test_negative.py --check-only", "tools/zen_test_all.py --check-only", "tools/zen_adapter_smoke.py --check-only", "native_runtime_implemented: false"]
        missing = [m for m in markers if m not in rtext]
        checks.append({"adapter": "readiness", "status": "PASS" if not missing else "FAIL", "issues": [f"readiness_marker_missing={m}" for m in missing]})
    failures = [c for c in checks if c["status"] != "PASS"]
    return {"status": "FAIL" if failures else "PASS", "generated": _dt.datetime.now().isoformat(timespec="seconds"), "mode": "adapter-smoke-read-only", "summary": {"PASS": sum(1 for c in checks if c["status"] == "PASS"), "FAIL": len(failures)}, "checks": checks, "writes_performed": [], "project_writes_performed": [], "redacted": True}


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# ZEN Adapter Smoke Report", "", f"Status: {payload['status']}", f"Generated: {payload['generated']}", "Mode: read-only adapter contract smoke; reports under validation/reports/.", "", "## Summary", f"- PASS: {payload['summary']['PASS']}", f"- FAIL: {payload['summary']['FAIL']}", "- Writes performed: []", "- Project writes performed: []", "", "## Checks"]
    for check in payload["checks"]:
        lines.append(f"- **{check['adapter']}**: {check['status']}")
        for issue in check.get("issues", []):
            lines.append(f"  - {sanitize(issue)}")
    return "\n".join(lines) + "\n"


def write_reports(md_path: Path, json_path: Path, payload: dict[str, Any]) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency-free adapter smoke checks for 00Z")
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
        print("ZEN ADAPTER SMOKE: FAIL")
        print(f"Validation failed: {sanitize(str(exc))}")
        return 1
    print(f"ZEN ADAPTER SMOKE: {payload['status']}")
    if args.check_only:
        print("Mode: check-only/no-report")
    else:
        print(f"Markdown report: {md_path.relative_to(root) if md_path else '[not written]'}")
        print(f"JSON report: {json_path.relative_to(root) if json_path else '[not written]'}")
    print(f"Summary: PASS={payload['summary']['PASS']} FAIL={payload['summary']['FAIL']}")
    for check in payload["checks"]:
        if check["status"] != "PASS":
            print(f"FAIL {check['adapter']}: {', '.join(check.get('issues', []))}")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
