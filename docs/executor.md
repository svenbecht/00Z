# Executor Runtime — Dry-Run First

## Ziel

`tools/zen_execute.py` ist die minimale lokale Executor-Preview-Runtime. Sie ist bewusst dry-run-first und schreibt keine Projektartefakte, keine Audit-Logs und keine P3-Run-Verzeichnisse.

## Modi

- Default: `dry-run` / no-write
- Ausgabe: Console/Stdout mit Audit-Preview JSON
- Optional: `--write-report` schreibt ausschließlich redigierte Preview-Reports unter `validation/reports/*.preview.json`
- Optional: `--preview-hitl` erzeugt eine no-write HITL Confirmation Preview mit `decision: preview_only` und `effective_confirmation: false`
- Optional: `--write-hitl-preview` schreibt ausschließlich redigierte HITL-Preview-Reports unter `validation/reports/*.hitl-preview.json`
- Optional: `--simulate-audit-append` simuliert Audit Append; es wird kein Projekt-`AUDIT.jsonl` geschrieben
- Verboten: Projektartefakt-Persistenz, P3-Run-Verzeichnisse, `.env`-Reads, Git/CI/Deployment, Dependency-/Lockfile-Aktionen, Deletes

## Runtime Boundary

| Bereich | Entscheidung |
|---|---|
| Projektartefakte | keine Writes im Dry-Run |
| Audit Writer | Preview auf stdout; optional kontrollierter Preview-Report, kein P3 Audit Append |
| P3 Run Manifest | Schema vorhanden, keine Datei im Dry-Run |
| HITL Confirmation | formal modelliert, keine aktive Freigabe ohne User-Confirmation-ID |

## Audit Preview

Dry-run erzeugt ein Preview-Objekt nach `harness/schemas/audit-preview.schema.json` mit:

- `timestamp`
- `run_id`
- `actor`
- `event_type`
- `target_paths`
- `risk_level`
- `trust_zone`
- `decision`
- `result`
- `redacted: true`

## P3 Run Manifest

Schema: `harness/schemas/run-manifest.schema.json`.

Ein echtes Manifest darf erst geschrieben werden, wenn ein späterer Executor-Write-Boundary implementiert ist und `READY_MUTATING`, Gates und HITL erfüllt sind.

## Controlled Report Mode

`--write-report` darf nur unter `validation/reports/` schreiben. Der Dateiname muss auf `.preview.json` enden, z. B. `validation/reports/zen-execute.preview.json`. Der Modus bleibt dry-run: keine Projektartefakte, keine P3-Run-Verzeichnisse, kein Audit-Append.

## HITL Confirmation Preview

Preview-Schema: `harness/schemas/hitl-preview.schema.json`.
Echte spätere Confirmation-Schema: `harness/schemas/hitl-confirmation.schema.json`.

Format: `hitl_YYYYMMDDTHHMMSSZ_suffix`.

`--preview-hitl` generiert nur eine redigierte Preview und keine echte Freigabe. Pflichtwerte:

- `decision: preview_only`
- `effective_confirmation: false`
- `preview_only: true`
- `redacted: true`

`--write-hitl-preview` darf nur `validation/reports/*.hitl-preview.json` schreiben.

## Productive Project Write Boundary — Disabled

Produktive Projektwrites sind weiterhin deaktiviert. `tools/zen_execute.py --explain-project-write-boundary` erklärt die Anforderungen und schreibt nichts. `--attempt-project-write` gibt `BLOCKED: productive_project_write_boundary_disabled` aus und schreibt nichts.

Design-Artefakte:

- ADR: `docs/adr/ADR-productive-write-boundary.md`
- Echte spätere Confirmation: `harness/schemas/real-confirmation.schema.json`
- Exact Allowlist Design: `harness/schemas/project-write-allowlist.schema.json`
- Atomic Audit Append Design: `harness/schemas/atomic-audit-append.schema.json`

Aktivierung benötigt explizite User-Freigabe, `READY_MUTATING`, Gates, echte HITL Confirmation, Audit Trail und Rubber-Duck-Freigabe.

## Controlled Write Boundary Reports

Alle folgenden Writes bleiben auf `validation/reports/` beschränkt und erzeugen keine Projektartefakte/P3-Run-Verzeichnisse:

- `--write-confirmation-report` -> `*.confirmation.json` mit `effective_confirmation: true`, aber ausschließlich als **Boundary-Test-Artefakt**. Es ist keine produktive Projektfreigabe, weil `not_project_authorization: true` und `production_scope: false` verpflichtend sind.
- `--append-audit-preview` -> `*.audit-preview.jsonl`, append-only Test in der Report-Zone, nicht in `projects/`.
- `--write-run-manifest-preview` -> `*.run-manifest.preview.json`, kein echtes P3 Run Manifest im Projekt.

### Warnung zu Confirmation Reports

`effective_confirmation: true` in `*.confirmation.json` bedeutet nur: Der kontrollierte Report-Boundary-Test hat eine Confirmation-Struktur erzeugt. Es darf daraus keine Projektmutation, kein P3-Run-Verzeichnis und keine produktive Freigabe abgeleitet werden. Produktive Freigaben benötigen später ein separates Schema/ADR ohne `not_project_authorization` und mit expliziter User-Freigabe.

## Audit Append Simulation

`--simulate-audit-append` erzeugt nur ein Preview-Feld `audit_append_simulation` mit `effective_append: false` und `writes_performed: []`. Es wird niemals in `projects/{project}/p3/.../AUDIT.jsonl` geschrieben. `--append-audit-preview` schreibt nur in `validation/reports/*.audit-preview.jsonl` und markiert `not_project_audit: true`.
