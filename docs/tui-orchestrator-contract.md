# 00Z TUI Orchestrator Contract

Status: `contract-first`
Keine UI-Implementation, keine Runtime-Aktivierung.

## Zweck

Dieses Dokument definiert, welche Informationen ein späterer TUI-Orchestrator für Pi und Claude anzeigen darf und welche Aktionen blockiert bleiben. Ziel ist präzise Operator-Kommunikation ohne Kontext- oder UI-Noise.

## Sichtbare Zustände

Ein TUI darf anzeigen:

- aktueller Harness-Root,
- Readiness: `unknown | pass | warn | fail`,
- Run-State: `IDLE | READY_READONLY | READY_MUTATING | RUNNING | BLOCKED | DONE | FAILED`,
- aktive Pipeline: `none | P1 | P2 | P3`,
- Gate-Status pro Gate,
- letzter Check-only-Befehl und Exitstatus,
- Brief `Handoff Status`,
- Reviewer-Verfügbarkeit und Reviewer-Validation-Status,
- Tool-Scope: read-only vs. mutating,
- Trust-Zonen: trusted constraints vs. untrusted context.

## Brief Preview

Ein TUI muss Briefs nach dem Brief Contract v2 anzeigen:

- Ziel,
- Nicht-Ziele,
- Scope,
- Trusted Constraints,
- Untrusted Context,
- Files Read,
- Files To Modify,
- Forbidden Paths,
- Allowed Tools,
- Validation Commands,
- Reviewer Requirements,
- Rollback Plan,
- Handoff Status.

Trusted Constraints und Untrusted Context müssen visuell getrennt bleiben.

## Reviewer-Anzeige

Ein TUI darf Reviewer-Ergebnisse anzeigen, wenn sie `tools/zen_review_validate.py --check-only` bestehen.

Anzuzeigen:

- Reviewer-Domain,
- Verdict,
- Finding Counts nach Severity,
- Critical Findings mit `blockingReason`,
- Evidence und Recommendation,
- Fingerprint.

Nicht anzeigen:

- interne Gedankengänge,
- private Scratchpads,
- vollständige Prompts,
- Secrets oder redigierte Inhalte im Klartext.

## Confirmation-Regeln

Ein TUI darf keine riskante Aktion direkt ausführen. Bei High-/Critical-Risk darf es nur eine Confirmation-Anfrage vorbereiten.

Immer blockiert ohne separate Freigabe:

- produktive Writes,
- P3-Persistenz,
- echte Audit-Appends,
- Git add/commit/push,
- Dependency-Installation,
- Docker/VM/Runtime-Aktivierung,
- Netzwerkzugriff,
- `.env*`-Zugriffe,
- Policy-/Security-/Validation-Schema-Änderungen.

## Adapter-Gleichbehandlung

Pi und Claude müssen denselben Contract sehen:

- keine native Runtime-Behauptung,
- no-CoT,
- validation-first,
- read-only default,
- mutating nur nach Gates und HITL,
- Brief v2 als Übergabeformat.

## Akzeptanzkriterium

Eine spätere TUI-Implementation darf erst beginnen, wenn:

1. `just check` grün ist,
2. der lokale Validator- und Smoke-Pfad grün ist,
3. Brief Contract v2 stabil ist,
4. Review-Result-Validation grün ist,
5. keine produktive Runtime-Aktivierung impliziert wird.
