# Validation Reports

Dieses Verzeichnis enthält bewusst persistierte, redigierte Validator-Reports.

## Kanonische Reports

- `zen-validate.report.md` / `zen-validate.report.json` — Standardausgabe von `tools/zen_validate.py`.
- `performance-gate.report.md` — reservierter Reportpfad für ein späteres dediziertes Performance Gate; aktuell ist Performance als `performance_budget` in `zen-validate.report.*` integriert.

## Test-/Custom-Reports

Dateien wie `test-custom.report.*`, `test-no-json.report.md` oder `final-phase*.report.*` sind bewusst dokumentierte Referenz-/Smoke-Test-Artefakte. Sie dürfen zur Nachvollziehbarkeit im Verzeichnis bleiben, werden aber nicht als aktuelle Source of Truth behandelt.

## Sicherheitsregeln

- Normalmodus darf Reports schreiben; `python3 tools/zen_validate.py --check-only` ist no-write und aktualisiert dieses Verzeichnis nicht.
- `tools/zen_execute.py --write-report` darf ausschließlich redigierte Preview-Reports mit Suffix `.preview.json` in diesem Verzeichnis schreiben; Default bleibt no-write.
- `tools/zen_execute.py --write-hitl-preview` darf ausschließlich redigierte HITL-Preview-Reports mit Suffix `.hitl-preview.json` schreiben; diese enthalten `decision: preview_only` und `effective_confirmation: false`.
- P3 Controlled Write Boundary Tests dürfen ausschließlich `.confirmation.json`, `.audit-preview.jsonl` und `.run-manifest.preview.json` in diesem Verzeichnis schreiben; sie sind keine Projektfreigaben und erzeugen keine `projects/*/p3` Verzeichnisse. `effective_confirmation: true` in `.confirmation.json` ist nur Boundary-Test-Semantik und wird durch `not_project_authorization: true` sowie `production_scope: false` begrenzt.
- Reports müssen redigiert sein und dürfen keine Secret-Werte enthalten.
- Echte `.env*`-Dateien werden durch den Validator nicht gelesen.
- Temporäre Cache-Artefakte gehören nach `harness/.cache/`; kanonische Reports bleiben unter `validation/reports/`.
