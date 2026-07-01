#!/usr/bin/env python3
"""Dependency-free review result validator for 00Z.

Validates reviewer-result JSON artifacts and built-in review fixtures.
Default/check-only mode writes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REVIEWERS = {"security", "code-quality", "docs", "pipeline", "reasoning"}
VERDICTS = {"lgtm", "suggestions", "warnings", "critical"}
SEVERITIES = {"suggestion", "warning", "critical"}
CATEGORIES = REVIEWERS | {"release", "compliance"}
CONFIDENCE = {"low", "medium", "high"}
SOURCES = {"diff", "file", "test", "manifest", "contextFreshnessSignals", "reviewer-inference"}


def expected_fingerprint(finding: dict[str, Any]) -> str:
    parts = [
        str(finding.get("domain", "")),
        str(finding.get("file") or "manifest"),
        str(finding.get("line") or "0"),
        str(finding.get("title", "")),
        str(finding.get("evidence", "")),
    ]
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:16]


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except Exception as exc:  # noqa: BLE001 - dependency-free CLI diagnostics
        return None, [f"{path}: invalid_json: {exc}"]


def validate_result(data: Any, path: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{path}: result must be object"]
    if data.get("schemaVersion") != 1:
        errors.append(f"{path}: schemaVersion must be 1")
    reviewer = data.get("reviewer")
    verdict = data.get("verdict")
    findings = data.get("findings")
    if reviewer not in REVIEWERS:
        errors.append(f"{path}: invalid reviewer {reviewer!r}")
    if verdict not in VERDICTS:
        errors.append(f"{path}: invalid verdict {verdict!r}")
    if not isinstance(findings, list):
        errors.append(f"{path}: findings must be array")
        return errors
    has_critical = False
    for idx, finding in enumerate(findings):
        prefix = f"{path}: findings[{idx}]"
        if not isinstance(finding, dict):
            errors.append(f"{prefix}: must be object")
            continue
        severity = finding.get("severity")
        domain = finding.get("domain")
        category = finding.get("category")
        confidence = finding.get("confidence")
        source = finding.get("source")
        if severity not in SEVERITIES:
            errors.append(f"{prefix}: invalid severity")
        if category not in CATEGORIES:
            errors.append(f"{prefix}: invalid category")
        if domain not in REVIEWERS:
            errors.append(f"{prefix}: invalid domain")
        if reviewer in REVIEWERS and domain in REVIEWERS and domain != reviewer:
            errors.append(f"{prefix}: domain must match reviewer")
        if confidence not in CONFIDENCE:
            errors.append(f"{prefix}: invalid confidence")
        if source not in SOURCES:
            errors.append(f"{prefix}: invalid source")
        for field, limit in [("title", 120), ("evidence", 500), ("recommendation", 500)]:
            value = finding.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}: {field} required")
            elif len(value) > limit:
                errors.append(f"{prefix}: {field} too long")
        has_file = "file" in finding
        has_line = "line" in finding
        if has_file != has_line:
            errors.append(f"{prefix}: file and line must appear together")
        if has_line and (not isinstance(finding.get("line"), int) or finding.get("line") < 1):
            errors.append(f"{prefix}: line must be positive integer")
        if severity == "critical":
            has_critical = True
            blocking = finding.get("blockingReason")
            if not isinstance(blocking, str) or not blocking.strip():
                errors.append(f"{prefix}: critical requires blockingReason")
            elif len(blocking) > 300:
                errors.append(f"{prefix}: blockingReason too long")
            if confidence == "low":
                errors.append(f"{prefix}: critical confidence must not be low")
        elif "blockingReason" in finding:
            errors.append(f"{prefix}: non-critical must not include blockingReason")
        fp = finding.get("fingerprint")
        if not isinstance(fp, str) or len(fp) != 16:
            errors.append(f"{prefix}: fingerprint must be 16 hex chars")
        elif fp != expected_fingerprint(finding):
            errors.append(f"{prefix}: fingerprint mismatch expected={expected_fingerprint(finding)} actual={fp}")
    if verdict == "critical" and not has_critical:
        errors.append(f"{path}: critical verdict requires at least one critical finding")
    return errors


def validate_file(path: Path) -> list[str]:
    data, errors = load_json(path)
    if errors:
        return errors
    return validate_result(data, path)


def iter_json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob("*.json") if p.is_file())
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency-free 00Z review result validator")
    parser.add_argument("--root", default=".")
    parser.add_argument("--run-dir", help="Optional review run directory or reviewer-results JSON file")
    parser.add_argument("--check-only", action="store_true", help="No-write mode; default also writes nothing")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "harness" / "manifest.yaml").is_file():
        print("Root validation failed: expected a 00Z harness root with harness/manifest.yaml")
        return 2

    errors: list[str] = []
    valid_dir = root / "validation" / "fixtures" / "review" / "valid"
    invalid_dir = root / "validation" / "fixtures" / "review" / "invalid"

    checked_valid = 0
    for path in iter_json_files(valid_dir):
        checked_valid += 1
        errors.extend(validate_file(path))

    checked_invalid = 0
    for path in iter_json_files(invalid_dir):
        checked_invalid += 1
        fixture_errors = validate_file(path)
        if not fixture_errors:
            errors.append(f"{path}: invalid fixture unexpectedly passed")

    checked_run = 0
    if args.run_dir:
        run_path = Path(args.run_dir)
        if not run_path.is_absolute():
            run_path = root / run_path
        target = run_path / "reviewer-results" if run_path.is_dir() and (run_path / "reviewer-results").is_dir() else run_path
        for path in iter_json_files(target):
            checked_run += 1
            errors.extend(validate_file(path))

    if errors:
        print("ZEN REVIEW VALIDATE: FAIL")
        print(f"Mode: {'check-only/no-write' if args.check_only else 'no-write'}")
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print("ZEN REVIEW VALIDATE: PASS")
    print(f"Mode: {'check-only/no-write' if args.check_only else 'no-write'}")
    print(f"Summary: valid_fixtures={checked_valid} invalid_fixtures={checked_invalid} run_results={checked_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
