#!/usr/bin/env python3
"""Controlled, dry-run-first executor preview for 00Z.

Default mode writes nothing. Controlled report modes write only redacted boundary
artifacts under validation/reports/. No project artifacts, P3 run directories,
.env reads, git, dependency or lockfile actions are performed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Any

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path("validation/reports")
DEFAULT_PREVIEW_REPORT = REPORT_DIR / "zen-execute.preview.json"
DEFAULT_HITL_PREVIEW_REPORT = REPORT_DIR / "zen-execute.hitl-preview.json"
DEFAULT_CONFIRMATION_REPORT = REPORT_DIR / "zen-execute.confirmation.json"
DEFAULT_AUDIT_PREVIEW_LOG = REPORT_DIR / "zen-execute.audit-preview.jsonl"
DEFAULT_RUN_MANIFEST_PREVIEW = REPORT_DIR / "zen-execute.run-manifest.preview.json"
ZEN_COMMANDS = {"ZEN NEW", "ZEN MEMORY INIT", "ZEN NEW BUILD", "ZEN STATUS", "ZEN PLAN", "ZEN SNAPSHOT", "ZEN P1", "ZEN P2", "ZEN P3", "ZEN RESET", "ZEN VALIDATE"}
PIPELINES = {"p1", "p2", "p3"}
PREVIEW_SCHEMA = "harness/schemas/audit-preview.schema.json"
HITL_PREVIEW_SCHEMA = "harness/schemas/hitl-preview.schema.json"
CONFIRMATION_SCHEMA = "harness/schemas/confirmation-report.schema.json"
AUDIT_PREVIEW_EVENT_SCHEMA = "harness/schemas/audit-preview-event.schema.json"
RUN_MANIFEST_PREVIEW_SCHEMA = "harness/schemas/run-manifest-preview.schema.json"
NEGATIVE_CASES = {
    "invalid-confirmation": "real confirmation schema requirements are not satisfied",
    "wrong-allowlist-path": "target path is outside the exact productive project write allowlist",
    "project-write-without-approval": "explicit user approval and READY_MUTATING are missing",
    "audit-append-violation": "audit operation must be atomic append-only and redacted",
    "report-path-traversal": "report path must remain under validation/reports/ without traversal",
    "cot-disclosure-request": "internal reasoning traces must not be disclosed",
    "env-access-request": "protected environment files are never read or written",
    "p3-run-directory-without-approval": "P3 run directory creation requires explicit approval and READY_MUTATING",
}


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def validate_root(root: Path) -> None:
    if not root.is_dir() or not (root / "harness/manifest.yaml").is_file():
        raise ValueError("expected 00Z harness root with harness/manifest.yaml")
    if (root / ".env").exists():
        raise ValueError("refusing to operate while .env exists in harness root")


def negative_simulation(case: str) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "case": case,
        "reason": NEGATIVE_CASES[case],
        "mode": "negative_fixture_simulation",
        "writes_performed": [],
        "project_writes_performed": [],
        "redacted": True,
    }


def explain_project_write_boundary() -> dict[str, Any]:
    return {
        "status": "DISABLED",
        "reason": "Productive project writes require explicit ADR/User approval and are not active in this harness phase.",
        "requirements": ["READY_MUTATING", "policy_gate", "filesystem_gate", "secret_gate", "prompt_injection_gate", "real_hitl_confirmation", "atomic_audit_trail"],
        "allowed_now": "validation/reports controlled boundary-test artifacts only",
        "project_writes_performed": [],
        "redacted": True,
    }


def safe_report_path(root: Path, value: str | None, suffix: str, default_path: Path) -> Path:
    candidate = Path(value) if value else default_path
    path = candidate.resolve(strict=False) if candidate.is_absolute() else (root / candidate).resolve(strict=False)
    reports_root_raw = root / REPORT_DIR
    reports_root = reports_root_raw.resolve(strict=False)
    if not reports_root_raw.is_dir() or reports_root_raw.is_symlink():
        raise ValueError("validation/reports must exist and must not be a symlink")
    try:
        path.relative_to(reports_root)
    except ValueError:
        raise ValueError("report path must stay under validation/reports/")
    if not path.name.endswith(suffix):
        raise ValueError(f"report must end with {suffix}")
    if path.exists() and path.is_symlink():
        raise ValueError("report file must not be a symlink")
    if not is_within(path.parent, root):
        raise ValueError("report parent must stay inside harness root")
    return path


def load_schema(root: Path, schema_rel: str) -> dict[str, Any]:
    return json.loads((root / schema_rel).read_text(encoding="utf-8"))


def validate_required(root: Path, schema_rel: str, obj: dict[str, Any], label: str) -> None:
    schema = load_schema(root, schema_rel)
    for field in schema.get("required", []):
        if field not in obj:
            raise ValueError(f"{label} missing required field: {field}")


def hitl_confirmation_id(now: _dt.datetime) -> str:
    return "hitl_" + now.strftime("%Y%m%dT%H%M%SZ") + "_preview"


def target_paths_for(command: str | None, pipeline: str | None) -> tuple[str, list[str], str]:
    target = command or (f"ZEN {pipeline.upper()}" if pipeline else "ZEN STATUS")
    event_type = "pipeline_run" if pipeline else "tool_call"
    target_paths = ["harness/state_machine.yaml", "harness/runtime.yaml"]
    if pipeline:
        target_paths.append(f"harness/pipelines/{pipeline}.yaml")
    elif command:
        command_id = command.lower().replace(" ", "-")
        if command_id == "zen-new-build":
            command_id = "zen-build-agent"
        if command_id in {"zen-p1", "zen-p2", "zen-p3"}:
            target_paths.append(f"harness/pipelines/{command_id[-2:]}.yaml")
        else:
            target_paths.append(f"harness/commands/{command_id}.yaml")
    return target, target_paths, event_type


def build_hitl_preview(now: _dt.datetime, target: str, target_paths: list[str]) -> dict[str, Any]:
    return {"confirmation_id": hitl_confirmation_id(now), "run_id": "dry-run-preview", "actor": "tools/zen_execute.py", "scope": target, "risk_level": "medium", "target_paths": target_paths, "expires_at": (now + _dt.timedelta(minutes=15)).isoformat(timespec="seconds"), "decision": "preview_only", "effective_confirmation": False, "redacted": True, "preview_only": True, "schema": HITL_PREVIEW_SCHEMA}


def build_confirmation_report(now: _dt.datetime, target: str, target_paths: list[str]) -> dict[str, Any]:
    return {"confirmation_id": hitl_confirmation_id(now), "run_id": "dry-run-preview", "actor": "tools/zen_execute.py", "scope": target, "risk_level": "medium", "target_paths": target_paths, "issued_at": now.isoformat(timespec="seconds"), "expires_at": (now + _dt.timedelta(minutes=15)).isoformat(timespec="seconds"), "decision": "approved_for_boundary_test", "effective_confirmation": True, "not_project_authorization": True, "production_scope": False, "redacted": True, "schema": CONFIRMATION_SCHEMA}


def build_run_manifest_preview(now: _dt.datetime) -> dict[str, Any]:
    return {"run_id": "dry-run-preview", "project": "preview-project", "pipeline": "p3", "run_state": "RUNNING", "artifact_lifecycle": ["transient", "draft", "approved", "persisted", "archived", "rejected"], "artifact_zones": {"draft": "projects/{project}/p3/{date}_{sequence}/draft/", "approved": "projects/{project}/p3/{date}_{sequence}/approved/", "reports": "projects/{project}/p3/{date}_{sequence}/reports/"}, "audit_log": "projects/preview-project/p3/preview-run/reports/AUDIT.jsonl", "dry_run": True, "preview_only": True, "not_project_manifest": True, "redacted": True, "schema": RUN_MANIFEST_PREVIEW_SCHEMA}


def build_audit_preview(root: Path, command: str | None, pipeline: str | None, include_hitl: bool, simulate_audit_append: bool) -> dict[str, Any]:
    now = _dt.datetime.now(_dt.timezone.utc)
    target, target_paths, event_type = target_paths_for(command, pipeline)
    preview: dict[str, Any] = {"timestamp": now.isoformat(timespec="seconds"), "run_id": "dry-run-preview", "actor": "tools/zen_execute.py", "event_type": event_type, "target_paths": target_paths, "risk_level": "low", "trust_zone": "harness_policy", "decision": "dry_run_only_no_mutation", "result": "planned_not_executed", "redacted": True, "command": target, "mode": "dry-run", "writes_performed": [], "schema": PREVIEW_SCHEMA, "next_required_state": "READY_MUTATING required before any persistence" if target in {"ZEN NEW", "ZEN MEMORY INIT", "ZEN NEW BUILD", "ZEN PLAN", "ZEN SNAPSHOT", "ZEN P3"} else "READY_READONLY sufficient for preview"}
    if include_hitl:
        hitl = build_hitl_preview(now, target, target_paths)
        validate_required(root, HITL_PREVIEW_SCHEMA, hitl, "hitl preview")
        preview["hitl_preview"] = hitl
    if simulate_audit_append:
        preview["audit_append_simulation"] = {"mode": "simulation_only", "effective_append": False, "would_append_to": "projects/{project}/p3/{date}_{sequence}/reports/AUDIT.jsonl", "writes_performed": [], "redacted": True}
    validate_required(root, PREVIEW_SCHEMA, preview, "audit preview")
    return preview


def build_audit_preview_event(preview: dict[str, Any]) -> dict[str, Any]:
    return {"timestamp": preview["timestamp"], "run_id": preview["run_id"], "actor": "tools/zen_execute.py", "event_type": preview["event_type"], "target_paths": preview["target_paths"], "risk_level": preview["risk_level"], "trust_zone": preview["trust_zone"], "decision": "append_preview_boundary_test", "result": "preview_event_appended_to_validation_reports_only", "effective_append": True, "not_project_audit": True, "redacted": True, "schema": AUDIT_PREVIEW_EVENT_SCHEMA}


def write_json_report(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl_report(path: Path, obj: dict[str, Any]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run-first executor preview for 00Z.", epilog="Default is no-write. Controlled writes are limited to validation/reports/.")
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="Harness root; default: parent of tools/")
    parser.add_argument("--command", choices=sorted(ZEN_COMMANDS), help="ZEN command to preview")
    parser.add_argument("--pipeline", choices=sorted(PIPELINES), help="Pipeline id to preview")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry-run mode; always enabled")
    parser.add_argument("--preview-hitl", action="store_true", help="Include no-write HITL confirmation preview")
    parser.add_argument("--simulate-audit-append", action="store_true", help="Simulate project audit append; never writes project AUDIT.jsonl")
    parser.add_argument("--write-report", action="store_true", help="Write redacted audit preview JSON under validation/reports/*.preview.json")
    parser.add_argument("--write-hitl-preview", action="store_true", help="Write redacted HITL preview JSON under validation/reports/*.hitl-preview.json")
    parser.add_argument("--write-confirmation-report", action="store_true", help="Write controlled confirmation boundary-test report under validation/reports/*.confirmation.json")
    parser.add_argument("--append-audit-preview", action="store_true", help="Append audit preview event only to validation/reports/*.audit-preview.jsonl")
    parser.add_argument("--write-run-manifest-preview", action="store_true", help="Write P3 run manifest preview only under validation/reports/*.run-manifest.preview.json")
    parser.add_argument("--explain-project-write-boundary", action="store_true", help="Explain why productive project writes are disabled; writes nothing")
    parser.add_argument("--attempt-project-write", action="store_true", help="Always BLOCKED; productive project writes are not enabled")
    parser.add_argument("--simulate-negative", choices=sorted(NEGATIVE_CASES), help="Simulate a negative fixture case; always BLOCKED and writes nothing")
    parser.add_argument("--report-json", default=str(DEFAULT_PREVIEW_REPORT), help="Audit preview report path ending in .preview.json")
    parser.add_argument("--hitl-report-json", default=str(DEFAULT_HITL_PREVIEW_REPORT), help="HITL preview report path ending in .hitl-preview.json")
    parser.add_argument("--confirmation-report-json", default=str(DEFAULT_CONFIRMATION_REPORT), help="Confirmation report path ending in .confirmation.json")
    parser.add_argument("--audit-preview-jsonl", default=str(DEFAULT_AUDIT_PREVIEW_LOG), help="Audit preview JSONL path ending in .audit-preview.jsonl")
    parser.add_argument("--run-manifest-preview-json", default=str(DEFAULT_RUN_MANIFEST_PREVIEW), help="Run manifest preview path ending in .run-manifest.preview.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    try:
        validate_root(root)
        if args.explain_project_write_boundary:
            print("ZEN PROJECT WRITE BOUNDARY: DISABLED")
            print(json.dumps(explain_project_write_boundary(), ensure_ascii=False, indent=2))
            return 0
        if args.attempt_project_write:
            print("BLOCKED: productive_project_write_boundary_disabled")
            print(json.dumps(explain_project_write_boundary(), ensure_ascii=False, indent=2))
            return 2
        if args.simulate_negative:
            print(f"BLOCKED: negative_fixture_{args.simulate_negative}")
            print(json.dumps(negative_simulation(args.simulate_negative), ensure_ascii=False, indent=2))
            return 2
        if args.command and args.pipeline:
            raise ValueError("choose either --command or --pipeline, not both")
        now = _dt.datetime.now(_dt.timezone.utc)
        include_hitl = args.preview_hitl or args.write_hitl_preview or args.write_confirmation_report
        preview = build_audit_preview(root, args.command, args.pipeline, include_hitl, args.simulate_audit_append)
        target, target_paths, _ = target_paths_for(args.command, args.pipeline)
        paths: list[tuple[Path, dict[str, Any] | None, str]] = []
        if args.write_report:
            paths.append((safe_report_path(root, args.report_json, ".preview.json", DEFAULT_PREVIEW_REPORT), preview, "Preview report"))
        if args.write_hitl_preview:
            paths.append((safe_report_path(root, args.hitl_report_json, ".hitl-preview.json", DEFAULT_HITL_PREVIEW_REPORT), preview["hitl_preview"], "HITL preview report"))
        if args.write_confirmation_report:
            confirmation = build_confirmation_report(now, target, target_paths)
            validate_required(root, CONFIRMATION_SCHEMA, confirmation, "confirmation report")
            paths.append((safe_report_path(root, args.confirmation_report_json, ".confirmation.json", DEFAULT_CONFIRMATION_REPORT), confirmation, "Confirmation report"))
        audit_event = None
        audit_path = None
        if args.append_audit_preview:
            audit_event = build_audit_preview_event(preview)
            validate_required(root, AUDIT_PREVIEW_EVENT_SCHEMA, audit_event, "audit preview event")
            audit_path = safe_report_path(root, args.audit_preview_jsonl, ".audit-preview.jsonl", DEFAULT_AUDIT_PREVIEW_LOG)
        if args.write_run_manifest_preview:
            manifest = build_run_manifest_preview(now)
            validate_required(root, RUN_MANIFEST_PREVIEW_SCHEMA, manifest, "run manifest preview")
            paths.append((safe_report_path(root, args.run_manifest_preview_json, ".run-manifest.preview.json", DEFAULT_RUN_MANIFEST_PREVIEW), manifest, "Run manifest preview"))
    except Exception as exc:
        print("ZEN EXECUTE DRY-RUN: FAIL")
        print(f"Validation failed: {exc}")
        return 1

    print("ZEN EXECUTE DRY-RUN: PASS")
    print(json.dumps(preview, ensure_ascii=False, indent=2))
    for path, obj, label in paths:
        if obj is not None:
            write_json_report(path, obj)
            print(f"{label}: {path.relative_to(root)}")
    if audit_path is not None and audit_event is not None:
        append_jsonl_report(audit_path, audit_event)
        print(f"Audit preview append: {audit_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
