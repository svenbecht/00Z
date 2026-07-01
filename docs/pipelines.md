# Pipelines — 00Z

## Übersicht

`00Z` nutzt drei Eskalationsstufen. Die Benennung ist ausschließlich P1/P2/P3; alte alternative Namen werden nicht verwendet.

| Pipeline | Trigger | Zweck | Agenten | Gate |
|---|---|---|---|---|
| P1 | `ZEN P1` | Direkter Expertendialog | 1 Orchestrator | nein |
| P2 | `ZEN P2` | Prompt Brief für einen Ziel-Agenten | 1 Agent | optional manuell |
| P3 | `ZEN P3` | Multi-Agent Flow bis max. 3 Tasks | max. 3 | Force Gate |

## P1 — Ask

Geeignet für kurze Fragen, Planverfeinerung und read-only Analyse. P1 schreibt standardmäßig keine Dateien und eskaliert zu P2/P3, wenn strukturierte Übergabe oder Gate-Prüfung nötig ist.

## P2 — Prompt Brief

Der Orchestrator erstellt einen vollständigen Brief mit Ziel, Kontext, Input, Output, Constraints, Erfolgskriterium und Risiken. Der User bestätigt den Ziel-Agenten. Persistenz erfolgt nur nach expliziter Bestätigung.

## P3 — Mid Pipeline

Ablauf:

1. Orchestrator bereitet Run-Kontext und Gates vor.
2. PromptEngineerAgent erzeugt Brief.
3. TasklistAgent zerlegt in maximal drei Tasks.
4. Optionales Tasklist-Gate durch RubberDuckAgent.
5. Zugewiesene Agenten führen Tasks parallel oder sequenziell aus.
6. Orchestrator synthetisiert Ergebnisse.
7. RubberDuckAgent führt Force Gate aus.
8. Nur bei `APPROVED` wird persistiert.

## Gate-Semantik

- `APPROVED`: Weiter oder speichern.
- `REJECTED`: Rework, maximal zwei Zyklen.
- `BLOCKED`: Stop, User-Entscheidung nötig.

## P3-Artefakt-Lifecycle

P3-Artefakte folgen einem expliziten Lifecycle:

```text
transient -> draft -> approved -> persisted -> archived
                 \-> rejected -> archived
```

| Phase | Bedeutung | Pfad/Zonen |
|---|---|---|
| `transient` | Nur im Kontext/Handoff, keine Datei | memory-only |
| `draft` | Vorläufige Artefakte, weiterhin untrusted | `projects/{project}/p3/{date}_{sequence}/draft/` |
| `approved` | Durch Force Gate freigegeben | `projects/{project}/p3/{date}_{sequence}/approved/` |
| `persisted` | Finales Projektartefakt nach Secret-/Filesystem-/Prompt-Injection-Gates | `projects/{project}/p3/{date}_{sequence}/approved/` plus Projekt-State |
| `rejected` | Abgelehnt oder blockiert, nur zur Nachvollziehbarkeit | `projects/{project}/p3/{date}_{sequence}/rejected/` |
| `archived` | Explizit bestätigte Ablage | `projects/{project}/p3/{date}_{sequence}/archive/` |

`READY_READONLY` darf nur Intake, Dry-Run und Planung erzeugen; Persistenz benötigt `READY_MUTATING`, Gates und Confirmation. Draft-Persistenz benötigt `READY_MUTATING` + Filesystem/Secret/Prompt-Injection Gates + Confirmation. Finales Persistieren benötigt zusätzlich Force-Gate `APPROVED`.

## P3 Run Manifest

P3 Run Manifests folgen `harness/schemas/run-manifest.schema.json`. Im aktuellen Dry-Run-First Executor werden Manifeste nur als Modell/Preview behandelt und nicht geschrieben. Ein echtes `RUN_MANIFEST.json` darf erst mit Executor-Write-Boundary, `READY_MUTATING`, Gates und HITL entstehen.

## HITL Confirmation

HITL Confirmations folgen `harness/schemas/hitl-confirmation.schema.json`. Confirmation IDs nutzen das Format `hitl_YYYYMMDDTHHMMSSZ_suffix` und sind für P3-Persistenz, Archivierung sowie High-/Critical-Risk-Writes erforderlich.

## Audit-Log-Modell

P3-Runs führen ein append-only Audit-Modell unter `projects/{project}/p3/{date}_{sequence}/reports/AUDIT.jsonl` gemäß `harness/schemas/audit.schema.json`.

Audit-Events:

- `pipeline_run`
- `tool_call`
- `gate_decision`
- `hitl_confirmation`
- `policy_block`

Pflichtfelder: `timestamp`, `run_id`, `actor`, `event_type`, `target_paths`, `risk_level`, `trust_zone`, `decision`, `result`, `redacted`. `redacted` ist im Schema verpflichtend und muss `true` sein. Secret-Werte sind verboten; Reports/Audit-Einträge müssen redigiert sein.

Nach Approval sind Schreibziele eng begrenzt: `approved/**`, `reports/**`, `archive/**` sowie explizite State-Updates. Draft- und Rejected-Zonen dürfen nach Approval nicht als finale Persistenzziele verwendet werden.
