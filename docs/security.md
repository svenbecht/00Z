# Security

## Gate-Ausführungsmodell

`ZEN VALIDATE` ist der operative Security-Check für das Harness. Der Ablauf ist deklarativ: Die Dateien unter `validation/` beschreiben Inputs, Checks, Fail Conditions, Severity und erwartete Reports. Die lokale Runtime `tools/zen_validate.py` führt diese Checks source-read-only/non-destructive aus. Normalmodus darf ausschließlich redigierte Reports unter `validation/reports/` schreiben; `--check-only` ist no-write und gibt nur Exit/Console-Status aus.

Reihenfolge:

1. Schema Gate — YAML/JSON und Schema-Referenzen
2. Placeholder Gate — keine Runtime-Platzhalter außerhalb Template-Zonen
3. Policy Gate — Policy-Vollständigkeit und Cross-File-Konsistenz
4. Onboarding Gate — Guide-/Readiness-Pflicht
5. Secret Gate — `.env*`, Token-Patterns, Redaction
6. Filesystem Gate — Workspace-Sandbox und Protected Paths
7. Prompt-Injection Gate — Trust-Zonen und Handoff-Vertrag
8. Adapter Gate — Pi/Claude Boot, Trigger, Security-Hardrules
9. Pipeline Gate — P1/P2/P3, Force-Gate, P3-Agenten in Registry
10. Performance Gate — Boot-/P3-Budget, Cache-Fähigkeit, no-CoT, Registry-/Alias-Konsistenz

Statuswerte: `PASS`, `WARN`, `FAIL`. `FAIL` bedeutet `BLOCKED` für produktive Nutzung und mutierende Tools.

## Validator-Sicherheitsmodell

Die Runtime `tools/zen_validate.py` arbeitet ohne destruktive Aktionen. Sie darf Source-Dateien lesen, verändert keine Harness-Quellen, überspringt echte `.env*`-Dateien außer `.env.example`, blockiert Symlink-/Pfad-Escapes durch Root-Sandboxing und schreibt im Normalmodus nur redigierte Markdown-/JSON-Reports unter `validation/reports/`. Die Policy-Boundary erlaubt dafür explizit `tools/**/*.py`, `harness/**/*.json` und kontrollierte Validator-Reports; `validation/*.yaml` bleibt geschützt. `--check-only` validiert ohne Schreibausgabe und kann wegen entfallender Report-Metriken eine andere PASS-Anzahl als der Normalmodus haben. Traversal, falsche Report-Suffixe und Symlink-Reports werden blockiert. Reports dürfen keine Secret-Werte oder Inhalte geschützter Dateien enthalten; Secret-Funde werden redacted und nur mit Pattern-Namen referenziert.

Performance-Gate-Ergebnisse sind aktuell in `zen-validate.report.*` integriert (`performance_budget`). Der dedizierte Pfad `validation/reports/performance-gate.report.md` ist für einen späteren Einzelreport reserviert; `harness/.cache/` ist nur für temporäre Cache-Artefakte vorgesehen.
