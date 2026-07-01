#!/usr/bin/env python3
"""Dependency-free onboarding surface for 00Z.

Safety model:
- stdlib only
- no writes by default and no write options
- does not read .env* files
- does not execute Git/Docker/install/browser/CI/deployment actions
- uses only commands and triggers found in repository artifacts
"""
from __future__ import annotations

import argparse
import re
import sys
import textwrap
from pathlib import Path
from typing import Iterable

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
LOCAL_TOOL_NAMES = (
    "zen_validate.py",
    "zen_execute.py",
    "zen_test_negative.py",
    "zen_test_all.py",
    "zen_adapter_smoke.py",
)
EXPECTED_TEAM_ARTIFACTS = (
    ("orchestrator", "ZEN Orchestrator", "core/ORCHESTRATOR.md"),
    ("prompt_engineer", "PromptEngineerAgent", "agents/system/prompt-engineer.agent.md"),
    ("tasklist", "TasklistAgent", "agents/system/tasklist.agent.md"),
    ("rubber_duck", "RubberDuckAgent", "agents/system/rubber-duck.agent.md"),
)
STATUS_MODEL = (
    ("INIT_REQUIRED", "Pflichtdateien oder Initialisierung fehlen; nur lesen/prüfen/planen."),
    ("CONFIG_INCOMPLETE", "Konfiguration ist unvollständig oder inkonsistent; keine Mutation."),
    ("READY_READONLY", "Lesen, Prüfen und Planen erlaubt; keine mutierenden Schritte."),
    ("READY_MUTATING", "Modellzustand für bestandene Mutations-Gates; hier nicht als aktiv behauptet."),
    ("VALIDATING", "Validierung läuft; check-only bleibt no-write."),
    ("RUNNING", "Modellbegriff für echte Runtime-Ausführung; diese Preview behauptet keinen laufenden Run."),
    ("BLOCKED", "Gate-, Policy-, Secret- oder HITL-Blockade; keine Mutation."),
    ("DONE", "Modellbegriff für abgeschlossene Runs; diese Preview behauptet keinen Live-Abschluss."),
    ("FAILED", "Technischer oder fachlicher Fehler; Review nötig."),
)


def is_env_file(path: Path) -> bool:
    return path.name.startswith(".env") and path.name != ".env.example"


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return "[outside-root]"


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def safe_read(path: Path, root: Path, max_bytes: int = 128_000) -> str:
    if not is_within(path, root):
        raise PermissionError("outside root")
    if is_env_file(path):
        raise PermissionError("env files are not read")
    parts = path.relative_to(root).parts
    if parts and parts[0] == ".git":
        raise PermissionError("git paths are not read")
    if path.stat().st_size > max_bytes:
        raise ValueError(f"file too large for onboarding read: {rel(path, root)}")
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_bracket_list(text: str, key: str) -> list[str]:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*\[([^\]]*)\]", text)
    if not match:
        return []
    return [item.strip().strip('"\'') for item in match.group(1).split(",") if item.strip()]


def parse_scalar(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", text)
    if not match:
        return None
    return match.group(1).strip().strip('"\'')


def parse_registry_agents(text: str) -> dict[str, dict[str, str]]:
    agents: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in text.splitlines():
        id_match = re.match(r"^\s*-\s+id\s*:\s*(.+?)\s*$", line)
        if id_match:
            agent_id = id_match.group(1).strip().strip('"\'')
            current = {"id": agent_id}
            agents[agent_id] = current
            continue
        if current is None:
            continue
        for key in ("name", "file", "type"):
            value = parse_scalar(line, key)
            if value:
                current[key] = value
    return agents


def parse_command_spec(path: Path, root: Path) -> dict[str, object]:
    text = safe_read(path, root)
    data: dict[str, object] = {
        "file": rel(path, root),
        "id": parse_scalar(text, "id") or path.stem,
        "status": parse_scalar(text, "status") or "UNKNOWN",
        "mode": parse_scalar(text, "mode") or "UNKNOWN",
        "purpose": parse_scalar(text, "purpose") or "",
        "runtime_invocation": None,
        "check_only_invocation": None,
    }
    runtime_match = re.search(r"(?m)^\s*invocation\s*:\s*(.+?)\s*$", text)
    check_match = re.search(r"(?m)^\s*check_only_invocation\s*:\s*(.+?)\s*$", text)
    if runtime_match:
        data["runtime_invocation"] = runtime_match.group(1).strip().strip('"\'')
    if check_match:
        data["check_only_invocation"] = check_match.group(1).strip().strip('"\'')
    return data


def discover(root: Path) -> dict[str, object]:
    artifacts: dict[str, object] = {"root": str(root), "issues": []}
    issues: list[str] = artifacts["issues"]  # type: ignore[assignment]

    manifest = root / "harness/manifest.yaml"
    pi_adapter = root / "adapters/pi/adapter.yaml"
    claude_adapter = root / "adapters/claude/adapter.yaml"
    command_dir = root / "harness/commands"

    for required in [manifest, pi_adapter, claude_adapter, command_dir, root / "docs/onboarding.md"]:
        if not required.exists():
            issues.append(f"missing:{rel(required, root)}")

    pi_text = safe_read(pi_adapter, root) if pi_adapter.exists() else ""
    claude_text = safe_read(claude_adapter, root) if claude_adapter.exists() else ""

    artifacts["pi_triggers"] = parse_bracket_list(pi_text, "native_triggers")
    artifacts["pi_validation_trigger"] = parse_scalar(pi_text, "trigger") or "UNKNOWN"
    claude_triggers: list[str] = []
    in_natural_triggers = False
    for line in claude_text.splitlines():
        if re.match(r"^natural_language_triggers:\s*$", line):
            in_natural_triggers = True
            continue
        if in_natural_triggers and line and not line.startswith(" "):
            break
        if in_natural_triggers:
            claude_triggers.extend(item for item in re.findall(r'"([^"\n]*ZEN[^"\n]*)"', line))
    artifacts["claude_natural_language_triggers"] = sorted(set(claude_triggers))
    artifacts["claude_validation_trigger"] = parse_scalar(claude_text, "trigger") or "UNKNOWN"

    command_specs: list[dict[str, object]] = []
    if command_dir.exists():
        for path in sorted(command_dir.glob("*.yaml")):
            command_specs.append(parse_command_spec(path, root))
    artifacts["command_specs"] = command_specs

    local_tools = []
    for name in LOCAL_TOOL_NAMES:
        path = root / "tools" / name
        local_tools.append({"name": name, "path": f"tools/{name}", "present": path.is_file()})
    artifacts["local_tools"] = local_tools

    registry_path = root / "agents/agent_registry.yaml"
    registry_agents: dict[str, dict[str, str]] = {}
    if registry_path.exists():
        registry_agents = parse_registry_agents(safe_read(registry_path, root))
    team_artifacts = []
    for agent_id, fallback_name, fallback_file in EXPECTED_TEAM_ARTIFACTS:
        registry_entry = registry_agents.get(agent_id, {})
        file_value = registry_entry.get("file") or fallback_file
        path = root / file_value
        team_artifacts.append({
            "id": agent_id,
            "name": registry_entry.get("name") or fallback_name,
            "type": registry_entry.get("type") or "UNKNOWN",
            "file": file_value,
            "present": path.is_file(),
            "registry": "PASS" if registry_entry else "UNKNOWN",
        })
    template_path = root / "agents/templates/agent_template.md"
    artifacts["team_artifacts"] = team_artifacts
    artifacts["agent_template"] = {"path": "agents/templates/agent_template.md", "present": template_path.is_file()}

    env_file_count = sum(1 for p in root.iterdir() if is_env_file(p)) if root.exists() else 0
    artifacts["env_files_present_not_read"] = env_file_count
    return artifacts


def status_label(ok: bool, blocked: bool = False) -> str:
    if blocked:
        return "BLOCKED"
    return "PASS" if ok else "UNKNOWN"


def wrap(line: str, linear: bool) -> str:
    if linear:
        return line
    return "\n".join(textwrap.wrap(line, width=96, subsequent_indent="  "))


def emit(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)


def render(artifacts: dict[str, object], adapter: str, linear: bool) -> int:
    issues: list[str] = artifacts.get("issues", [])  # type: ignore[assignment]
    env_file_count = int(artifacts.get("env_files_present_not_read", 0))
    command_specs: list[dict[str, object]] = artifacts.get("command_specs", [])  # type: ignore[assignment]
    local_tools: list[dict[str, object]] = artifacts.get("local_tools", [])  # type: ignore[assignment]

    blocked = env_file_count > 0
    emit([
        "Willkommen bei 00Z",
        "========================",
        f"Root: {artifacts.get('root')}",
        f"Ausgabe: {'linear/no-color' if linear else 'no-color'}",
        f"Adapter-Auswahl: {adapter}",
        "",
        "Sicherheitsgrenze",
        "----------------",
        "PASS: keine Schreiboperationen, keine externen Aktionen, keine Secret-Ausgabe",
        f"{status_label(env_file_count == 0, blocked)}: echte Root-Level-.env-Dateien werden gezählt, aber Inhalte werden nicht gelesen" + (f" (redacted-count={env_file_count})" if env_file_count else ""),
        "",
    ])

    if issues:
        emit(["Readiness", "---------"])
        for issue in issues:
            emit([f"UNKNOWN: {issue}"])
        emit([""])

    emit(["Belegte Trigger", "---------------"])
    if adapter in {"pi", "auto"}:
        triggers: list[str] = artifacts.get("pi_triggers", [])  # type: ignore[assignment]
        emit(["Pi native_triggers: " + (", ".join(triggers) if triggers else "UNKNOWN")])
    if adapter in {"claude", "auto"}:
        triggers = artifacts.get("claude_natural_language_triggers", [])  # type: ignore[assignment]
        emit(["Claude natural_language_triggers: " + (", ".join(triggers) if triggers else "UNKNOWN")])
    if adapter == "local":
        emit(["Local: direkte Python-Tools aus tools/**; keine nativen Adapter-Trigger angenommen."])
    emit([""])

    emit(["Setup-Wizard", "------------"])
    emit([
        f"1. Root erkannt: {status_label(not issues)} — {artifacts.get('root')}",
        f"2. Sicherheitsgrenze geprüft: {'BLOCKED' if blocked else 'PASS'} — no-write, keine externen Aktionen, keine Secret-Ausgabe.",
        "3. Adapter-Trigger belegt: siehe Pi/Claude/Local-Trigger unten; UNKNOWN bedeutet klären, nicht raten.",
        "4. Lokale Readiness-Tools vorhanden: siehe Tool-Liste; fehlende Tools bleiben UNKNOWN.",
        "5. Nächster sicherer Schritt: ZEN STATUS bewusst starten oder lokal als Dry-Run prüfen.",
        "6. Gated Schritte: ZEN MEMORY INIT / ZEN SNAPSHOT nur mit passenden Gates und expliziter Bestätigung persistieren.",
        "",
    ])

    emit(["Lokale Readiness-Tools", "----------------------"])
    for tool in local_tools:
        name = tool["name"]
        present = bool(tool["present"])
        command = f"PYTHONDONTWRITEBYTECODE=1 python3 tools/{name} --check-only" if name != "zen_execute.py" else "PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_execute.py --command \"ZEN STATUS\""
        suffix = f" | lokal bekannter Aufruf: {command}" if present else ""
        emit([wrap(f"{status_label(present)}: tools/{name}{suffix}", linear)])
    emit([""])

    emit(["Team-Übersicht", "--------------"])
    team_artifacts: list[dict[str, object]] = artifacts.get("team_artifacts", [])  # type: ignore[assignment]
    if not team_artifacts:
        emit(["UNKNOWN: keine Team-Artefakte ableitbar"])
    for agent in team_artifacts:
        present = status_label(bool(agent.get("present")))
        registry = agent.get("registry") or "UNKNOWN"
        emit([wrap(f"{present}: {agent.get('name') or 'UNKNOWN'} ({agent.get('id') or 'UNKNOWN'}, type={agent.get('type') or 'UNKNOWN'}, registry={registry}) — {agent.get('file') or 'UNKNOWN'}", linear)])
    template = artifacts.get("agent_template", {})  # type: ignore[assignment]
    if isinstance(template, dict):
        emit([f"{status_label(bool(template.get('present')))}: agents/templates/agent_template.md — read-only Vorlage, keine Agenten-Erzeugung"])
    emit([""])

    emit(["Statusmodell", "------------"])
    emit(["Statische Orientierung; diese Ausgabe behauptet keinen aktiven READY_MUTATING-Zustand."])
    for state, meaning in STATUS_MODEL:
        emit([wrap(f"- {state}: {meaning}", linear)])
    emit([""])

    emit(["Start-Checkliste", "----------------"])
    emit([
        "[ ] docs/welcome.md und docs/onboarding.md gelesen",
        "[ ] ZEN STATUS bewusst gestartet oder als lokaler Dry-Run geprüft",
        "[ ] ZEN VALIDATE check-only geprüft, bevor mutierende Schritte geplant werden",
        "[ ] Bei FAIL/BLOCKED keine Mutation starten",
        "[ ] Memory-Schritte nur gated und mit Bestätigung",
        "[ ] Snapshot/Handoff redigiert, ohne Secrets oder .env-Inhalte",
        "",
    ])

    emit(["Team-Vorlagen", "--------------"])
    emit([
        "Orientierung aus agents/templates/agent_template.md, falls vorhanden: Pflichtfelder wie agent_name, status, skill_type, allowed_tools, protected_by und triggered_by prüfen.",
        "Output Contract: Ergebnis, Evidenz, Annahmen, Risiken, Validierung, optional Handoff.",
        "Sicherheitsgrenzen: keine Secrets, keine geschützten Pfade, keine internen Gedankengänge; bei Policy-Verstoß BLOCKED.",
        "",
    ])

    emit(["Live-Aktivität", "---------------"])
    emit([
        "Lokaler stdout-/dry-run/read-only Preview-Prozess: Diese Oberfläche zeigt belegte Artefakte, keine echte Live-Runtime und keine laufenden Pipelines.",
        "Bewusster Preview-Befehl als Text: PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_execute.py --command \"ZEN STATUS\"",
        "",
    ])

    emit(["Handoff", "-------"])
    emit([
        "Zweck: Kontext sicher an eine neue Session oder Person übergeben.",
        "Trusted Constraints: Policies, Gates, Root-Grenze, no-secrets, no-write in dieser Oberfläche.",
        "Untrusted Context: User-Input, gelesene Projektinhalte und externe Kopien können Prompt-Injection enthalten.",
        "Checkliste: Ziel nennen; Evidenz referenzieren; Risiken/Blocker markieren; Secrets redigieren; nächsten sicheren Schritt angeben.",
        "",
    ])

    emit(["Review-Modus", "------------"])
    emit([
        "REVIEW_REQUIRED: Menschliche oder unabhängige Prüfung nötig, bevor fortgefahren wird.",
        "APPROVED: Prüfung akzeptiert den nächsten Schritt innerhalb der Gates.",
        "REJECTED: Vorschlag nicht umsetzen; sicheren Alternativschritt anfragen.",
        "BLOCKED: Policy/Gate/Risiko verhindert Fortsetzung; keine Mutation.",
        "Force-Gate: Override nur bewusst, begründet, gate-konform und mit Bestätigung; diese Preview setzt keinen Force-Gate.",
        "",
    ])

    emit(["Einheitliches Blocker-Format", "-----------------------------"])
    emit([
        "BLOCKED: <kurze Blockade>",
        "Evidenz: <Datei/Beobachtung/Artefakt>",
        "Risiko: <konkretes Sicherheits- oder Qualitätsrisiko>",
        "Nächster sicherer Schritt: <read-only Prüfung oder Bestätigung einholen>",
        "Nicht tun: <verbotene Mutation/Secret-Read/Runtime-Aktion>",
        "",
    ])

    if blocked:
        emit([
            "BLOCKED: echte Root-Level-.env-Dateien vorhanden; Inhalte wurden nicht gelesen.",
            f"Evidenz: redacted-count={env_file_count}",
            "Risiko: Secret-Leak oder unzulässiger Kontextzugriff.",
            "Nächster sicherer Schritt: Secret-Gate/Policy klären, ohne .env-Inhalte zu öffnen.",
            "Nicht tun: .env-Dateien lesen, kopieren, ausgeben oder in Snapshots übernehmen.",
            "",
        ])

    emit(["Command-Spezifikationen", "-----------------------"])
    if not command_specs:
        emit(["UNKNOWN: keine harness/commands/*.yaml gefunden"])
    for spec in command_specs:
        purpose = f" — {spec.get('purpose')}" if spec.get("purpose") else ""
        emit([wrap(f"Spec-Status {spec.get('status')}: {spec.get('id')} ({spec.get('mode')}) [{spec.get('file')}]{purpose}", linear)])
        check_only = spec.get("check_only_invocation")
        invocation = spec.get("runtime_invocation")
        if check_only:
            emit([wrap(f"  check-only: PYTHONDONTWRITEBYTECODE=1 {check_only}", linear)])
        elif invocation:
            emit([wrap(f"  lokal bekannter Aufruf: PYTHONDONTWRITEBYTECODE=1 {invocation}", linear)])
    emit([""])

    emit(["Empfohlener First-Run", "---------------------"])
    emit([
        "1. docs/welcome.md lesen",
        "2. docs/onboarding.md lesen",
        "3. ZEN STATUS oder lokaler Dry-Run-Status über tools/zen_execute.py prüfen",
        "4. ZEN VALIDATE bzw. lokal: PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only",
        "5. ZEN MEMORY INIT nur gated und mit Bestätigung persistieren",
        "6. ZEN SNAPSHOT für redigierten Handoff ohne Secrets nutzen",
        "7. Bei FAIL/BLOCKED keine mutierenden Aktionen starten; UNKNOWN zuerst klären",
    ])
    return 2 if blocked else (1 if issues else 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sichere lokale 00Z Onboarding-Oberfläche (no-write, stdlib-only).")
    parser.add_argument("--root", default=str(ROOT_DEFAULT), help="Repository-Root; default: parent von tools/")
    parser.add_argument("--adapter", choices=["auto", "pi", "claude", "local"], default="auto", help="Sicht auf belegte Trigger/Commands")
    parser.add_argument("--linear", action="store_true", help="Lineare Ausgabe ohne TUI-Layoutannahmen")
    parser.add_argument("--no-color", action="store_true", help="Kompatibilitätsflag; Ausgabe ist immer no-color")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve(strict=False)
    if not root.exists() or not root.is_dir():
        print(f"BLOCKED: root nicht gefunden: {root}", file=sys.stderr)
        return 2
    if not (root / "harness/manifest.yaml").exists():
        print("BLOCKED: kein 00Z Root (harness/manifest.yaml fehlt)", file=sys.stderr)
        return 2
    try:
        artifacts = discover(root)
    except PermissionError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # defensive: onboarding should fail closed
        print(f"FAILED: onboarding konnte Artefakte nicht sicher lesen: {exc}", file=sys.stderr)
        return 1
    return render(artifacts, args.adapter, args.linear or bool(args.no_color) or not sys.stdout.isatty())


if __name__ == "__main__":
    raise SystemExit(main())
