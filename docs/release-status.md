# Release Status / Status Matrix — 00Z

## Snapshot

- Version: P9 local release snapshot
- Modus: lokal-first, nicht-destruktiv
- Produktive Writes: disabled
- Native Pi-/Claude-Runtime: nicht aktiviert
- Source of Truth für Readiness: `docs/readiness.md`

## P0–P9 Status

| Phase | Status | Evidenz |
|---|---|---|
| P0 Scaffold | PASS | Core/Harness-Struktur vorhanden |
| P1 Schema/Gates | PASS | `tools/zen_validate.py --check-only` |
| P2 Run-State/Commands | PASS | `run_state_model`, `command_specs` |
| P3 Executor Preview | PASS | `executor_runtime`, dry-run/no project writes |
| P4 Productive Write Boundary | PASS | `productive_write_boundary_disabled`, P4 ADR |
| P5 Negative Fixtures | PASS | `negative_fixture_coverage` |
| P6 Negative Test Runner | PASS | `negative_test_runner` |
| P7 Test-All Orchestrator | PASS | `test_all_runner` |
| P8 Readiness/Adapter Hardening | PASS | `readiness_checklist`, `adapter_smoke_runner` |
| P9 Release Snapshot | PASS | `release_status_snapshot`, `tools/zen_release_snapshot.py --check-only` |

## Lokale PASS-Kommandos

```bash
python3 tools/zen_validate.py --check-only
python3 tools/zen_test_negative.py --check-only
python3 tools/zen_test_all.py --check-only
python3 tools/zen_adapter_smoke.py --check-only
python3 tools/zen_release_snapshot.py --check-only
```

Optionale Normalmodi schreiben ausschließlich redigierte Reports unter `validation/reports/`.

## Kanonische Report-Pfade

Wenn Normalmodi lokal ausgeführt werden, dürfen ausschließlich diese redigierten Report-Pfade unter `validation/reports/` entstehen:

- `validation/reports/zen-validate.report.md/json`
- `validation/reports/zen-negative-tests.report.md/json`
- `validation/reports/zen-test-all.report.md/json`
- `validation/reports/zen-adapter-smoke.report.md/json`
- `validation/reports/release-status.snapshot.md/json`

## Sicherheitsgrenzen

- no-CoT: keine Chain-of-Thought-Offenlegung
- no-env: keine echte `.env` lesen/schreiben; `.env.example` ist erlaubt
- no-project-write: produktive Projektwrites disabled
- keine echten `projects/*/p3` Run-Verzeichnisse
- keine destruktiven Befehle, kein Git/CI/Deployment, keine Dependency-/Lockfile-Aktionen
- Reports nur sandboxed unter `validation/reports/`

## Nicht-Ziele

- Keine Aktivierung von `READY_MUTATING`
- Keine native Pi-/Claude-Runtime-Aktivierung
- Keine produktiven P3-Artefakte
- Keine echten `AUDIT.jsonl` Appends unter `projects/`
- Keine CI/CD-Integration

## Follow-up Focus

- experimentelle Positionierung konsistent halten
- lokale non-destructive Checks grün halten
- produktive Writes und native Runtime deaktiviert halten

## Voraussetzungen für spätere Mutationsphasen

Eine spätere Mutationsphase braucht separat:

1. explizite User-/ADR-Freigabe
2. `READY_MUTATING`
3. bestandene Gates: onboarding, policy, filesystem, secret, prompt-injection, adapter
4. echte HITL Confirmation gemäß `harness/schemas/real-confirmation.schema.json`
5. exact Project Write Allowlist gemäß `harness/schemas/project-write-allowlist.schema.json`
6. atomarer, append-only Audit Trail gemäß `harness/schemas/atomic-audit-append.schema.json`
7. Rubber-Duck-/Force-Gate-Freigabe für P3-Persistenz
