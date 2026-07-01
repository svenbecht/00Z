# Readiness — 00Z

## Status

P8 Readiness ist lokal-first und nicht-destruktiv. Dieses Dokument aktiviert keine produktiven Projektwrites und keine native Pi-/Claude-Runtime.

## Lokale PASS-Kriterien

Vor jeder Freigabe müssen diese Befehle im Harness-Root PASS liefern. Für no-cache/no-write Checks sollte `PYTHONDONTWRITEBYTECODE=1` gesetzt werden:

```bash
just check
just audit-deep
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_negative.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_all.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_adapter_smoke.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_review_validate.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_audit_deep.py
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_release_snapshot.py --check-only
```

Optional dürfen Normalmodi redigierte Reports ausschließlich unter `validation/reports/` schreiben:

```bash
python3 tools/zen_validate.py
python3 tools/zen_test_negative.py
python3 tools/zen_test_all.py
python3 tools/zen_adapter_smoke.py
python3 tools/zen_release_snapshot.py
```

## Adapter-Hardening

Pi und Claude müssen dieselben Sicherheitsgrenzen einhalten:

- `BLOCKED:` für blockierte Aktionen
- `WARN:` für nicht-blockierende Risiken
- `PASS:` für bestandene lokale Checks
- no-CoT: keine Chain-of-Thought-Offenlegung; nur Entscheidung, Evidenz, Annahmen, Risiken, Validierung, HITL-Punkt
- no-env: keine echten `.env` lesen/schreiben; `.env.example` bleibt die einzige erlaubte Vorlage
- no-project-write: keine produktiven Projektwrites, keine echten `projects/*/p3` Run-Verzeichnisse
- mutierende Aktionen bleiben bis `READY_MUTATING`, Gates, HITL und Audit Trail blockiert
- `runtime_implemented: true` bedeutet lokale Tools vorhanden; `native_runtime_implemented: false` muss bestehen bleiben

## Runtime-Contracts

Lokale Runtime-Tools:

| Tool | Modus | Erlaubte Schreibausgabe |
|---|---|---|
| `tools/zen_onboarding.py` | read-only/stdout-only | keine |
| `tools/zen_validate.py` | source-read-only/non-destructive | `validation/reports/zen-validate.report.md/json` |
| `tools/zen_test_negative.py` | negative simulation | `validation/reports/zen-negative-tests.report.md/json` |
| `tools/zen_test_all.py` | lokaler Orchestrator | `validation/reports/zen-test-all.report.md/json` |
| `tools/zen_adapter_smoke.py` | Adapter-Smoke | `validation/reports/zen-adapter-smoke.report.md/json` |
| `tools/zen_review_validate.py` | Review-Result-Validation | keine Default-Schreibausgabe |
| `tools/zen_audit_deep.py` | Deep Read-only Audit | keine |
| `tools/zen_release_snapshot.py` | Release-Snapshot | `validation/reports/release-status.snapshot.md/json` |

`docs/release-status.md` und `docs/status-matrix.md` dokumentieren die versionierte Status-Matrix. Das Betreiber-/Handoff-Dokument steht in `docs/operator-handoff.md`.

`--check-only` schreibt nie Reports.

## Manuelle Freigabegrenzen

`READY_MUTATING` und produktive Writes dürfen nicht aus diesen lokalen Checks abgeleitet werden. Eine spätere Aktivierung braucht separate ADR/User-Freigabe, P4 Write-Boundary, echte Confirmation und Audit Trail.
