#!/usr/bin/env python3
"""Read-only validator for ZEN VALIDATE.

No external installation step required. Uses PyYAML/jsonschema if already available;
falls back to WARN where optional libraries are missing.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path("validation/reports")
DEFAULT_REPORT_MD = REPORT_DIR / "zen-validate.report.md"
DEFAULT_REPORT_JSON = REPORT_DIR / "zen-validate.report.json"

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

TEMPLATE_ZONES = {
    ("agents", "templates"),
    ("skills", "templates"),
    ("prompts", "templates"),
    ("projects", "templates"),
}

EXPECTED_CORE = [
    "README.md",
    "SECURITY.md",
    ".gitignore",
    ".env.example",
    "core/SOUL.md",
    "core/ORCHESTRATOR.md",
    "core/BOOT_PROTOCOL.md",
    "harness/manifest.yaml",
    "harness/runtime.yaml",
    "harness/state_machine.yaml",
    "harness/commands/zen-validate.yaml",
    "harness/pipelines/p1.yaml",
    "harness/pipelines/p2.yaml",
    "harness/pipelines/p3.yaml",
    "harness/policies/secrets.yaml",
    "harness/reasoning/reasoning_routing.yaml",
    "harness/reasoning/reasoning_output.schema.json",
    "agents/agent_registry.yaml",
    "adapters/pi/adapter.yaml",
    "adapters/claude/adapter.yaml",
]

SCHEMA_BINDINGS = [
    ("harness/manifest.yaml", "harness/schemas/manifest.schema.json"),
    ("harness/runtime.yaml", "harness/schemas/runtime.schema.json"),
    ("harness/reasoning/reasoning_routing.yaml", "harness/schemas/reasoning-routing.schema.json"),
    ("agents/agent_registry.yaml", "harness/schemas/agent-registry.schema.json"),
]

TRIGGER_TO_CLAUDE_KEY = {
    "ZEN NEW": "zen_new",
    "ZEN MEMORY INIT": "zen_memory_init",
    "ZEN NEW BUILD": "zen_new_build",
    "ZEN STATUS": "zen_status",
    "ZEN PLAN": "zen_plan",
    "ZEN SNAPSHOT": "zen_snapshot",
    "ZEN P1": "zen_p1",
    "ZEN P2": "zen_p2",
    "ZEN P3": "zen_p3",
    "ZEN RESET": "zen_reset",
    "ZEN VALIDATE": "zen_validate",
}

SECRET_PATTERNS = [
    ("openai_key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("private_key", re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA)? ?PRIVATE KEY-----")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")),
    ("generic_secret_assignment", re.compile(r"(?i)(api[_-]?key|password|token|secret)\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
]

REDACTION = "[REDACTED_SECRET]"
MAX_DETAIL_CHARS = 900
MAX_SCAN_FILE_BYTES = 256 * 1024
MAX_SYNTAX_FILE_BYTES = 512 * 1024
TEXT_SCAN_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".txt"}
EXCLUDED_DIR_NAMES = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".pytest_cache", ".mypy_cache"}
EXCLUDED_REL_PREFIXES = {
    (".pi", "cache"),
    (".claude", "cache"),
    ("harness", ".cache"),
    ("validation", "reports"),
}
SCAN_METRICS: dict[str, Any] = {
    "files_read": 0,
    "bytes_read": 0,
    "skipped_large": 0,
    "skipped_non_text": 0,
    "skipped_excluded": 0,
    "read_paths": set(),
}


def reset_scan_metrics() -> None:
    SCAN_METRICS["files_read"] = 0
    SCAN_METRICS["bytes_read"] = 0
    SCAN_METRICS["skipped_large"] = 0
    SCAN_METRICS["skipped_non_text"] = 0
    SCAN_METRICS["skipped_excluded"] = 0
    SCAN_METRICS["read_paths"] = set()


UNSAFE_COT_PATTERNS = [
    re.compile(r"reveal_chain_of_thought\s*:\s*true", re.I),
    re.compile(r"no_chain_of_thought_disclosure\s*:\s*false", re.I),
    re.compile(r"expose_internal_steps\s*:\s*true", re.I),
    re.compile(r"persist_private_scratchpad\s*:\s*true", re.I),
]


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def sanitize_detail(detail: str) -> str:
    safe = detail
    for _name, pattern in SECRET_PATTERNS:
        safe = pattern.sub(REDACTION, safe)
    safe = safe.replace(str(Path.home()), "~")
    if len(safe) > MAX_DETAIL_CHARS:
        safe = safe[:MAX_DETAIL_CHARS] + "... [truncated]"
    return safe


def is_skipped_path(path: Path, root: Path) -> bool:
    if not is_within(path, root):
        return True
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        SCAN_METRICS["skipped_excluded"] += 1
        return True
    if any(parts[: len(prefix)] == prefix for prefix in EXCLUDED_REL_PREFIXES):
        SCAN_METRICS["skipped_excluded"] += 1
        return True
    if path.suffix in {".pyc", ".pyo"}:
        return True
    if path.name.startswith(".env") and path.name != ".env.example":
        return True
    if path.is_symlink() and not is_within(path.resolve(strict=False), root):
        return True
    return False


def is_template_zone(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    return len(parts) >= 2 and (parts[0], parts[1]) in TEMPLATE_ZONES


def iter_files(root: Path, suffixes: set[str] | None = None, max_bytes: int = MAX_SCAN_FILE_BYTES):
    allowed_suffixes = suffixes or TEXT_SCAN_SUFFIXES
    for p in root.rglob("*"):
        if not p.is_file() or is_skipped_path(p, root):
            continue
        if p.suffix not in allowed_suffixes:
            SCAN_METRICS["skipped_non_text"] += 1
            continue
        try:
            size = p.stat().st_size
        except OSError:
            SCAN_METRICS["skipped_excluded"] += 1
            continue
        if size > max_bytes:
            SCAN_METRICS["skipped_large"] += 1
            continue
        yield p


def safe_read_text(path: Path, root: Path, max_bytes: int | None = MAX_SCAN_FILE_BYTES) -> str:
    if is_skipped_path(path, root):
        raise PermissionError(f"blocked protected or out-of-sandbox path: {rel(path, root) if is_within(path, root) else '[outside-root]'}")
    if max_bytes is not None and path.stat().st_size > max_bytes:
        raise ValueError(f"file exceeds validator read limit: {rel(path, root)}")
    resolved = str(path.resolve(strict=False))
    if resolved not in SCAN_METRICS["read_paths"]:
        SCAN_METRICS["read_paths"].add(resolved)
        SCAN_METRICS["files_read"] += 1
        try:
            SCAN_METRICS["bytes_read"] += path.stat().st_size
        except OSError:
            pass
    return path.read_text(encoding="utf-8", errors="ignore")


def load_yaml(path: Path, root: Path | None = None) -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML unavailable")
    text = safe_read_text(path, root) if root is not None else path.read_text(encoding="utf-8", errors="ignore")
    return yaml.safe_load(text)


def frontmatter(path: Path, root: Path | None = None) -> Any | None:
    text = safe_read_text(path, root) if root is not None else path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    if yaml is None:
        raise RuntimeError("PyYAML unavailable")
    return yaml.safe_load(text[4:end])


def add(results: list[dict[str, str]], status: str, check: str, detail: str) -> None:
    results.append({"status": status, "check": check, "detail": sanitize_detail(detail)})


def check_structure(root: Path, results: list[dict[str, str]]) -> None:
    missing = [p for p in EXPECTED_CORE if not (root / p).is_file()]
    if missing:
        add(results, FAIL, "target_structure", "missing: " + ", ".join(missing))
    else:
        add(results, PASS, "target_structure", "all core files present")
    if (root / ".env").exists():
        add(results, FAIL, "env_safety", ".env exists; validator does not read it")
    elif (root / ".env.example").is_file():
        add(results, PASS, "env_safety", "only .env.example present")
    else:
        add(results, FAIL, "env_safety", ".env.example missing")


def check_syntax(root: Path, results: list[dict[str, str]]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    json_errors: list[str] = []
    yaml_errors: list[str] = []
    for p in iter_files(root, {".json"}, MAX_SYNTAX_FILE_BYTES):
        try:
            parsed[rel(p, root)] = json.loads(safe_read_text(p, root, MAX_SYNTAX_FILE_BYTES))
        except Exception as exc:
            json_errors.append(f"{rel(p, root)}: {exc}")
    for p in iter_files(root, {".yaml", ".yml"}, MAX_SYNTAX_FILE_BYTES):
        try:
            parsed[rel(p, root)] = load_yaml(p, root)
        except Exception as exc:
            yaml_errors.append(f"{rel(p, root)}: {exc}")
    add(results, FAIL if json_errors else PASS, "json_syntax", "; ".join(json_errors) if json_errors else "ok")
    add(results, FAIL if yaml_errors else PASS, "yaml_syntax", "; ".join(yaml_errors) if yaml_errors else "ok")
    return parsed


def check_schema_gate(root: Path, results: list[dict[str, str]]) -> None:
    if yaml is None or jsonschema is None:
        add(results, WARN, "schema_gate", "PyYAML or jsonschema unavailable; syntax-only validation used")
        return
    bindings = list(SCHEMA_BINDINGS)
    bindings += [(rel(p, root), "harness/schemas/command.schema.json") for p in sorted((root / "harness/commands").glob("*.yaml"))]
    bindings += [(rel(p, root), "harness/schemas/pipeline.schema.json") for p in sorted((root / "harness/pipelines").glob("*.yaml"))]
    bindings += [(rel(p, root), "harness/schemas/policy.schema.json") for p in sorted((root / "harness/policies").glob("*.yaml"))]
    bindings += [(rel(p, root), "harness/schemas/adapter.schema.json") for p in sorted((root / "adapters").glob("*/adapter.yaml"))]
    for p in sorted((root / "agents").glob("**/*.md")):
        if frontmatter(p, root) is not None:
            bindings.append((rel(p, root), "harness/schemas/agent.schema.json"))
    for p in sorted((root / "skills").glob("**/*.md")):
        if frontmatter(p, root) is not None:
            bindings.append((rel(p, root), "harness/schemas/skill.schema.json"))
    for p in sorted((root / "kontext/memory").glob("**/*.md")):
        if frontmatter(p, root) is not None:
            bindings.append((rel(p, root), "harness/schemas/memory.schema.json"))

    errors: list[str] = []
    for data_rel, schema_rel in bindings:
        data_path = root / data_rel
        schema_path = root / schema_rel
        if not schema_path.is_file():
            errors.append(f"missing schema {schema_rel}")
            continue
        try:
            if is_skipped_path(schema_path, root) or is_skipped_path(data_path, root):
                errors.append(f"blocked protected or out-of-sandbox binding {data_rel}")
                continue
            schema = json.loads(safe_read_text(schema_path, root))
            data = frontmatter(data_path, root) if data_path.suffix == ".md" else load_yaml(data_path, root)
            jsonschema.Draft202012Validator(schema).validate(data)
        except Exception as exc:
            msg = getattr(exc, "message", str(exc))
            errors.append(f"{data_rel} vs {schema_rel}: {msg}")
    add(results, FAIL if errors else PASS, "schema_gate", "; ".join(errors) if errors else f"{len(bindings)} bindings valid")


def check_placeholders_and_aliases(root: Path, results: list[dict[str, str]]) -> None:
    placeholder_hits: list[str] = []
    legacy_hits: list[str] = []
    legacy_token = "L" + "3"
    for p in iter_files(root):
        text = safe_read_text(p, root)
        for n, line in enumerate(text.splitlines(), 1):
            if not is_template_zone(p, root) and re.search(r"\{\{[^}]+\}\}", line):
                placeholder_hits.append(f"{rel(p, root)}:{n}")
            if legacy_token in line or "L" + "3_PIPELINE" in line:
                legacy_hits.append(f"{rel(p, root)}:{n}")
    add(results, FAIL if placeholder_hits else PASS, "placeholder_gate", ", ".join(placeholder_hits) if placeholder_hits else "ok")
    add(results, FAIL if legacy_hits else PASS, "legacy_alias_gate", ", ".join(legacy_hits) if legacy_hits else "ok")


def check_cot_and_secret_safety(root: Path, results: list[dict[str, str]]) -> None:
    cot_hits: list[str] = []
    secret_hits: list[str] = []
    for p in iter_files(root):
        text = safe_read_text(p, root)
        for n, line in enumerate(text.splitlines(), 1):
            for pat in UNSAFE_COT_PATTERNS:
                if pat.search(line):
                    cot_hits.append(f"{rel(p, root)}:{n}")
            for name, pat in SECRET_PATTERNS:
                if pat.search(line):
                    secret_hits.append(f"{rel(p, root)}:{n}:{name}")
    add(results, FAIL if cot_hits else PASS, "no_cot_disclosure", ", ".join(cot_hits) if cot_hits else "ok")
    add(results, FAIL if secret_hits else PASS, "secret_scan", ", ".join(secret_hits) if secret_hits else "ok; .env files skipped")


def check_references(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    refs: set[str] = set(EXPECTED_CORE)
    manifest = parsed.get("harness/manifest.yaml") or {}
    for value in (manifest.get("core") or {}).values():
        refs.add(str(value))
    for item in manifest.get("pipelines") or []:
        if isinstance(item, dict):
            refs.add(str(item.get("path")))
    security = manifest.get("security") or {}
    if security.get("policy_root"):
        for name in ["filesystem.yaml", "protected_paths.yaml", "secrets.yaml", "network.yaml", "shell.yaml", "tools.yaml", "prompt-injection.yaml", "onboarding.yaml"]:
            refs.add(str(Path(security["policy_root"]) / name))
    runtime = parsed.get("harness/runtime.yaml") or {}
    for section in ["context", "reasoning", "validation"]:
        obj = runtime.get(section) or {}
        for key, val in obj.items():
            if "report" in str(key):
                continue
            if isinstance(val, str) and ("/" in val or val.endswith((".yaml", ".json", ".md"))):
                refs.add(val)
            if isinstance(val, list):
                refs.update(str(x) for x in val if isinstance(x, str) and "/" in x)
    missing = sorted(r for r in refs if r and "*" not in r and "{" not in r and not (root / r).exists())
    add(results, FAIL if missing else PASS, "referenced_core_paths", ", ".join(missing) if missing else "ok")


def check_adapters(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    sm = parsed.get("harness/state_machine.yaml") or {}
    triggers = [t.get("trigger") for t in sm.get("transitions", []) if str(t.get("trigger", "")).startswith("ZEN ")]
    pi = parsed.get("adapters/pi/adapter.yaml") or {}
    pi_triggers = (pi.get("commands") or {}).get("native_triggers") or []
    missing_pi = sorted(set(triggers) - set(pi_triggers))
    if missing_pi:
        issues.append("pi_missing=" + ",".join(missing_pi))
    claude = parsed.get("adapters/claude/adapter.yaml") or {}
    claude_keys = set((claude.get("natural_language_triggers") or {}).keys())
    missing_claude = [key for trig, key in TRIGGER_TO_CLAUDE_KEY.items() if trig in triggers and key not in claude_keys]
    if missing_claude:
        issues.append("claude_missing=" + ",".join(missing_claude))
    for route in ((pi.get("commands") or {}).get("pipeline_routes") or {}).values():
        if not (root / str(route)).exists():
            issues.append("pi_route_missing=" + str(route))
    for route in (claude.get("pipeline_routes") or {}).values():
        if not (root / str(route)).exists():
            issues.append("claude_route_missing=" + str(route))
    add(results, FAIL if issues else PASS, "adapter_consistency", "; ".join(issues) if issues else "ok")


def check_trigger_authority_sync(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    sm = parsed.get("harness/state_machine.yaml") or {}
    if sm.get("authority") != "trigger_source_of_truth":
        issues.append("state_machine_authority_missing")
    triggers = sorted({str(t.get("trigger")) for t in sm.get("transitions", []) if str(t.get("trigger", "")).startswith("ZEN ")})
    trigger_set = set(triggers)

    orchestrator_text = safe_read_text(root / "core/ORCHESTRATOR.md", root)
    missing_orchestrator = [trig for trig in triggers if f"`{trig}`" not in orchestrator_text and trig not in orchestrator_text]
    if missing_orchestrator:
        issues.append("orchestrator_missing=" + ",".join(missing_orchestrator))

    registry = parsed.get("agents/agent_registry.yaml") or {}
    orchestrator = next(
        (agent for agent in registry.get("agents", []) if isinstance(agent, dict) and agent.get("id") == "orchestrator"),
        None,
    )
    registry_triggers = {str(t) for t in ((orchestrator or {}).get("triggers") or []) if str(t).startswith("ZEN ")}
    missing_registry = sorted(trigger_set - registry_triggers)
    extra_registry = sorted(registry_triggers - trigger_set)
    if missing_registry:
        issues.append("registry_orchestrator_missing=" + ",".join(missing_registry))
    if extra_registry:
        issues.append("registry_orchestrator_extra=" + ",".join(extra_registry))

    pi = parsed.get("adapters/pi/adapter.yaml") or {}
    pi_triggers = {str(t) for t in ((pi.get("commands") or {}).get("native_triggers") or []) if str(t).startswith("ZEN ")}
    missing_pi = sorted(trigger_set - pi_triggers)
    extra_pi = sorted(pi_triggers - trigger_set)
    if missing_pi:
        issues.append("pi_missing=" + ",".join(missing_pi))
    if extra_pi:
        issues.append("pi_extra=" + ",".join(extra_pi))
    if (pi.get("validation_flow") or {}).get("trigger") == "ZEN VALIDATE" and (pi.get("validation_flow") or {}).get("runtime_implemented") is not True:
        issues.append("pi_validation_runtime_not_implemented")

    claude = parsed.get("adapters/claude/adapter.yaml") or {}
    expected_claude_keys = {TRIGGER_TO_CLAUDE_KEY[trig] for trig in triggers if trig in TRIGGER_TO_CLAUDE_KEY}
    claude_keys = set((claude.get("natural_language_triggers") or {}).keys())
    missing_claude = sorted(expected_claude_keys - claude_keys)
    extra_claude = sorted(key for key in (claude_keys - expected_claude_keys) if key.startswith("zen_"))
    if missing_claude:
        issues.append("claude_missing=" + ",".join(missing_claude))
    if extra_claude:
        issues.append("claude_extra=" + ",".join(extra_claude))
    if (claude.get("validation_flow") or {}).get("trigger") == "ZEN VALIDATE" and (claude.get("validation_flow") or {}).get("runtime_implemented") is not True:
        issues.append("claude_validation_runtime_not_implemented")

    add(results, FAIL if issues else PASS, "trigger_authority_sync", "; ".join(issues) if issues else "ok")


def check_validator_policy_boundary(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    fs = parsed.get("harness/policies/filesystem.yaml") or {}
    protected = parsed.get("harness/policies/protected_paths.yaml") or {}
    secrets = parsed.get("harness/policies/secrets.yaml") or {}

    read_allowed = set(fs.get("read_allowed") or [])
    for required in ["tools/**/*.py", "harness/**/*.json"]:
        if required not in read_allowed:
            issues.append(f"filesystem_read_missing={required}")

    exception = fs.get("validator_report_write_exception") or {}
    if exception.get("actor") != "tools/zen_validate.py":
        issues.append("filesystem_validator_exception_actor_missing")
    exception_paths = set(exception.get("paths") or [])
    for required in ["validation/reports/zen-validate.report.md", "validation/reports/zen-validate.report.json"]:
        if required not in exception_paths:
            issues.append(f"filesystem_validator_report_path_missing={required}")
    exception_constraints = set(exception.get("constraints") or [])
    for required in ["no_secret_values_in_reports", "no_env_file_reads", "report_path_must_remain_under_validation_reports", "check_only_writes_nothing"]:
        if required not in exception_constraints:
            issues.append(f"filesystem_validator_constraint_missing={required}")

    no_write = set(protected.get("no_write") or [])
    if "validation/**" in no_write or "validation/" in no_write:
        issues.append("protected_paths_overbroad_validation_no_write")
    for required in ["validation/*.yaml", "validation/**/*.yaml"]:
        if required not in no_write:
            issues.append(f"protected_validation_yaml_missing={required}")
    controlled = (protected.get("controlled_write_exceptions") or {}).get("validator_reports") or {}
    if controlled.get("actor") != "tools/zen_validate.py":
        issues.append("protected_validator_exception_actor_missing")
    controlled_paths = set(controlled.get("paths") or [])
    if "validation/reports/zen-validate.report.md" not in controlled_paths:
        issues.append("protected_validator_report_md_missing")
    controlled_constraints = set(controlled.get("constraints") or [])
    for required in ["redacted_reports_only", "no_secret_values", "no_source_mutation", "check_only_writes_nothing"]:
        if required not in controlled_constraints:
            issues.append(f"protected_validator_constraint_missing={required}")

    policy_exceptions = secrets.get("policy_file_exceptions") or {}
    readable_policy_files = set(policy_exceptions.get("readable_policy_files") or [])
    allowed_policy_files = set((secrets.get("secret_files") or {}).get("allowed_policy_files") or [])
    if "harness/policies/secrets.yaml" not in readable_policy_files:
        issues.append("secrets_policy_read_exception_missing")
    if "harness/policies/secrets.yaml" not in allowed_policy_files:
        issues.append("secrets_allowed_policy_file_missing")
    blocked_read = set((secrets.get("secret_files") or {}).get("blocked_read") or [])
    for required in [".env", ".env.*", "**/.env", "**/.env.*"]:
        if required not in blocked_read:
            issues.append(f"secret_block_missing={required}")

    add(results, FAIL if issues else PASS, "validator_policy_boundary", "; ".join(issues) if issues else "ok")


def check_run_state_model(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    required_states = {
        "INIT_REQUIRED",
        "CONFIG_INCOMPLETE",
        "READY_READONLY",
        "READY_MUTATING",
        "VALIDATING",
        "RUNNING",
        "BLOCKED",
        "DONE",
        "FAILED",
    }
    sm = parsed.get("harness/state_machine.yaml") or {}
    runtime = parsed.get("harness/runtime.yaml") or {}
    sm_model = sm.get("run_state_model") or {}
    rt_model = runtime.get("run_state_model") or {}

    sm_states_raw = sm_model.get("states") or {}
    sm_states = set(sm_states_raw.keys()) if isinstance(sm_states_raw, dict) else set(sm_states_raw or [])
    rt_states = set(rt_model.get("states") or [])
    if sm_model.get("authority") != "runtime_lifecycle_source":
        issues.append("state_machine_run_state_authority_missing")
    missing_sm = sorted(required_states - sm_states)
    missing_rt = sorted(required_states - rt_states)
    if missing_sm:
        issues.append("state_machine_run_states_missing=" + ",".join(missing_sm))
    if missing_rt:
        issues.append("runtime_run_states_missing=" + ",".join(missing_rt))
    if sm_states and rt_states and sm_states != rt_states:
        issues.append("run_state_model_state_drift")
    if sm_model.get("initial") != "INIT_REQUIRED" or rt_model.get("initial") != "INIT_REQUIRED":
        issues.append("run_state_initial_not_init_required")
    if rt_model.get("mutation_requires_state") != "READY_MUTATING":
        issues.append("runtime_mutation_state_not_ready_mutating")
    if rt_model.get("validation_state") != "VALIDATING":
        issues.append("runtime_validation_state_not_validating")
    if rt_model.get("running_state") != "RUNNING":
        issues.append("runtime_running_state_not_running")
    for state in ["DONE", "BLOCKED", "FAILED"]:
        if state not in set(sm_model.get("terminal_states") or []) or state not in set(rt_model.get("terminal_states") or []):
            issues.append(f"terminal_state_missing={state}")
    readonly = set(sm_model.get("readonly_states") or []) | set(rt_model.get("readonly_states") or [])
    for state in ["INIT_REQUIRED", "CONFIG_INCOMPLETE", "READY_READONLY", "VALIDATING", "BLOCKED", "FAILED"]:
        if state not in readonly:
            issues.append(f"readonly_state_missing={state}")
    sm_gates = sm_model.get("gates") or {}
    rt_gates = rt_model.get("gates") or {}
    for key in ["onboarding_to_ready_readonly", "ready_readonly_to_ready_mutating", "validating_to_blocked", "running_to_done"]:
        if key not in sm_gates:
            issues.append(f"state_machine_gate_missing={key}")
    for key in ["readonly_required", "mutating_required", "p3_required"]:
        if key not in rt_gates:
            issues.append(f"runtime_gate_missing={key}")
    docs = ["docs/architecture.md", "docs/onboarding.md", "core/BOOT_PROTOCOL.md"]
    for doc in docs:
        text = safe_read_text(root / doc, root)
        for state in required_states:
            if state not in text:
                issues.append(f"doc_state_missing={doc}:{state}")
                break
    add(results, FAIL if issues else PASS, "run_state_model", "; ".join(issues) if issues else "ok")


def check_command_specs(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    command_files = sorted((root / "harness/commands").glob("*.yaml"))
    required_keys = ["inputs", "outputs", "reads", "writes", "preconditions", "gates", "run_state_transition", "failure_modes", "mutation"]
    for path in command_files:
        rel_path = rel(path, root)
        data = parsed.get(rel_path) or (load_yaml(path, root) if yaml is not None else {})
        if data.get("status") == "scaffold":
            issues.append(f"{rel_path}:status_scaffold")
        for key in required_keys:
            if key not in data:
                issues.append(f"{rel_path}:missing_{key}")
        transition = data.get("run_state_transition") or {}
        for key in ["start_from", "on_start", "on_success", "on_blocked", "on_failure"]:
            if key not in transition:
                issues.append(f"{rel_path}:run_state_missing_{key}")
        mutation = data.get("mutation") or {}
        writes = data.get("writes") or []
        report_only = rel_path == "harness/commands/zen-validate.yaml"
        has_writes = bool(writes)
        if has_writes and not report_only:
            if "READY_READONLY" in set(transition.get("start_from") or []):
                if mutation.get("readonly_intake_allowed_from") != "READY_READONLY":
                    issues.append(f"{rel_path}:ready_readonly_without_intake_mode")
                if not mutation.get("readonly_intake_outputs"):
                    issues.append(f"{rel_path}:ready_readonly_without_dry_run_outputs")
            if mutation.get("persist_requires_state") != "READY_MUTATING":
                issues.append(f"{rel_path}:persist_without_ready_mutating")
            if mutation.get("required_state") != "READY_MUTATING":
                issues.append(f"{rel_path}:mutating_without_ready_mutating")
            if mutation.get("requires_confirmation") is not True:
                issues.append(f"{rel_path}:mutating_without_confirmation")
            gates = set((data.get("gates") or {}).get("before_write") or [])
            for gate in ["filesystem_gate", "secret_gate"]:
                if gate not in gates:
                    issues.append(f"{rel_path}:write_gate_missing_{gate}")
        if not has_writes and mutation.get("allowed") not in {False, None}:
            issues.append(f"{rel_path}:read_only_mutation_not_false")
    add(results, FAIL if issues else PASS, "command_specs", "; ".join(issues) if issues else "ok")


def check_pipeline_run_state_alignment(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    for pipe in ["p1", "p2", "p3"]:
        path = f"harness/pipelines/{pipe}.yaml"
        data = parsed.get(path) or {}
        if "state_transition" in data:
            issues.append(f"{path}:legacy_state_transition_key")
        if "routing_state_transition" not in data:
            issues.append(f"{path}:missing_routing_state_transition")
        transition = data.get("run_state_transition") or {}
        for key in ["start_from", "on_start", "on_success", "on_blocked", "on_failure"]:
            if key not in transition:
                issues.append(f"{path}:run_state_missing_{key}")
        semantics = data.get("run_state_semantics") or {}
        if "mutation_requires_state" not in semantics:
            issues.append(f"{path}:missing_mutation_requires_state")
        if pipe == "p3":
            if "READY_MUTATING" not in set(transition.get("start_from") or []):
                issues.append("p3:start_not_ready_mutating")
            if semantics.get("mutation_allowed") != "after_force_gate_approved_only":
                issues.append("p3:wrong_mutation_semantics")
            persist_requires = set(semantics.get("persist_requires") or [])
            if "force_gate" not in persist_requires:
                issues.append("p3:force_gate_not_required_for_persist")
    add(results, FAIL if issues else PASS, "pipeline_run_state_alignment", "; ".join(issues) if issues else "ok")


def check_p3_artifact_lifecycle(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    p3 = parsed.get("harness/pipelines/p3.yaml") or {}
    runtime = parsed.get("harness/runtime.yaml") or {}
    fs = parsed.get("harness/policies/filesystem.yaml") or {}
    artifacts = p3.get("artifacts") or {}
    required_lifecycle = ["transient", "draft", "approved", "persisted", "archived", "rejected"]
    lifecycle = artifacts.get("lifecycle") or []
    for state in required_lifecycle:
        if state not in lifecycle:
            issues.append(f"p3_lifecycle_missing={state}")
    zones = artifacts.get("zones") or {}
    for zone in ["draft", "approved", "report", "snapshot", "archived", "rejected"]:
        if zone not in zones:
            issues.append(f"p3_zone_missing={zone}")
    rules = artifacts.get("lifecycle_rules") or {}
    for rule in ["transient_to_draft", "draft_to_approved", "approved_to_persisted", "draft_to_rejected"]:
        if rule not in rules:
            issues.append(f"p3_lifecycle_rule_missing={rule}")
    if "force_gate" not in str(rules.get("draft_to_approved", "")):
        issues.append("p3_approval_without_force_gate")
    artifact_policy = p3.get("artifact_policy") or {}
    allowed_after_approved = set(artifact_policy.get("allowed_after_approved") or [])
    if "projects/*/p3/*" in allowed_after_approved:
        issues.append("p3_allowed_after_approved_too_broad")
    for required in ["projects/*/p3/*/approved/**", "projects/*/p3/*/reports/**"]:
        if required not in allowed_after_approved:
            issues.append(f"p3_allowed_after_approved_missing={required}")
    forbidden_after_approved = set(artifact_policy.get("forbidden_after_approved") or [])
    for forbidden in ["projects/*/p3/*/draft/**", "projects/*/p3/*/rejected/**"]:
        if forbidden not in forbidden_after_approved:
            issues.append(f"p3_forbidden_after_approved_missing={forbidden}")
    persist_requires = set(artifact_policy.get("persist_requires") or [])
    for required in ["READY_MUTATING", "force_gate_APPROVED", "filesystem_gate", "secret_gate", "prompt_injection_gate", "confirmation"]:
        if required not in persist_requires:
            issues.append(f"p3_artifact_policy_persist_requires_missing={required}")
    trust = artifacts.get("trust") or {}
    for state in ["transient", "draft", "approved", "persisted"]:
        if state not in trust:
            issues.append(f"p3_trust_missing={state}")
    rt_lifecycle = runtime.get("artifact_lifecycle") or {}
    if set(rt_lifecycle.get("states") or []) != set(required_lifecycle):
        issues.append("runtime_artifact_lifecycle_state_drift")
    if "READY_MUTATING" not in str((rt_lifecycle.get("persistence_rules") or {}).get("draft_write_requires", "")):
        issues.append("runtime_draft_write_not_ready_mutating")
    fs_policy = fs.get("p3_artifact_write_policy") or {}
    if set(fs_policy.get("lifecycle") or []) != set(required_lifecycle):
        issues.append("filesystem_p3_lifecycle_state_drift")
    if "ready_readonly_intake_only_no_persist" not in set(fs_policy.get("constraints") or []):
        issues.append("filesystem_ready_readonly_intake_constraint_missing")
    add(results, FAIL if issues else PASS, "p3_artifact_lifecycle", "; ".join(issues) if issues else "ok")


def check_audit_model(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    p3 = parsed.get("harness/pipelines/p3.yaml") or {}
    runtime = parsed.get("harness/runtime.yaml") or {}
    tools_policy = parsed.get("harness/policies/tools.yaml") or {}
    schema_path = root / "harness/schemas/audit.schema.json"
    audit_schema: dict[str, Any] = {}
    if not schema_path.is_file():
        issues.append("audit_schema_missing")
    else:
        try:
            audit_schema = json.loads(safe_read_text(schema_path, root))
        except Exception as exc:
            issues.append(f"audit_schema_parse_error={exc}")
    audit = p3.get("audit") or {}
    runtime_audit = runtime.get("audit_model") or {}
    policy_audit = tools_policy.get("audit_log_model") or {}
    required_events = {"pipeline_run", "tool_call", "gate_decision", "hitl_confirmation", "policy_block"}
    for source_name, source in [("p3", audit), ("runtime", runtime_audit), ("tools_policy", policy_audit)]:
        events = set(source.get("required_events") or source.get("event_types") or source.get("applies_to") or [])
        if not required_events.issubset(events):
            issues.append(f"{source_name}_audit_events_missing")
        fields = set(source.get("required_fields") or [])
        for field in ["timestamp", "run_id", "actor", "event_type", "target_paths", "risk_level", "trust_zone", "decision", "result", "redacted"]:
            if field not in fields:
                issues.append(f"{source_name}_audit_field_missing={field}")
    if audit_schema:
        required_schema_fields = set(audit_schema.get("required") or [])
        if "redacted" not in required_schema_fields:
            issues.append("audit_schema_redacted_not_required")
        redacted_prop = (audit_schema.get("properties") or {}).get("redacted") or {}
        if redacted_prop.get("const") is not True:
            issues.append("audit_schema_redacted_not_const_true")
    if runtime_audit.get("redaction_required") is not True or runtime_audit.get("no_secret_values") is not True:
        issues.append("runtime_audit_redaction_missing")
    if policy_audit.get("append_only") is not True:
        issues.append("policy_audit_not_append_only")
    add(results, FAIL if issues else PASS, "audit_model", "; ".join(issues) if issues else "ok")


def check_executor_runtime(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    executor_path = root / "tools/zen_execute.py"
    if not executor_path.is_file():
        issues.append("executor_tool_missing")
    else:
        text = safe_read_text(executor_path, root)
        if "open(" in text or ".mkdir(" in text:
            issues.append("executor_contains_unsafe_file_primitive")
        if "write_text" in text and ("safe_report_path" not in text or ".preview.json" not in text):
            issues.append("executor_write_text_without_preview_boundary")
        for required in ["dry-run", "writes_performed", "redacted", "audit-preview.schema.json"]:
            if required not in text:
                issues.append(f"executor_text_missing={required}")
    runtime = parsed.get("harness/runtime.yaml") or {}
    tools_policy = parsed.get("harness/policies/tools.yaml") or {}
    fs = parsed.get("harness/policies/filesystem.yaml") or {}
    executor = runtime.get("executor_runtime") or {}
    if executor.get("tool") != "tools/zen_execute.py":
        issues.append("runtime_executor_tool_missing")
    if executor.get("default_mode") != "dry_run":
        issues.append("runtime_executor_not_dry_run_default")
    if executor.get("writes_project_artifacts") is not False or executor.get("writes_audit_log") is not False:
        issues.append("runtime_executor_allows_project_or_audit_writes")
    policy = tools_policy.get("executor_policy") or {}
    if policy.get("default_decision") != "dry_run_only":
        issues.append("tools_policy_executor_not_dry_run_only")
    fs_policy = fs.get("executor_dry_run_policy") or {}
    if fs_policy.get("writes_allowed") != [] or fs_policy.get("p3_run_directories") != "no_create_in_dry_run":
        issues.append("filesystem_executor_dry_run_boundary_invalid")
    for schema_rel in ["harness/schemas/run-manifest.schema.json", "harness/schemas/hitl-confirmation.schema.json", "harness/schemas/hitl-preview.schema.json"]:
        if not (root / schema_rel).is_file():
            issues.append(f"schema_missing={schema_rel}")
    docs = ["docs/executor.md", "docs/architecture.md", "docs/commands.md", "docs/pipelines.md"]
    for doc in docs:
        if not (root / doc).is_file():
            issues.append(f"doc_missing={doc}")
            continue
        doc_text = safe_read_text(root / doc, root)
        if "zen_execute.py" not in doc_text and doc != "docs/pipelines.md":
            issues.append(f"doc_executor_missing={doc}")
    add(results, FAIL if issues else PASS, "executor_runtime", "; ".join(issues) if issues else "ok")


def check_executor_report_boundary(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    runtime = parsed.get("harness/runtime.yaml") or {}
    fs = parsed.get("harness/policies/filesystem.yaml") or {}
    protected = parsed.get("harness/policies/protected_paths.yaml") or {}
    tools_policy = parsed.get("harness/policies/tools.yaml") or {}
    executor = runtime.get("executor_runtime") or {}
    controlled = executor.get("controlled_report_mode") or {}
    if controlled.get("default_path") != "validation/reports/zen-execute.preview.json":
        issues.append("runtime_executor_preview_default_path_missing")
    if controlled.get("suffix") != ".preview.json":
        issues.append("runtime_executor_preview_suffix_missing")
    fs_exception = fs.get("executor_preview_report_exception") or {}
    if fs_exception.get("actor") != "tools/zen_execute.py":
        issues.append("filesystem_executor_preview_actor_missing")
    if "validation/reports/*.preview.json" not in set(fs_exception.get("paths") or []):
        issues.append("filesystem_executor_preview_glob_missing")
    for required in ["suffix_must_be_preview_json_or_hitl_preview_json", "audit_preview_schema_required", "hitl_preview_schema_required", "no_project_artifact_writes", "no_project_audit_append"]:
        if required not in set(fs_exception.get("constraints") or []):
            issues.append(f"filesystem_executor_preview_constraint_missing={required}")
    protected_exception = (protected.get("controlled_write_exceptions") or {}).get("executor_preview_reports") or {}
    if protected_exception.get("actor") != "tools/zen_execute.py":
        issues.append("protected_executor_preview_actor_missing")
    if "validation/reports/*.preview.json" not in set(protected_exception.get("paths") or []):
        issues.append("protected_executor_preview_glob_missing")
    policy = tools_policy.get("executor_policy") or {}
    if policy.get("preview_schema") != "harness/schemas/audit-preview.schema.json":
        issues.append("tools_policy_executor_preview_schema_missing")
    if "preview_report_write" not in set(policy.get("allowed_without_confirmation") or []):
        issues.append("tools_policy_preview_report_not_allowed")
    add(results, FAIL if issues else PASS, "executor_report_boundary", "; ".join(issues) if issues else "ok")


def check_audit_preview_schema(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    schema_path = root / "harness/schemas/audit-preview.schema.json"
    if not schema_path.is_file():
        issues.append("audit_preview_schema_missing")
    else:
        try:
            schema = json.loads(safe_read_text(schema_path, root))
        except Exception as exc:
            schema = {}
            issues.append(f"audit_preview_schema_parse_error={exc}")
        required = set(schema.get("required") or [])
        for field in ["timestamp", "run_id", "actor", "event_type", "target_paths", "risk_level", "trust_zone", "decision", "result", "redacted", "mode", "writes_performed"]:
            if field not in required:
                issues.append(f"audit_preview_required_missing={field}")
        props = schema.get("properties") or {}
        if (props.get("actor") or {}).get("const") != "tools/zen_execute.py":
            issues.append("audit_preview_actor_const_missing")
        if (props.get("mode") or {}).get("const") != "dry-run":
            issues.append("audit_preview_mode_const_missing")
        if (props.get("writes_performed") or {}).get("maxItems") != 0:
            issues.append("audit_preview_writes_performed_not_empty")
        if (props.get("redacted") or {}).get("const") is not True:
            issues.append("audit_preview_redacted_not_const_true")
    add(results, FAIL if issues else PASS, "audit_preview_schema", "; ".join(issues) if issues else "ok")


def check_hitl_preview_model(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    schema_path = root / "harness/schemas/hitl-preview.schema.json"
    if not schema_path.is_file():
        issues.append("hitl_preview_schema_missing")
        schema = {}
    else:
        try:
            schema = json.loads(safe_read_text(schema_path, root))
        except Exception as exc:
            schema = {}
            issues.append(f"hitl_preview_schema_parse_error={exc}")
    required = set(schema.get("required") or [])
    for field in ["confirmation_id", "run_id", "actor", "scope", "risk_level", "target_paths", "expires_at", "decision", "effective_confirmation", "redacted", "preview_only"]:
        if field not in required:
            issues.append(f"hitl_preview_required_missing={field}")
    props = schema.get("properties") or {}
    if (props.get("decision") or {}).get("const") != "preview_only":
        issues.append("hitl_preview_decision_not_preview_only")
    if (props.get("effective_confirmation") or {}).get("const") is not False:
        issues.append("hitl_preview_effective_confirmation_not_false")
    if (props.get("preview_only") or {}).get("const") is not True:
        issues.append("hitl_preview_preview_only_not_true")
    if (props.get("schema") or {}).get("const") != "harness/schemas/hitl-preview.schema.json":
        issues.append("hitl_preview_schema_property_missing")
    runtime = parsed.get("harness/runtime.yaml") or {}
    tools_policy = parsed.get("harness/policies/tools.yaml") or {}
    hitl_runtime = (runtime.get("executor_runtime") or {}).get("hitl_preview") or {}
    if hitl_runtime.get("decision") != "preview_only" or hitl_runtime.get("effective_confirmation") is not False:
        issues.append("runtime_hitl_preview_semantics_invalid")
    policy = tools_policy.get("executor_policy") or {}
    if policy.get("hitl_preview_schema") != "harness/schemas/hitl-preview.schema.json":
        issues.append("tools_policy_hitl_preview_schema_missing")
    if policy.get("effective_confirmation") is not False or policy.get("hitl_preview_decision") != "preview_only":
        issues.append("tools_policy_hitl_preview_semantics_invalid")
    add(results, FAIL if issues else PASS, "hitl_preview_model", "; ".join(issues) if issues else "ok")


def check_audit_append_simulation(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    runtime = parsed.get("harness/runtime.yaml") or {}
    tools_policy = parsed.get("harness/policies/tools.yaml") or {}
    fs = parsed.get("harness/policies/filesystem.yaml") or {}
    simulation = (runtime.get("executor_runtime") or {}).get("audit_append_simulation") or {}
    if simulation.get("effective_append") is not False or simulation.get("project_audit_log_write") is not False:
        issues.append("runtime_audit_append_simulation_not_false")
    policy = tools_policy.get("executor_policy") or {}
    if policy.get("audit_append_simulation_effective_append") is not False:
        issues.append("tools_policy_audit_append_simulation_not_false")
    if "audit_append_simulation" not in set(policy.get("allowed_without_confirmation") or []):
        issues.append("tools_policy_audit_append_simulation_not_allowed")
    fs_exception = fs.get("executor_preview_report_exception") or {}
    if "no_project_audit_append" not in set(fs_exception.get("constraints") or []):
        issues.append("filesystem_no_project_audit_append_missing")
    executor_text = safe_read_text(root / "tools/zen_execute.py", root)
    for required in ["simulate-audit-append", "effective_append", "would_append_to"]:
        if required not in executor_text:
            issues.append(f"executor_audit_simulation_text_missing={required}")
    add(results, FAIL if issues else PASS, "audit_append_simulation", "; ".join(issues) if issues else "ok")


def check_controlled_write_boundary(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    runtime = parsed.get("harness/runtime.yaml") or {}
    fs = parsed.get("harness/policies/filesystem.yaml") or {}
    protected = parsed.get("harness/policies/protected_paths.yaml") or {}
    tools_policy = parsed.get("harness/policies/tools.yaml") or {}
    boundary = ((runtime.get("executor_runtime") or {}).get("controlled_write_boundary") or {})
    for key in ["confirmation_report", "audit_preview_append", "run_manifest_preview"]:
        if key not in boundary:
            issues.append(f"runtime_boundary_missing={key}")
    fs_paths = set((fs.get("executor_preview_report_exception") or {}).get("paths") or [])
    protected_paths = set(((protected.get("controlled_write_exceptions") or {}).get("executor_preview_reports") or {}).get("paths") or [])
    for required in ["validation/reports/*.confirmation.json", "validation/reports/*.audit-preview.jsonl", "validation/reports/*.run-manifest.preview.json"]:
        if required not in fs_paths:
            issues.append(f"filesystem_boundary_path_missing={required}")
        if required not in protected_paths:
            issues.append(f"protected_boundary_path_missing={required}")
    policy = tools_policy.get("executor_policy") or {}
    for allowed in ["confirmation_report_boundary_test", "audit_preview_append_validation_report", "run_manifest_preview_report"]:
        if allowed not in set(policy.get("allowed_without_confirmation") or []):
            issues.append(f"tools_policy_boundary_allowed_missing={allowed}")
    for schema_rel in ["harness/schemas/confirmation-report.schema.json", "harness/schemas/audit-preview-event.schema.json", "harness/schemas/run-manifest-preview.schema.json"]:
        if not (root / schema_rel).is_file():
            issues.append(f"boundary_schema_missing={schema_rel}")
    executor_text = safe_read_text(root / "tools/zen_execute.py", root)
    for flag in ["write-confirmation-report", "append-audit-preview", "write-run-manifest-preview"]:
        if flag not in executor_text:
            issues.append(f"executor_flag_missing={flag}")
    add(results, FAIL if issues else PASS, "controlled_write_boundary", "; ".join(issues) if issues else "ok")


def check_confirmation_report_model(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    schema_path = root / "harness/schemas/confirmation-report.schema.json"
    if not schema_path.is_file():
        issues.append("confirmation_report_schema_missing")
        schema = {}
    else:
        schema = json.loads(safe_read_text(schema_path, root))
    required = set(schema.get("required") or [])
    for field in ["confirmation_id", "decision", "effective_confirmation", "not_project_authorization", "production_scope", "redacted", "schema"]:
        if field not in required:
            issues.append(f"confirmation_required_missing={field}")
    props = schema.get("properties") or {}
    if "Boundary-test artifact only" not in schema.get("description", ""):
        issues.append("confirmation_schema_boundary_description_missing")
    if (props.get("effective_confirmation") or {}).get("const") is not True:
        issues.append("confirmation_effective_not_true")
    if "never authorizes project mutation" not in (props.get("effective_confirmation") or {}).get("description", ""):
        issues.append("confirmation_effective_description_missing")
    if (props.get("not_project_authorization") or {}).get("const") is not True:
        issues.append("confirmation_not_project_authorization_missing")
    if (props.get("production_scope") or {}).get("const") is not False:
        issues.append("confirmation_production_scope_not_false")
    add(results, FAIL if issues else PASS, "confirmation_report_model", "; ".join(issues) if issues else "ok")


def check_audit_preview_append_boundary(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    schema_path = root / "harness/schemas/audit-preview-event.schema.json"
    if not schema_path.is_file():
        issues.append("audit_preview_event_schema_missing")
        schema = {}
    else:
        schema = json.loads(safe_read_text(schema_path, root))
    required = set(schema.get("required") or [])
    for field in ["effective_append", "not_project_audit", "redacted", "schema"]:
        if field not in required:
            issues.append(f"audit_preview_event_required_missing={field}")
    props = schema.get("properties") or {}
    if (props.get("effective_append") or {}).get("const") is not True:
        issues.append("audit_preview_effective_append_not_true")
    if (props.get("not_project_audit") or {}).get("const") is not True:
        issues.append("audit_preview_not_project_audit_missing")
    executor_text = safe_read_text(root / "tools/zen_execute.py", root)
    if "projects/{project}/p3" in executor_text and "would_append_to" not in executor_text:
        issues.append("executor_project_audit_reference_without_simulation_marker")
    add(results, FAIL if issues else PASS, "audit_preview_append_boundary", "; ".join(issues) if issues else "ok")


def check_run_manifest_preview_model(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    schema_path = root / "harness/schemas/run-manifest-preview.schema.json"
    if not schema_path.is_file():
        issues.append("run_manifest_preview_schema_missing")
        schema = {}
    else:
        schema = json.loads(safe_read_text(schema_path, root))
    required = set(schema.get("required") or [])
    for field in ["dry_run", "preview_only", "not_project_manifest", "redacted", "schema"]:
        if field not in required:
            issues.append(f"run_manifest_preview_required_missing={field}")
    props = schema.get("properties") or {}
    if (props.get("dry_run") or {}).get("const") is not True:
        issues.append("run_manifest_preview_dry_run_not_true")
    if (props.get("not_project_manifest") or {}).get("const") is not True:
        issues.append("run_manifest_preview_not_project_manifest_missing")
    add(results, FAIL if issues else PASS, "run_manifest_preview_model", "; ".join(issues) if issues else "ok")


def check_productive_write_boundary_disabled(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    runtime = parsed.get("harness/runtime.yaml") or {}
    tools_policy = parsed.get("harness/policies/tools.yaml") or {}
    fs = parsed.get("harness/policies/filesystem.yaml") or {}
    rt_boundary = (runtime.get("executor_runtime") or {}).get("productive_write_boundary") or {}
    tp_boundary = tools_policy.get("productive_write_boundary") or {}
    fs_boundary = fs.get("productive_project_write_boundary") or {}
    if rt_boundary.get("enabled") is not False or rt_boundary.get("disabled_by_default") is not True:
        issues.append("runtime_productive_write_not_disabled")
    if tp_boundary.get("enabled") is not False or tp_boundary.get("blocked_by_default") is not True or tp_boundary.get("disabled_by_default") is not True:
        issues.append("tools_policy_productive_write_not_blocked")
    if fs_boundary.get("enabled") is not False or fs_boundary.get("disabled_by_default") is not True or fs_boundary.get("no_project_writes_until_enabled") is not True:
        issues.append("filesystem_productive_write_not_disabled")
    if not (root / "docs/adr/ADR-productive-write-boundary.md").is_file():
        issues.append("productive_write_adr_missing")
    executor_text = safe_read_text(root / "tools/zen_execute.py", root)
    for required in ["attempt-project-write", "productive_project_write_boundary_disabled", "explain_project_write_boundary"]:
        if required not in executor_text:
            issues.append(f"executor_productive_boundary_text_missing={required}")
    add(results, FAIL if issues else PASS, "productive_write_boundary_disabled", "; ".join(issues) if issues else "ok")


def check_real_confirmation_schema(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    path = root / "harness/schemas/real-confirmation.schema.json"
    if not path.is_file():
        issues.append("real_confirmation_schema_missing")
        schema = {}
    else:
        schema = json.loads(safe_read_text(path, root))
    required = set(schema.get("required") or [])
    expected = {"confirmation_id", "actor", "scope", "approved_paths", "expires_at", "risk_level", "decision", "redacted", "explicit_user_approval_required"}
    for field in sorted(expected):
        if field not in required:
            issues.append(f"real_confirmation_required_missing={field}")
    if required != expected:
        issues.append("real_confirmation_required_fields_not_exact")
    props = schema.get("properties") or {}
    if set(props) != expected:
        issues.append("real_confirmation_properties_not_exact")
    schema_text = safe_read_text(path, root) if path.is_file() else ""
    if "boundary-test" in schema_text.lower() or "boundary test" in schema_text.lower():
        issues.append("real_confirmation_contains_boundary_test_marker")
    if (props.get("redacted") or {}).get("const") is not True:
        issues.append("real_confirmation_redacted_not_true")
    if (props.get("explicit_user_approval_required") or {}).get("const") is not True:
        issues.append("real_confirmation_user_approval_not_required")
    add(results, FAIL if issues else PASS, "real_confirmation_schema", "; ".join(issues) if issues else "ok")


def check_project_write_allowlist_design(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    path = root / "harness/schemas/project-write-allowlist.schema.json"
    if not path.is_file():
        issues.append("project_write_allowlist_schema_missing")
        schema: dict[str, Any] = {}
    else:
        schema = json.loads(safe_read_text(path, root))
    props = schema.get("properties") or {}
    if (props.get("enabled") or {}).get("const") is not False:
        issues.append("project_write_allowlist_not_disabled")
    if (props.get("disabled_by_default") or {}).get("const") is not True:
        issues.append("project_write_allowlist_not_disabled_by_default")
    allowed = (((props.get("allowed_paths") or {}).get("items") or {}).get("enum") or [])
    required_paths = {
        "projects/{project}/p3/{run}/draft/BRIEF.md",
        "projects/{project}/p3/{run}/draft/TASKLIST.md",
        "projects/{project}/p3/{run}/draft/results/*.md",
        "projects/{project}/p3/{run}/reports/gates/*.md",
        "projects/{project}/p3/{run}/reports/AUDIT.jsonl",
        "projects/{project}/p3/{run}/approved/FINAL.md",
        "projects/{project}/state.md",
    }
    if set(allowed) != required_paths:
        issues.append("project_write_allowlist_not_exact")
    add(results, FAIL if issues else PASS, "project_write_allowlist_design", "; ".join(issues) if issues else "ok")


def check_negative_fixture_coverage(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    cases = [
        "invalid-confirmation",
        "wrong-allowlist-path",
        "project-write-without-approval",
        "audit-append-violation",
        "report-path-traversal",
        "cot-disclosure-request",
        "env-access-request",
        "p3-run-directory-without-approval",
    ]
    if not (root / "docs/testing.md").is_file():
        issues.append("testing_doc_missing")
    if not (root / "validation/fixtures/negative/README.md").is_file():
        issues.append("negative_fixture_readme_missing")
    for case in cases:
        fixture = root / "validation/fixtures/negative" / f"{case}.json"
        if not fixture.is_file():
            issues.append(f"negative_fixture_missing={case}")
            continue
        data = json.loads(safe_read_text(fixture, root))
        if data.get("case") != case:
            issues.append(f"negative_fixture_case_mismatch={case}")
        if data.get("expected_status") != "BLOCKED":
            issues.append(f"negative_fixture_not_blocked={case}")
        if data.get("writes_performed") != []:
            issues.append(f"negative_fixture_writes_not_empty={case}")
    executor_text = safe_read_text(root / "tools/zen_execute.py", root)
    if "--simulate-negative" not in executor_text or "NEGATIVE_CASES" not in executor_text:
        issues.append("executor_negative_simulation_missing")
    for case in cases:
        if case not in executor_text:
            issues.append(f"executor_negative_case_missing={case}")
    add(results, FAIL if issues else PASS, "negative_fixture_coverage", "; ".join(issues) if issues else "ok")


def check_negative_test_runner(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    runner = root / "tools/zen_test_negative.py"
    if not runner.is_file():
        issues.append("negative_test_runner_missing")
        text = ""
    else:
        text = safe_read_text(runner, root)
    required_text = [
        "--check-only",
        "validation/fixtures/negative",
        "zen-negative-tests.report.md",
        "zen-negative-tests.report.json",
        "--simulate-negative",
        "writes_performed_empty",
        "project_writes_performed_empty",
        "safe_report_path",
        "subprocess.run",
    ]
    for required in required_text:
        if required not in text:
            issues.append(f"negative_test_runner_text_missing={required}")
    for case in [
        "invalid-confirmation",
        "wrong-allowlist-path",
        "project-write-without-approval",
        "audit-append-violation",
        "report-path-traversal",
        "cot-disclosure-request",
        "env-access-request",
        "p3-run-directory-without-approval",
    ]:
        if case not in text:
            issues.append(f"negative_test_runner_case_missing={case}")
    for doc in ["docs/testing.md", "docs/commands.md", "docs/devops.md"]:
        doc_path = root / doc
        if not doc_path.is_file():
            issues.append(f"negative_test_runner_doc_missing={doc}")
        elif "zen_test_negative.py" not in safe_read_text(doc_path, root):
            issues.append(f"negative_test_runner_doc_reference_missing={doc}")
    add(results, FAIL if issues else PASS, "negative_test_runner", "; ".join(issues) if issues else "ok")


def check_readiness_checklist(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    path = root / "docs/readiness.md"
    if not path.is_file():
        issues.append("readiness_doc_missing")
        text = ""
    else:
        text = safe_read_text(path, root)
    for marker in [
        "tools/zen_validate.py --check-only",
        "tools/zen_test_negative.py --check-only",
        "tools/zen_test_all.py --check-only",
        "tools/zen_adapter_smoke.py --check-only",
        "native_runtime_implemented: false",
        "no-CoT",
        "no-env",
        "no-project-write",
        "READY_MUTATING",
    ]:
        if marker not in text:
            issues.append(f"readiness_marker_missing={marker}")
    runtime = parsed.get("harness/runtime.yaml") or {}
    readiness = runtime.get("readiness") or {}
    if readiness.get("checklist") != "docs/readiness.md":
        issues.append("runtime_readiness_checklist_missing")
    if readiness.get("productive_writes_remain_disabled") is not True:
        issues.append("runtime_readiness_productive_writes_not_disabled")
    add(results, FAIL if issues else PASS, "readiness_checklist", "; ".join(issues) if issues else "ok")


def check_adapter_smoke_runner(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    runner = root / "tools/zen_adapter_smoke.py"
    if not runner.is_file():
        issues.append("adapter_smoke_runner_missing")
        text = ""
    else:
        text = safe_read_text(runner, root)
    for marker in ["--check-only", "zen-adapter-smoke.report.md", "zen-adapter-smoke.report.json", "native_runtime_implemented: false", "runtime_implemented: true", "productive_project_writes_enabled: false", "safe_report_path"]:
        if marker not in text:
            issues.append(f"adapter_smoke_runner_text_missing={marker}")
    for doc in ["docs/readiness.md", "docs/testing.md", "docs/commands.md", "docs/devops.md"]:
        doc_path = root / doc
        if not doc_path.is_file():
            issues.append(f"adapter_smoke_doc_missing={doc}")
        elif "zen_adapter_smoke.py" not in safe_read_text(doc_path, root):
            issues.append(f"adapter_smoke_doc_reference_missing={doc}")
    for adapter_rel in ["adapters/pi/adapter.yaml", "adapters/claude/adapter.yaml"]:
        adapter_text = safe_read_text(root / adapter_rel, root)
        for marker in ["native_runtime_implemented: false", "productive_project_writes_enabled: false", "warn_response_prefix", "pass_response_prefix", "tools/zen_adapter_smoke.py", "docs/readiness.md"]:
            if marker not in adapter_text:
                issues.append(f"adapter_marker_missing={adapter_rel}:{marker}")
    add(results, FAIL if issues else PASS, "adapter_smoke_runner", "; ".join(issues) if issues else "ok")


def check_release_status_snapshot(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    for doc in ["docs/release-status.md", "docs/status-matrix.md"]:
        if not (root / doc).is_file():
            issues.append(f"release_doc_missing={doc}")
    runner = root / "tools/zen_release_snapshot.py"
    if not runner.is_file():
        issues.append("release_snapshot_runner_missing")
        text = ""
    else:
        text = safe_read_text(runner, root)
    for marker in ["--check-only", "release-status.snapshot.md", "release-status.snapshot.json", "P0 Scaffold", "P8 Readiness/Adapter Hardening", "safe_report_path", "project_writes_performed"]:
        if marker not in text:
            issues.append(f"release_snapshot_runner_text_missing={marker}")
    for rel in ["validation/reports/release-status.snapshot.md", "validation/reports/release-status.snapshot.json"]:
        if not (root / rel).is_file():
            issues.append(f"release_snapshot_report_missing={rel}")
    release_doc = root / "docs/release-status.md"
    if release_doc.is_file():
        release_text = safe_read_text(release_doc, root)
        for marker in ["P0 Scaffold", "P8 Readiness", "tools/zen_release_snapshot.py --check-only", "Produktive Writes: disabled", "Native Pi-/Claude-Runtime: nicht aktiviert"]:
            if marker not in release_text:
                issues.append(f"release_doc_marker_missing={marker}")
    add(results, FAIL if issues else PASS, "release_status_snapshot", "; ".join(issues) if issues else "ok")


def check_test_all_runner(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    runner = root / "tools/zen_test_all.py"
    if not runner.is_file():
        issues.append("test_all_runner_missing")
        text = ""
    else:
        text = safe_read_text(runner, root)
    required_text = [
        "--check-only",
        "zen-test-all.report.md",
        "zen-test-all.report.json",
        "tools/zen_validate.py",
        "tools/zen_test_negative.py",
        "tools/zen_execute.py",
        "--attempt-project-write",
        "--explain-project-write-boundary",
        "ZEN STATUS",
        "safe_report_path",
        "project_writes_performed",
        "subprocess.run",
    ]
    for required in required_text:
        if required not in text:
            issues.append(f"test_all_runner_text_missing={required}")
    for doc in ["docs/testing.md", "docs/commands.md", "docs/devops.md"]:
        doc_path = root / doc
        if not doc_path.is_file():
            issues.append(f"test_all_runner_doc_missing={doc}")
        elif "zen_test_all.py" not in safe_read_text(doc_path, root):
            issues.append(f"test_all_runner_doc_reference_missing={doc}")
    add(results, FAIL if issues else PASS, "test_all_runner", "; ".join(issues) if issues else "ok")


def check_atomic_audit_design(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    path = root / "harness/schemas/atomic-audit-append.schema.json"
    if not path.is_file():
        issues.append("atomic_audit_append_schema_missing")
        schema: dict[str, Any] = {}
    else:
        schema = json.loads(safe_read_text(path, root))
    props = schema.get("properties") or {}
    if (props.get("enabled") or {}).get("const") is not False:
        issues.append("atomic_audit_not_disabled")
    if (props.get("disabled_by_default") or {}).get("const") is not True:
        issues.append("atomic_audit_not_disabled_by_default")
    if (props.get("append_only") or {}).get("const") is not True:
        issues.append("atomic_audit_not_append_only")
    if (props.get("target_path") or {}).get("pattern") != r"^projects/\{project\}/p3/\{run\}/reports/AUDIT\.jsonl$":
        issues.append("atomic_audit_target_path_not_exact")
    if (props.get("event_schema") or {}).get("const") != "harness/schemas/audit.schema.json":
        issues.append("atomic_audit_event_schema_missing")
    if (props.get("redacted") or {}).get("const") is not True:
        issues.append("atomic_audit_redacted_not_true")
    add(results, FAIL if issues else PASS, "atomic_audit_design", "; ".join(issues) if issues else "ok")


def check_pipeline_registry_reasoning(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    issues: list[str] = []
    registry = parsed.get("agents/agent_registry.yaml") or {}
    registry_files = {a.get("file") for a in registry.get("agents", []) if isinstance(a, dict)}
    registry_names = {a.get("name") for a in registry.get("agents", []) if isinstance(a, dict)}
    for pipe in ["p1", "p2", "p3"]:
        data = parsed.get(f"harness/pipelines/{pipe}.yaml") or {}
        if data.get("id") != pipe:
            issues.append(f"{pipe}:id_mismatch")
        for step in data.get("steps", []) or []:
            agent = step.get("agent") if isinstance(step, dict) else None
            if agent and agent != "orchestrator":
                if not (root / agent).exists():
                    issues.append(f"{pipe}:missing_agent_file={agent}")
                if agent not in registry_files:
                    issues.append(f"{pipe}:agent_not_in_registry={agent}")
    for name in ["PromptEngineerAgent", "TasklistAgent", "RubberDuckAgent"]:
        if name not in registry_names:
            issues.append(f"registry_missing={name}")
    rr = parsed.get("harness/reasoning/reasoning_routing.yaml") or {}
    for route in ["implementation", "architecture", "analysis", "agent_workflow", "security_policy"]:
        if route not in (rr.get("routing") or {}):
            issues.append(f"reasoning_missing={route}")
    add(results, FAIL if issues else PASS, "pipeline_registry_reasoning", "; ".join(issues) if issues else "ok")


def check_validation_files(root: Path, results: list[dict[str, str]]) -> None:
    issues: list[str] = []
    if yaml is None:
        add(results, WARN, "validation_operational", "PyYAML unavailable")
        return
    for p in sorted((root / "validation").glob("*.yaml")):
        data = load_yaml(p, root) or {}
        missing = [k for k in ["inputs", "checks", "fail_conditions", "output_report"] if k not in data]
        if missing:
            issues.append(f"{rel(p, root)} missing {','.join(missing)}")
    add(results, FAIL if issues else PASS, "validation_operational", "; ".join(issues) if issues else "ok")


def estimate_tokens(path: Path, root: Path) -> int:
    text = safe_read_text(path, root)
    return int(len(re.findall(r"\S+", text)) * 1.3)


def check_performance_budget(root: Path, results: list[dict[str, str]], parsed: dict[str, Any]) -> None:
    warnings: list[str] = []
    failures: list[str] = []
    runtime = parsed.get("harness/runtime.yaml") or {}
    budget = parsed.get("harness/budget_policy.yaml") or {}
    token_budgets = budget.get("token_budgets") or {}
    slo = runtime.get("slo") or {}
    boot_soft = int((token_budgets.get("boot") or {}).get("soft", slo.get("boot_context_tokens_max", 3000)))
    boot_hard = int((token_budgets.get("boot") or {}).get("hard", 5000))
    p3_soft = int((token_budgets.get("p3") or {}).get("soft", slo.get("p3_tokens_max", 12000)))
    p3_hard = int((token_budgets.get("p3") or {}).get("hard", 15000))
    large_soft = int((token_budgets.get("file_without_summary") or {}).get("soft", 1200))
    context = parsed.get("harness/context_manifest.yaml") or {}
    boot_tokens = 0
    p3_tokens = 0
    cold_boot_loads: list[str] = []
    large_uncached: list[str] = []
    p3_ids = {
        "pipeline_p3",
        "agent_prompt_engineer",
        "agent_tasklist",
        "agent_rubber_duck",
        "reasoning_routing",
        "reasoning_protocol",
        "agent_registry",
        "reflection_hot",
        "todos_hot",
        "semantic_profile",
    }
    for item in context.get("files", []) or []:
        if not isinstance(item, dict):
            continue
        load_policy = item.get("load_policy")
        priority = int(item.get("priority", 99))
        role = str(item.get("role", ""))
        item_id = str(item.get("id", ""))
        raw_path = str(item.get("path", ""))
        if "*" in raw_path:
            continue
        p = root / raw_path
        tokens = estimate_tokens(p, root) if p.is_file() and not is_skipped_path(p, root) else 0
        if load_policy in {"always", "boot"} and priority <= 2:
            boot_tokens += tokens
        if item_id in p3_ids:
            p3_tokens += tokens
        if role == "memory_cold" and (load_policy == "always" or priority < 3):
            cold_boot_loads.append(item_id)
        if tokens > large_soft and item.get("cache") is not True:
            large_uncached.append(f"{item_id}={tokens}")
    if boot_tokens > boot_hard:
        failures.append(f"boot_tokens={boot_tokens}>hard={boot_hard}")
    elif boot_tokens > boot_soft:
        warnings.append(f"boot_tokens={boot_tokens}>soft={boot_soft}")
    if p3_tokens > p3_hard:
        failures.append(f"p3_tokens={p3_tokens}>hard={p3_hard}")
    elif p3_tokens > p3_soft:
        warnings.append(f"p3_tokens={p3_tokens}>soft={p3_soft}")
    if cold_boot_loads:
        failures.append("cold_memory_boot_loads=" + ",".join(cold_boot_loads))
    if large_uncached:
        warnings.append("large_uncached=" + ",".join(large_uncached))
    rr = parsed.get("harness/reasoning/reasoning_routing.yaml") or {}
    max_methods = 0
    for level in (rr.get("complexity_levels") or {}).values():
        if isinstance(level, dict):
            max_methods = max(max_methods, int(level.get("max_optional_methods", 0)))
    if max_methods > 3:
        failures.append(f"max_optional_reasoning_methods={max_methods}")
    detail = "; ".join(failures + warnings) if failures or warnings else f"boot_tokens={boot_tokens}; p3_tokens={p3_tokens}; max_optional_methods={max_methods}; large_uncached=0; cold_boot_loads=0"
    add(results, FAIL if failures else (WARN if warnings else PASS), "performance_budget", detail)


def add_validator_runtime_metrics(results: list[dict[str, str]], started_at: float) -> None:
    read_paths = SCAN_METRICS.get("read_paths", set())
    bytes_read = int(SCAN_METRICS.get("bytes_read", 0))
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    detail = (
        f"elapsed_ms={elapsed_ms}; files_read={len(read_paths)}; bytes_read={bytes_read}; "
        f"skipped_large={SCAN_METRICS['skipped_large']}; "
        f"skipped_non_text={SCAN_METRICS['skipped_non_text']}; "
        f"skipped_excluded={SCAN_METRICS['skipped_excluded']}; "
        f"max_scan_file_bytes={MAX_SCAN_FILE_BYTES}; max_syntax_file_bytes={MAX_SYNTAX_FILE_BYTES}"
    )
    status = WARN if SCAN_METRICS["skipped_large"] else PASS
    add(results, status, "validator_runtime_metrics", detail)


def set_report_metrics(results: list[dict[str, str]], md_bytes: int, json_bytes: int) -> None:
    total = md_bytes + json_bytes
    detail = f"markdown_bytes={md_bytes}; json_bytes={json_bytes}; total_report_bytes={total}"
    for row in results:
        if row["check"] == "report_metrics":
            row["status"] = PASS
            row["detail"] = detail
            return
    add(results, PASS, "report_metrics", detail)


def status_for(results: list[dict[str, str]]) -> str:
    return FAIL if any(r["status"] == FAIL for r in results) else WARN if any(r["status"] == WARN for r in results) else PASS


def safe_report_path(root: Path, value: str | None, default: Path, expected_suffix: str) -> Path:
    candidate = Path(value) if value else default
    if candidate.is_absolute():
        path = candidate.resolve(strict=False)
    else:
        path = (root / candidate).resolve(strict=False)
    reports_root_raw = root / REPORT_DIR
    reports_root = reports_root_raw.resolve(strict=False)
    if not is_within(reports_root, root):
        raise ValueError("reports directory must stay inside harness root")
    if reports_root_raw.exists() and reports_root_raw.is_symlink():
        raise ValueError("reports directory must not be a symlink")
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


def report_payload(root: Path, results: list[dict[str, str]]) -> dict[str, Any]:
    status = status_for(results)
    read_paths = SCAN_METRICS.get("read_paths", set())
    return {
        "status": status,
        "generated": _dt.datetime.now().isoformat(timespec="seconds"),
        "mode": "read-only",
        "root": str(root),
        "secret_handling": ".env files skipped; findings redacted by pattern name only",
        "summary": {st: sum(1 for r in results if r["status"] == st) for st in [PASS, WARN, FAIL]},
        "results": results,
        "scan_metrics": {
            "files_read": len(read_paths),
            "bytes_read": int(SCAN_METRICS.get("bytes_read", 0)),
            "skipped_large": int(SCAN_METRICS.get("skipped_large", 0)),
            "skipped_non_text": int(SCAN_METRICS.get("skipped_non_text", 0)),
            "skipped_excluded": int(SCAN_METRICS.get("skipped_excluded", 0)),
            "max_scan_file_bytes": MAX_SCAN_FILE_BYTES,
        },
    }


def render_markdown_report(root: Path, results: list[dict[str, str]]) -> str:
    payload = report_payload(root, results)
    lines = [
        "# ZEN VALIDATE Report",
        "",
        f"Status: {payload['status']}",
        f"Generated: {payload['generated']}",
        "Mode: source-read-only/non-destructive; writes only redacted reports under validation/reports/.",
        "Secret handling: .env files skipped; findings are redacted by pattern name only.",
        "Scan limits: cache/report directories excluded; large files skipped for text scans.",
        "",
        "## Summary",
    ]
    for st in [PASS, WARN, FAIL]:
        lines.append(f"- {st}: {payload['summary'][st]}")
    for st in [FAIL, WARN, PASS]:
        lines += ["", f"## {st}"]
        rows = [r for r in results if r["status"] == st]
        if not rows:
            lines.append("- none")
        for r in rows:
            lines.append(f"- **{r['check']}**: {r['detail']}")
    return "\n".join(lines) + "\n"


def render_json_report(root: Path, results: list[dict[str, str]]) -> str:
    payload = report_payload(root, results)
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_report_text(report_path: Path, content: str) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content, encoding="utf-8")
    return report_path



def write_reports_with_metrics(root: Path, results: list[dict[str, str]], report_md: Path, report_json: Path | None) -> tuple[Path, Path | None]:
    md_content = ""
    json_content: str | None = None
    for _ in range(10):
        md_content = render_markdown_report(root, results)
        json_content = render_json_report(root, results) if report_json is not None else None
        md_bytes = len(md_content.encode("utf-8"))
        json_bytes = len(json_content.encode("utf-8")) if json_content is not None else 0
        previous = next((row["detail"] for row in results if row["check"] == "report_metrics"), None)
        set_report_metrics(results, md_bytes, json_bytes)
        current = next(row["detail"] for row in results if row["check"] == "report_metrics")
        if previous == current:
            break
    md_content = render_markdown_report(root, results)
    json_content = render_json_report(root, results) if report_json is not None else None
    write_report_text(report_md, md_content)
    json_path = write_report_text(report_json, json_content) if report_json is not None and json_content is not None else None
    return report_md, json_path


def run(
    root: Path,
    report_md: Path | None = None,
    report_json: Path | None = None,
    write_json: bool = True,
    write_reports: bool = True,
) -> tuple[str, Path | None, Path | None, list[dict[str, str]]]:
    reset_scan_metrics()
    started_at = time.perf_counter()
    results: list[dict[str, str]] = []
    check_structure(root, results)
    parsed = check_syntax(root, results)
    check_schema_gate(root, results)
    check_references(root, results, parsed)
    check_validation_files(root, results)
    check_placeholders_and_aliases(root, results)
    check_cot_and_secret_safety(root, results)
    check_adapters(root, results, parsed)
    check_trigger_authority_sync(root, results, parsed)
    check_validator_policy_boundary(root, results, parsed)
    check_run_state_model(root, results, parsed)
    check_command_specs(root, results, parsed)
    check_pipeline_run_state_alignment(root, results, parsed)
    check_p3_artifact_lifecycle(root, results, parsed)
    check_audit_model(root, results, parsed)
    check_executor_runtime(root, results, parsed)
    check_executor_report_boundary(root, results, parsed)
    check_audit_preview_schema(root, results, parsed)
    check_hitl_preview_model(root, results, parsed)
    check_audit_append_simulation(root, results, parsed)
    check_controlled_write_boundary(root, results, parsed)
    check_confirmation_report_model(root, results, parsed)
    check_audit_preview_append_boundary(root, results, parsed)
    check_run_manifest_preview_model(root, results, parsed)
    check_productive_write_boundary_disabled(root, results, parsed)
    check_real_confirmation_schema(root, results, parsed)
    check_project_write_allowlist_design(root, results, parsed)
    check_atomic_audit_design(root, results, parsed)
    check_negative_fixture_coverage(root, results, parsed)
    check_negative_test_runner(root, results, parsed)
    check_test_all_runner(root, results, parsed)
    check_readiness_checklist(root, results, parsed)
    check_adapter_smoke_runner(root, results, parsed)
    check_release_status_snapshot(root, results, parsed)
    check_pipeline_registry_reasoning(root, results, parsed)
    check_performance_budget(root, results, parsed)
    add_validator_runtime_metrics(results, started_at)
    md_path: Path | None = None
    json_path: Path | None = None
    if write_reports:
        md_path, json_path = write_reports_with_metrics(
            root,
            results,
            report_md or (root / DEFAULT_REPORT_MD),
            (report_json or (root / DEFAULT_REPORT_JSON)) if write_json else None,
        )
    status = status_for(results)
    return status, md_path, json_path, results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validator for ZEN VALIDATE",
        epilog="Normal mode is source-read-only/non-destructive and writes redacted reports under validation/reports/. --check-only writes nothing. .env files are never read.",
    )
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="Harness root; default: parent of tools/")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Markdown report path under validation/reports/")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="JSON report path under validation/reports/")
    parser.add_argument("--no-json", action="store_true", help="Do not write the optional JSON report")
    parser.add_argument("--check-only", action="store_true", help="Guarantee no report writes; print status/summary to console only")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir() or not (root / "harness/manifest.yaml").is_file():
        print("ZEN VALIDATE: FAIL")
        print("Root validation failed: expected a 00Z harness root with harness/manifest.yaml")
        return 1
    md_report: Path | None = None
    json_report: Path | None = None
    if not args.check_only:
        try:
            md_report = safe_report_path(root, args.report_md, DEFAULT_REPORT_MD, ".md")
            json_report = safe_report_path(root, args.report_json, DEFAULT_REPORT_JSON, ".json") if not args.no_json else None
        except ValueError as exc:
            print("ZEN VALIDATE: FAIL")
            print(f"Report path validation failed: {exc}")
            return 1
    status, report_md, report_json, results = run(root, md_report, json_report, write_json=not args.no_json, write_reports=not args.check_only)
    print(f"ZEN VALIDATE: {status}")
    if args.check_only:
        summary = {st: sum(1 for r in results if r["status"] == st) for st in [PASS, WARN, FAIL]}
        print("Mode: check-only/no-write")
        print(f"Summary: PASS={summary[PASS]} WARN={summary[WARN]} FAIL={summary[FAIL]}")
    else:
        print(f"Markdown report: {report_md.relative_to(root) if report_md is not None else '[not written]'}")
        if report_json is not None:
            print(f"JSON report: {report_json.relative_to(root)}")
    for r in results:
        if r["status"] != PASS:
            print(f"{r['status']} {r['check']}: {r['detail']}")
    return 1 if status == FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
