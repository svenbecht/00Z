# ADR: Productive Project Write Boundary

## Status

Design-only / disabled. Keine produktiven Projektwrites sind durch dieses ADR aktiviert.

## Kontext

P0–P3 haben Trigger-Sync, Run-State, Command-Spezifikationen, P3-Artefaktmodell, Audit-Preview und kontrollierte Report-Zone unter `validation/reports/` etabliert. Der nächste Schritt ist das Design einer produktiven Write-Boundary für spätere P3-Projektartefakte unter `projects/{project}/p3/{run}/...`.

## Entscheidung

Produktive Projektwrites bleiben deaktiviert, bis alle folgenden Bedingungen erfüllt und in einer separaten Freigabe bestätigt sind:

1. `READY_MUTATING`
2. `onboarding_gate`, `policy_gate`, `filesystem_gate`, `secret_gate`, `prompt_injection_gate`
3. P3 `force_gate_APPROVED`, falls P3-Artefakte persistiert werden
4. echte HITL Confirmation gemäß `harness/schemas/real-confirmation.schema.json`
5. Exact Allowlist für konkrete Zielpfade gemäß `harness/schemas/project-write-allowlist.schema.json`
6. append-only Audit Trail gemäß `harness/schemas/atomic-audit-append.schema.json`
7. Rubber-Duck-Freigabe und explizite User-Freigabe

## Nicht-Ziele

- Keine Aktivierung produktiver Projektwrites in dieser Phase.
- Keine Erstellung von `projects/*/p3` Run-Verzeichnissen.
- Keine echten `AUDIT.jsonl` Appends unter `projects/`.
- Keine Nutzung von Boundary-Test-Confirmation-Reports als produktive Freigabe.

## Exact Allowlist Design

Erste produktive P3-Pfade dürfen nur exakt aus einem geprüften Run-Kontext abgeleitet werden:

- `projects/{project}/p3/{run}/draft/BRIEF.md`
- `projects/{project}/p3/{run}/draft/TASKLIST.md`
- `projects/{project}/p3/{run}/draft/results/*.md`
- `projects/{project}/p3/{run}/reports/gates/*.md`
- `projects/{project}/p3/{run}/reports/AUDIT.jsonl`
- `projects/{project}/p3/{run}/approved/FINAL.md`
- `projects/{project}/state.md`

Platzhalter müssen vor Write durch konkrete, validierte Werte ersetzt sein. Globale Wildcards sind für produktive Writes nicht ausreichend.

## Atomic Audit Append Design

Echte Audit-Appends müssen atomar, append-only und redigiert sein:

1. Event gegen `harness/schemas/audit.schema.json` validieren.
2. Secret-Scan vor Append.
3. Zielpfad exakt allowlisted.
4. Bestehende Datei nur append-only erweitern; kein Rewrite vorhandener Events.
5. Jeder Event enthält `redacted: true` und keine Secret-Werte.
6. Append-Operation ist an dieselbe HITL Confirmation und denselben `run_id` gebunden.

## Konsequenzen

- `tools/zen_execute.py --attempt-project-write` muss `BLOCKED` ausgeben und darf nichts schreiben.
- `--explain-project-write-boundary` darf nur erklären, nicht schreiben.
- Validator prüft, dass produktive Write-Boundary deaktiviert bleibt.
