# DevOps — 00Z

## Lokale Validierung

Das Harness bleibt lokal-first. `ZEN VALIDATE` wird lokal durch `tools/zen_validate.py` ausgeführt. Normalmodus ist source-read-only/non-destructive und schreibt ausschließlich redigierte Reports:

```bash
python3 tools/zen_validate.py
```

Check-only/no-write garantiert, dass keine Reports geschrieben werden:

```bash
python3 tools/zen_validate.py --check-only
```

Begriffe: `source-read-only` verändert keine Harness-Quellen; `non-destructive` führt keine Deletes, Rechteänderungen, Git-/CI-/Deployment- oder Dependency-/Lockfile-Aktionen aus; `report-writing allowed` gilt nur für redigierte Reports unter `validation/reports/`; `check-only/no-write` schreibt nichts. `--check-only` kann eine andere PASS-Anzahl als der Normalmodus haben, weil Report-Metriken ohne Report-Schreibausgabe entfallen.

Schreibausgaben im Normalmodus sind ausschließlich die redigierten Reports unter `validation/reports/`:

- `zen-validate.report.md`
- `zen-validate.report.json`

Negative Fixture Tests laufen dependency-frei über `tools/zen_test_negative.py`:

```bash
python3 tools/zen_test_negative.py --check-only
python3 tools/zen_test_negative.py
```

Der Normalmodus schreibt ausschließlich:

- `zen-negative-tests.report.md`
- `zen-negative-tests.report.json`

Lokale Gesamtchecks laufen über `tools/zen_test_all.py`:

```bash
python3 tools/zen_test_all.py --check-only
python3 tools/zen_test_all.py
```

Der Normalmodus schreibt ausschließlich:

- `zen-test-all.report.md`
- `zen-test-all.report.json`

Adapter-Smoke läuft über `tools/zen_adapter_smoke.py`:

```bash
python3 tools/zen_adapter_smoke.py --check-only
python3 tools/zen_adapter_smoke.py
```

Der Normalmodus schreibt ausschließlich:

- `zen-adapter-smoke.report.md`
- `zen-adapter-smoke.report.json`

Readiness-Kriterien sind in `docs/readiness.md` dokumentiert.

Release-Snapshot läuft über `tools/zen_release_snapshot.py`:

```bash
python3 tools/zen_release_snapshot.py --check-only
python3 tools/zen_release_snapshot.py
```

Der Normalmodus schreibt ausschließlich:

- `release-status.snapshot.md`
- `release-status.snapshot.json`

Die versionierte Status-Matrix steht in `docs/release-status.md` und `docs/status-matrix.md`.

Echte `.env`-Dateien werden nicht gelesen. Für reine Markdown-Ausgabe: `python3 tools/zen_validate.py --no-json`.

Performance-Regeln der Validator Runtime:

- Cache-/Report-Verzeichnisse werden bei Scans ausgeschlossen: `.pi/cache`, `.claude/cache`, `harness/.cache`, `validation/reports`.
- Textscans beschränken sich auf relevante Suffixe (`.md`, `.yaml`, `.yml`, `.json`, `.py`, `.txt`).
- Standard-Limit pro Textscan-Datei: 256 KiB; Syntax-Scan-Limit: 512 KiB.
- Report enthält Runtime-Metriken: gelesene Dateien, gelesene Bytes, übersprungene große/nicht-textuelle/ausgeschlossene Dateien.
- Tokenbudgets werden grob über `words * 1.3` geschätzt.

Vor mutierenden Änderungen sollen Gates in dieser Reihenfolge geprüft werden:

1. YAML/JSON-Syntax
2. Schema Gate gegen `harness/schemas/*.schema.json`
3. Placeholder Gate
4. Policy Gate
5. Onboarding Gate
6. Secret Gate
7. Filesystem Gate
8. Prompt-Injection Gate
9. Adapter Gate
10. Pipeline Gate
11. Performance Gate

Performance-Gate-Status: Der aktuelle Validator integriert Performance-Ergebnisse im `ZEN VALIDATE` Report als Check `performance_budget`. `validation/reports/performance-gate.report.md` ist als späterer dedizierter Einzelreport reserviert. `harness/.cache/` ist nur für temporäre Cache-/Arbeitsartefakte vorgesehen.

## Schema Gate

Schemas unter `harness/schemas/` definieren Mindestverträge für zentrale Konfigurationen:

| Schema | Ziel |
|---|---|
| `manifest.schema.json` | Root-Harness-Konfiguration |
| `command.schema.json` | `harness/commands/*.yaml` |
| `pipeline.schema.json` | `harness/pipelines/*.yaml` |
| `agent.schema.json` | Agent-Frontmatter |
| `skill.schema.json` | Skill-Frontmatter |
| `memory.schema.json` | Memory-Frontmatter |
| `policy.schema.json` | `harness/policies/*.yaml` |
| `adapter.schema.json` | `adapters/*/adapter.yaml` |
| `runtime.schema.json` | `harness/runtime.yaml` |
| `reasoning-routing.schema.json` | `harness/reasoning/reasoning_routing.yaml` |
| `agent-registry.schema.json` | `agents/agent_registry.yaml` |
| `validation-report.schema.json` | JSON-Reports aus `tools/zen_validate.py` |

## CI/CD-Advisory optional/future

Keine Pipeline-Artefakte ohne explizite Freigabe erstellen. Später sinnvoll:

- Schema Validation
- Secret Scan
- Link Check
- Adapter Consistency Check
- P3 Smoke Test

Bestehende lokale Runtime: `tools/zen_validate.py`. CI/CD darf diese später mit `--report-json` nutzen, aber Pipeline-Artefakte werden nur nach expliziter Freigabe erstellt. Adapter-Konfiguration: `runtime_implemented: true` bedeutet lokale Validator Runtime vorhanden; `native_runtime_implemented: false` bedeutet native Pi-/Claude-Runtime/Extension bleibt Roadmap.

## Multi-Architektur-Kompatibilität

- Zen Core: zentrale Policies und Schemas wiederverwendbar halten.
- Zen Mini: Markdown-Templates kompatibel halten.
- Zeni Pi: Adapter- und Extension-Pfade explizit prüfen.
