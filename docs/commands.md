# commands

## Willkommen und Befehlsübersicht

Startpunkt für neue Nutzer: `docs/welcome.md`. Die lokale Onboarding-Oberfläche ist direkt als `PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color` verfügbar; sie ist no-write und kein nativer Adapter-Trigger.

| Befehl | Kurzbeschreibung |
|---|---|
| `ZEN NEW` | Neues Projektprofil vorbereiten; Persistenz nur nach Mutationsfreigabe. |
| `ZEN MEMORY INIT` | Hot Memory und Projektprofil prüfen oder initialisieren; guarded/mutierend, braucht Gates und Bestätigung. |
| `ZEN NEW BUILD` | Projektagent aus Template spezifizieren/erzeugen. |
| `ZEN STATUS` | Read-only Status über Harness, Gates, Projekte und nächste sichere Aktion. |
| `ZEN PLAN` | Plan read-only entwerfen; Persistenz nur nach Freigabe. |
| `ZEN SNAPSHOT` | Redigierten Session-Handoff vorbereiten; keine Secrets. |
| `ZEN P1` | Direkter Ask-/Klärungsmodus. |
| `ZEN P2` | Prompt Brief für genau einen Ziel-Agenten. |
| `ZEN P3` | Multi-Agent Pipeline mit max. drei Agenten und Force Gate. |
| `ZEN RESET` | Logischer Session-Reset ohne Deletes. |
| `ZEN VALIDATE` | Source-read-only Validierung mit redigierten Reports. |

## Lokales Onboarding

`tools/zen_onboarding.py` zeigt Pi-/Claude-/Local-Sichten, belegte Trigger, lokale Check-Aufrufe und Command-Spezifikationen. Es führt keine Checks automatisch aus und schreibt keine Reports.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --adapter pi --linear --no-color
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --adapter claude --linear --no-color
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --adapter local --linear --no-color
```

Details: `docs/onboarding-ui.md`.

## Operator-Checks

Bevorzugte lokale Entry-Points:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only
just check
just audit-deep
```

Diese Standardpfade nutzen `PYTHONDONTWRITEBYTECODE=1`; die Check-Pfade nutzen `--check-only`, schreiben keine Reports und aktivieren keine Runtime. `audit:deep` ist read-only/stdout-only und prüft Links, generierte Artefakte, Provider-/Credential-Risiken, Tool-Scope und Guardrails.

## ZEN VALIDATE

Source-read-only/non-destructive Qualitätslauf für den Harness. Die lokale Validator Runtime liegt unter `tools/zen_validate.py` und verändert keine Harness-Quellen. Normalmodus: einzige erlaubte Persistenz sind redigierte Reports unter `validation/reports/zen-validate.report.md` und `validation/reports/zen-validate.report.json`. Check-only/no-write: `--check-only` schreibt keine Reports und gibt nur Exit/Console-Status aus. Keine mutierenden Aktionen ausführen, solange ein Gate `FAIL` meldet.

### Lokaler Aufruf

```bash
python3 tools/zen_validate.py
```

Von einem anderen Arbeitsverzeichnis:

```bash
REPO_ROOT=/path/to/00Z
python3 "$REPO_ROOT/tools/zen_validate.py" --root "$REPO_ROOT"
```

Optionen:

```bash
python3 tools/zen_validate.py --help
python3 tools/zen_validate.py --report-md validation/reports/custom.md --report-json validation/reports/custom.json
python3 tools/zen_validate.py --no-json
python3 tools/zen_validate.py --check-only
```

Begriffe:

- `source-read-only`: Harness-Quellen werden gelesen, aber nicht verändert.
- `non-destructive`: keine Deletes, keine Rechteänderungen, kein Git/CI/Deployment, keine Dependency-/Lockfile-Aktionen.
- `report-writing allowed`: Normalmodus darf ausschließlich redigierte Reports unter `validation/reports/` schreiben.
- `check-only/no-write`: `--check-only` schreibt keine Reports und validiert nur mit Exit-Code und Console-Summary.

Hinweis: `--check-only` kann eine andere PASS-Anzahl als der Normalmodus haben, weil Report-Metriken ohne Report-Schreibausgabe entfallen.

Der Validator liest keine echten `.env`-Dateien; `.env.example` ist erlaubt. Reports müssen unter `validation/reports/` liegen. Cache- und Report-Verzeichnisse werden aus Vollscans ausgeschlossen; der Report enthält Runtime-Metriken zu gelesenen Dateien/Bytes und Budget-Schätzungen.

### Gate-Reihenfolge

1. `validation/schema-gate.yaml`
2. `validation/placeholder-gate.yaml`
3. `validation/policy-gate.yaml`
4. `validation/onboarding-gates.yaml`
5. `validation/secret-gates.yaml`
6. `validation/filesystem-gates.yaml`
7. `validation/prompt-injection-gates.yaml`
8. `validation/adapter-gate.yaml`
9. `validation/pipeline-gate.yaml`
10. `validation/performance-gate.yaml`

### Performance-Gate

Prüft Boot-/P3-Tokenbudget, Cold-Memory-Load, Cache-Fähigkeit großer Dateien, dynamisches Reasoning ohne Chain-of-Thought-Offenlegung, P3-Registry-Alignment und Legacy-Alias-Freiheit.

Aktueller Stand: Performance-Ergebnisse sind im `ZEN VALIDATE` Report als Check `performance_budget` integriert. Der Pfad `validation/reports/performance-gate.report.md` ist als späterer dedizierter Einzelreport reserviert. Temporäre Cache-/Arbeitskopien dürfen unter `harness/.cache/` liegen, gelten aber nicht als Source of Truth.

Status:

- `PASS`: alle kritischen Checks bestanden, keine Warnungen.
- `WARN`: kritische Checks bestanden, mindestens eine Budget-/Cache-Warnung.
- `FAIL`: mindestens ein kritischer Check fehlgeschlagen; mutierende Aktionen blockieren.

## Command-Statusmodell

- `scaffold`: Platzhalter-/Grundstruktur, fachlich nicht vollständig.
- `draft`: fachlich beschrieben, aber noch nicht als Runtime geprüft.
- `ready`: spezifiziert und bereit zur Implementierung/Integration.
- `implemented`: Runtime oder Adapterverhalten ist vorhanden und lokal validierbar.
- `active`/`stable`/`deprecated`: Legacy-kompatible Statuswerte für bestehende Schemas und ältere Artefakte.

`zen-validate` ist `implemented`, weil `tools/zen_validate.py` als lokale Runtime vorhanden ist. Adapter-Felder `runtime_implemented: true` beziehen sich auf diese lokale Validator Runtime; `native_runtime_implemented: false` bedeutet Roadmap: keine native Pi-/Claude-Extension ist Teil dieses Harness-Scaffolds.

## Executor Dry-Run Preview

`tools/zen_execute.py` ist die minimale Executor-Preview-Runtime. Sie führt keine Mutationen aus, schreibt keine Projektartefakte und erzeugt keine echten P3-Run-Verzeichnisse. Der Default ist Dry-Run mit Audit-Preview auf stdout. Optional darf `--write-report` ausschließlich redigierte Preview-Reports unter `validation/reports/*.preview.json` schreiben.

Beispiel:

```bash
python3 tools/zen_execute.py --command "ZEN STATUS"
python3 tools/zen_execute.py --pipeline p3
python3 tools/zen_execute.py --command "ZEN P3" --preview-hitl
python3 tools/zen_execute.py --command "ZEN P3" --preview-hitl --write-hitl-preview
python3 tools/zen_execute.py --command "ZEN STATUS" --simulate-audit-append
python3 tools/zen_execute.py --command "ZEN STATUS" --write-report
python3 tools/zen_execute.py --command "ZEN P3" --write-confirmation-report
python3 tools/zen_execute.py --command "ZEN STATUS" --append-audit-preview
python3 tools/zen_execute.py --pipeline p3 --write-run-manifest-preview
python3 tools/zen_execute.py --explain-project-write-boundary
python3 tools/zen_execute.py --attempt-project-write
```

`--attempt-project-write` muss blockieren; produktive Projektwrites sind deaktiviert.

## Negative Test Runner

`tools/zen_test_negative.py` führt alle Fixtures unter `validation/fixtures/negative/` dependency-frei über `tools/zen_execute.py --simulate-negative <case>` aus. Der Runner erwartet je Case Exit-Code `2`, `BLOCKED`, `writes_performed: []` und `project_writes_performed: []`.

```bash
python3 tools/zen_test_negative.py --check-only
python3 tools/zen_test_negative.py
```

Normalmodus schreibt ausschließlich redigierte Reports unter `validation/reports/zen-negative-tests.report.md` und `validation/reports/zen-negative-tests.report.json`. `--check-only` schreibt nichts.

## Test-All Orchestrator

`tools/zen_test_all.py` bündelt lokale nicht-destruktive Checks: `tools/zen_validate.py --check-only`, `tools/zen_test_negative.py --check-only`, `ZEN STATUS` Dry-Run, Write-Boundary-Erklärung und einen erwarteten BLOCKED-Versuch via `--attempt-project-write`.

```bash
python3 tools/zen_test_all.py --check-only
python3 tools/zen_test_all.py
```

Normalmodus schreibt ausschließlich redigierte Reports unter `validation/reports/zen-test-all.report.md` und `validation/reports/zen-test-all.report.json`. `--check-only` schreibt nichts.

## Deep Audit

`tools/zen_audit_deep.py` ist ein zusätzlicher read-only Audit für professionelle Vorabprüfungen. Er schreibt keine Reports und startet keine Runtime.

```bash
python3 tools/zen_audit_deep.py
python3 tools/zen_audit_deep.py --strict-artifacts
just audit-deep
```

`--strict-artifacts` stuft generierte Artefakte wie Python-Cache-Verzeichnisse als Fehler ein. Ohne diese Option werden sie als Warnung ausgegeben, damit Cleanup separat freigegeben werden kann.

## Review Result Validation

`tools/zen_review_validate.py` validiert 00Z Reviewer-Result-JSONs und Review-Fixtures. Es startet keine Reviewer-Agenten, keine Chain und keine Runtime.

```bash
python3 tools/zen_review_validate.py --check-only
just review-validate
```

Details: `docs/review-artifacts.md`.

## Adapter Smoke

`tools/zen_adapter_smoke.py` prüft Pi-/Claude-Adapter read-only: Entry Points, Security-/Response-Contracts, `runtime_implemented: true`, `native_runtime_implemented: false`, no-CoT/no-env/no-project-write und Readiness-Verweise.

```bash
python3 tools/zen_adapter_smoke.py --check-only
python3 tools/zen_adapter_smoke.py
```

Normalmodus schreibt ausschließlich redigierte Reports unter `validation/reports/zen-adapter-smoke.report.md` und `validation/reports/zen-adapter-smoke.report.json`.

## P4 Productive Write Boundary

P4 aktiviert keine produktiven Writes. Es definiert nur die spätere Boundary:

- echte Projektwrites bleiben `BLOCKED`, bis User-Freigabe, `READY_MUTATING`, alle Mutations-Gates, HITL Confirmation, Rubber-Duck-Freigabe und Audit Trail vorliegen.
- echte Confirmation nutzt `harness/schemas/real-confirmation.schema.json` und ist nicht identisch mit Boundary-Test-/Preview-Reports.
- erste erlaubte produktive Pfade sind als disabled-by-default Exact-Allowlist in `harness/schemas/project-write-allowlist.schema.json` beschrieben.
- echtes `projects/{project}/p3/{run}/reports/AUDIT.jsonl` ist nur als disabled-by-default Atomic-Append-Design in `harness/schemas/atomic-audit-append.schema.json` beschrieben.
- `tools/zen_execute.py --attempt-project-write` schreibt nichts und gibt `BLOCKED` zurück.

## Mutierende Commands und READY_READONLY

Mutierende Commands (`ZEN NEW`, `ZEN MEMORY INIT`, `ZEN NEW BUILD`, persistierendes `ZEN PLAN`, `ZEN SNAPSHOT`) dürfen aus `READY_READONLY` nur Intake, Dry-Run oder Planung erzeugen. Jede Datei-Persistenz benötigt:

1. `READY_MUTATING`
2. passende Gates: Policy, Filesystem, Secret, Prompt-Injection und ggf. Onboarding
3. explizite Confirmation, sofern der Command schreibt oder Risiko `high|critical` erreicht
4. Audit-Ereignis bei P3-/Pipeline-Kontext

P3-Artefakte folgen `transient -> draft -> approved -> persisted -> archived/rejected`; siehe `docs/pipelines.md`.
