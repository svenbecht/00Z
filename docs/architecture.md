# Architektur — 00Z

## Zielbild

`00Z` ist ein lokales, security-first Agent-Harness für Pi und Claude. Die Architektur ist YAML-/Markdown-first: Policies, Gates, Pipelines, Adapter und Agenten werden deklarativ beschrieben; `tools/zen_validate.py` bildet die lokale Validator Runtime Boundary.

## Routing-State vs. Run-State

Das Harness trennt zwei Zustandsmodelle:

- **Trigger-State-Machine / Routing**: `harness/state_machine.yaml#transitions` routet ZEN-Trigger auf Commands und Pipelines. Zustände wie `IDLE`, `PIPELINE`, `P3_PIPELINE` oder `VALIDATE` sind Routing-Zustände.
- **Run-State-Lifecycle / Security**: `harness/state_machine.yaml#run_state_model` und `harness/runtime.yaml#run_state_model` steuern Lebenszyklus, Gate-Status, Mutationsfreigabe und Fehlerbehandlung.

## Run-State-Modell

Autoritative Quelle: `harness/state_machine.yaml#run_state_model`. Runtime-Spiegel: `harness/runtime.yaml#run_state_model`.

| State | Bedeutung | Mutationen |
|---|---|---|
| `INIT_REQUIRED` | Pflichtdateien oder Initialisierung fehlen | nein |
| `CONFIG_INCOMPLETE` | Konfiguration vorhanden, aber unvollständig/inkonsistent | nein |
| `READY_READONLY` | Lesen, Prüfen, Planen erlaubt; keine Persistenz außer Validator-Reports | nein |
| `READY_MUTATING` | Mutierende Tools gemäß Policies und User-Freigabe erlaubt | policy-gated |
| `VALIDATING` | `ZEN VALIDATE` läuft | nur Validator-Reports im Normalmodus |
| `RUNNING` | Command oder P1/P2/P3 läuft | gemäß Pipeline-/Tool-Policy |
| `BLOCKED` | Gate-, Policy-, Secret-, Prompt-Injection- oder HITL-Blockade | nein |
| `DONE` | Run abgeschlossen | nein, außer neuer freigegebener Run |
| `FAILED` | Technischer/fachlicher Fehler | nein, Review nötig |

## Kontrollfluss

```text
Boot
  → INIT_REQUIRED | CONFIG_INCOMPLETE | READY_READONLY
Onboarding + Pflicht-Gates PASS
  → READY_READONLY
Mutation-Gates + ggf. User Confirmation PASS
  → READY_MUTATING
ZEN VALIDATE
  → VALIDATING → READY_READONLY | BLOCKED | FAILED
P1/P2/P3 oder Command
  → RUNNING → DONE | BLOCKED | FAILED
```

## Gate-Grenzen

- Read-only: `required_files_exist`, `placeholder_gate`, `policy_gate`, `adapter_gate`.
- Mutating: `onboarding_gate`, `policy_gate`, `filesystem_gate`, `secret_gate`, `prompt_injection_gate`, ggf. Human Confirmation.
- P3 zusätzlich: Force Gate vor Persistenz.
- Validator Normalmodus: source-read-only/non-destructive mit kontrollierten Reports unter `validation/reports/`.
- Validator `--check-only`: no-write.

## Executor Runtime — Dry-Run First

P2 führt `tools/zen_execute.py` als minimale Executor-Preview-Runtime ein. Sie ist dry-run-first, schreibt keine Projektartefakte, erzeugt keine P3-Run-Verzeichnisse und appendet keine Audit-Logs. Stattdessen gibt sie ein redigiertes Audit-Preview-JSON auf stdout aus. Optional schreibt `--write-report` nur kontrollierte Preview-Reports unter `validation/reports/*.preview.json`. `--preview-hitl` erzeugt keine echte Freigabe: `decision: preview_only`, `effective_confirmation: false`. P3 Controlled Write Boundary bleibt auf `validation/reports/` beschränkt: `*.confirmation.json`, `*.audit-preview.jsonl`, `*.run-manifest.preview.json`. Diese Reports tragen Schutzmarker wie `not_project_authorization`, `not_project_audit`, `not_project_manifest` oder `production_scope: false`. Insbesondere bedeutet `effective_confirmation: true` in `*.confirmation.json` nur Boundary-Test-Wirksamkeit innerhalb `validation/reports/`, niemals produktive Projektfreigabe. Ein späterer produktiver Write-Boundary benötigt `READY_MUTATING`, Gates und echte HITL Confirmation über separates ADR/Schema.

Schemas:

- P3 Run Manifest: `harness/schemas/run-manifest.schema.json`
- HITL Confirmation: `harness/schemas/hitl-confirmation.schema.json`
- HITL Preview: `harness/schemas/hitl-preview.schema.json`
- Audit Event: `harness/schemas/audit.schema.json`
- Audit Preview: `harness/schemas/audit-preview.schema.json`

## Produktive Projektwrites — Design-only / Disabled

Produktive Projektwrites sind nicht aktiv. Das Design liegt in `docs/adr/ADR-productive-write-boundary.md` und den Schemas `real-confirmation`, `project-write-allowlist` und `atomic-audit-append`. `tools/zen_execute.py --attempt-project-write` muss blockieren; `--explain-project-write-boundary` schreibt nichts.

Aktivierung erfordert ein separates ADR/User-Approval, `READY_MUTATING`, Gates, echte HITL Confirmation, Exact Allowlist, Atomic Audit Trail und Rubber-Duck-Freigabe.

## P3-Artefakt- und Audit-Modell

P3 nutzt den Lifecycle `transient -> draft -> approved -> persisted -> archived/rejected`.

- `transient`: memory-only, keine Datei.
- `draft`: `projects/{project}/p3/{date}_{sequence}/draft/`, weiterhin untrusted.
- `approved`: `projects/{project}/p3/{date}_{sequence}/approved/`, nur nach Force Gate `APPROVED`.
- `persisted`: finale Ablage nach Approved + Secret/Filesystem/Prompt-Injection Gates.
- `rejected`: abgelehnte/blockierte Artefakte zur Nachvollziehbarkeit.
- `archived`: explizit bestätigte Ablage.

Audit-Logs sind append-only JSONL unter `projects/{project}/p3/{date}_{sequence}/reports/AUDIT.jsonl` und folgen `harness/schemas/audit.schema.json`. Erfasst werden Tool Calls, Gate Decisions, HITL Confirmations, Policy Blocks und Pipeline Runs. Secret-Werte sind verboten; alle Einträge müssen `redacted: true` enthalten.

Mutierende Commands dürfen aus `READY_READONLY` nur Intake, Dry-Run oder Planung starten. Persistenz benötigt `READY_MUTATING`, passende Gates und Confirmation.

## Architektur-Entscheidung: Run-State als Lifecycle-Vertrag

- **Kontext**: P0 hat Trigger-, Runtime- und Policy-Boundaries stabilisiert. Für produktive Commands fehlt ein expliziter Lebenszyklus.
- **Optionen**: Implizite Zustände aus Commands ableiten oder explizites Run-State-Modell als Vertrag definieren.
- **Entscheidung**: Explizites Run-State-Modell in `harness/state_machine.yaml`, gespiegelt in `harness/runtime.yaml`.
- **Begründung**: Gates, Adapter, Validator und spätere Executor-Logik benötigen dieselbe Zustandssemantik.
- **Konsequenzen**: Validator prüft die Modell-Konsistenz; Commands/Pipelines müssen künftig gegen diese States spezifiziert werden.
