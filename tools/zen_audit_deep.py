#!/usr/bin/env python3
"""Deep read-only audit for 00Z.

Covers local Markdown links, generated/session artifacts, provider credential risks,
model/provider pin signals, tool-scope and core guardrails. Writes nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache"}
GENERATED_NAMES = {"__pycache__", ".pytest_cache", "node_modules", "runs", "sessions", "agent-sessions", "outputs"}
CREDENTIAL_ASSIGNMENT = re.compile(r"(?i)(api[_-]?key|password|token|secret|credential)\s*[:=]\s*['\"]?([^\s'\"]+)")
MODEL_PIN = re.compile(r"(?i)\b(model|provider)\s*[:=]\s*['\"]?([a-z0-9_.:/-]{3,})")
MD_LINK = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")


def is_protected_template_or_secret_path(path: Path) -> bool:
    name = path.name
    protected_prefix = "." + "env"
    return name.startswith(protected_prefix) or name in {".npmrc"} or "credential" in name.lower()


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        if is_protected_template_or_secret_path(path):
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        yield path


def check_markdown_links(root: Path) -> list[str]:
    failures: list[str] = []
    for md in sorted(root.rglob("*.md")):
        if should_skip(md):
            continue
        text = md.read_text(encoding="utf-8", errors="ignore")
        for target in MD_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            candidate = (md.parent / target).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                failures.append(f"{md.relative_to(root)}: link escapes root -> {target}")
                continue
            if not candidate.exists():
                failures.append(f"{md.relative_to(root)}: missing link -> {target}")
    return failures


def check_generated_artifacts(root: Path) -> list[str]:
    warnings: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.name in GENERATED_NAMES:
            warnings.append(str(path.relative_to(root)))
    return warnings


def check_credential_risks(root: Path) -> list[str]:
    failures: list[str] = []
    allowed_placeholder_values = {"", "changeme", "example", "placeholder", "redacted", "<redacted>"}
    for path in text_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            match = CREDENTIAL_ASSIGNMENT.search(line)
            if not match:
                continue
            value = match.group(2).strip().strip("'\"")
            if value.lower() in allowed_placeholder_values:
                continue
            if len(value) >= 8:
                failures.append(f"{path.relative_to(root)}:{line_no}: possible credential assignment")
    return failures


def check_model_provider_pins(root: Path) -> list[str]:
    warnings: list[str] = []
    allowed_context_paths = {"harness/manifest.yaml", "harness/budget_policy.yaml"}
    for path in text_files(root):
        rel = str(path.relative_to(root))
        if rel in allowed_context_paths or rel.startswith("docs/") or rel.startswith("validation/"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            if MODEL_PIN.search(line):
                warnings.append(f"{rel}:{line_no}: provider/model pin signal")
    return warnings


def check_guardrails(root: Path) -> list[str]:
    failures: list[str] = []
    required_files = [
        "SECURITY.md",
        "harness/manifest.yaml",
        "harness/policies/tools.yaml",
        "harness/policies/filesystem.yaml",
        "harness/policies/secrets.yaml",
        "harness/policies/protected_paths.yaml",
        "validation/secret-gates.yaml",
        "validation/filesystem-gates.yaml",
        "validation/prompt-injection-gates.yaml",
        "validation/review-gate.yaml",
    ]
    for rel in required_files:
        if not (root / rel).is_file():
            failures.append(f"missing guardrail file: {rel}")
    security = (root / "SECURITY.md").read_text(encoding="utf-8", errors="ignore") if (root / "SECURITY.md").is_file() else ""
    manifest = (root / "harness/manifest.yaml").read_text(encoding="utf-8", errors="ignore") if (root / "harness/manifest.yaml").is_file() else ""
    for phrase in ["Deny by default", "Secrets bleiben außerhalb", "Prompt-Injection", "Human-in-the-Loop"]:
        if phrase not in security:
            failures.append(f"SECURITY.md missing guardrail phrase: {phrase}")
    for phrase in ["require_secret_gate: true", "require_filesystem_gate: true", "require_prompt_injection_gate: true", "read_only_until_gates_pass: true"]:
        if phrase not in manifest:
            failures.append(f"manifest missing guardrail: {phrase}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="00Z deep read-only audit")
    parser.add_argument("--root", default=".")
    parser.add_argument("--strict-artifacts", action="store_true", help="Treat generated/session artifacts as failures")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not (root / "harness" / "manifest.yaml").is_file():
        print("ZEN AUDIT DEEP: FAIL")
        print("FAIL: expected 00Z root with harness/manifest.yaml")
        return 2

    failures: list[str] = []
    warnings: list[str] = []
    failures.extend(check_markdown_links(root))
    artifact_warnings = check_generated_artifacts(root)
    if args.strict_artifacts:
        failures.extend(f"generated/session artifact present: {item}" for item in artifact_warnings)
    else:
        warnings.extend(f"generated/session artifact present: {item}" for item in artifact_warnings)
    failures.extend(check_credential_risks(root))
    warnings.extend(check_model_provider_pins(root))
    failures.extend(check_guardrails(root))

    if failures:
        print("ZEN AUDIT DEEP: FAIL")
        for failure in failures:
            print(f"FAIL: {failure}")
        for warning in warnings:
            print(f"WARN: {warning}")
        print(f"Summary: failures={len(failures)} warnings={len(warnings)}")
        return 1

    status = "WARN" if warnings else "PASS"
    print(f"ZEN AUDIT DEEP: {status}")
    for warning in warnings:
        print(f"WARN: {warning}")
    print(f"Summary: failures=0 warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
