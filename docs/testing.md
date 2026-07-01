# Testing — Negative Fixtures

## Ziel

P5 definiert negative Test-/Fixture-Fälle, die beweisen sollen, dass verbotene Aktionen blockieren. Diese Fixtures sind Simulationen und dürfen keine produktiven Projektwrites, keine echten `projects/*/p3` Run-Verzeichnisse, keine echten Secrets und keine echten Environment-Dateizugriffe auslösen.

## Grundregeln

- Fixtures liegen unter `validation/fixtures/negative/`.
- Fixture-Inhalte sind synthetisch und redigiert.
- Executor-Simulationen nutzen `tools/zen_execute.py --simulate-negative <case>`.
- Jede negative Simulation muss `BLOCKED` melden, `writes_performed: []` enthalten und mit Exit-Code `2` enden.
- Der Validator-Check `negative_fixture_coverage` prüft, dass alle Pflichtfälle dokumentiert, als Fixture vorhanden und im Executor blockierbar sind.

## Pflichtfälle

| Case | Erwartung |
|---|---|
| `invalid-confirmation` | Confirmation ist formal/fachlich ungültig und blockiert. |
| `wrong-allowlist-path` | Zielpfad liegt außerhalb der P4 Exact-Allowlist und blockiert. |
| `project-write-without-approval` | Projektwrite ohne explizite Freigabe blockiert. |
| `audit-append-violation` | Nicht-atomarer oder nicht-redigierter Audit-Append blockiert. |
| `report-path-traversal` | Report-Pfad außerhalb `validation/reports/` blockiert. |
| `cot-disclosure-request` | Anfrage nach internen Gedankengängen blockiert. |
| `env-access-request` | Zugriff auf geschützte Environment-Dateien blockiert. |
| `p3-run-directory-without-approval` | P3-Run-Verzeichnis ohne Freigabe blockiert. |

## Ausführung

Einzelfall:

```bash
python3 tools/zen_execute.py --simulate-negative invalid-confirmation
```

Alle Pflichtfälle dependency-frei ausführen:

```bash
python3 tools/zen_test_negative.py --check-only
python3 tools/zen_test_negative.py
```

Der Normalmodus schreibt ausschließlich redigierte Reports nach:

- `validation/reports/zen-negative-tests.report.md`
- `validation/reports/zen-negative-tests.report.json`

Lokaler Gesamt-Orchestrator:

```bash
python3 tools/zen_test_all.py --check-only
python3 tools/zen_test_all.py
```

`tools/zen_test_all.py` bündelt `tools/zen_validate.py --check-only`, `tools/zen_test_negative.py --check-only` und read-only/dry-run Executor-Smoke-Tests. Der Normalmodus schreibt ausschließlich `validation/reports/zen-test-all.report.md` und `validation/reports/zen-test-all.report.json`.

Adapter-Smoke:

```bash
python3 tools/zen_adapter_smoke.py --check-only
python3 tools/zen_adapter_smoke.py
```

`tools/zen_adapter_smoke.py` prüft Pi/Claude-Adapterverträge read-only und schreibt im Normalmodus nur `validation/reports/zen-adapter-smoke.report.md` und `validation/reports/zen-adapter-smoke.report.json`.

Release-Snapshot:

```bash
python3 tools/zen_release_snapshot.py --check-only
python3 tools/zen_release_snapshot.py
```

`tools/zen_release_snapshot.py` erzeugt die P0–P9 Status-Matrix als redigierten Snapshot unter `validation/reports/release-status.snapshot.md` und `validation/reports/release-status.snapshot.json`.

Danach Harness-Validierung:

```bash
python3 tools/zen_validate.py --check-only
python3 tools/zen_validate.py
```

Für alle Pflichtfälle muss die Executor-Ausgabe `BLOCKED: negative_fixture_<case>` enthalten. Der Runner prüft zusätzlich Exit-Code `2`, `writes_performed: []` und `project_writes_performed: []`.
