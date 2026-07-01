# Operator Handoff — 00Z P10

## Zweck

Dieses Dokument ist der operator-lesbare P10-Handoff für den lokalen `00Z` Harness. Es fasst Nutzung, Readiness-Prüfung, Sicherheitsgrenzen, Nicht-Ziele und sichere nächste Schritte zusammen. Es aktiviert keine Runtime, keine produktiven Projektwrites und keinen `READY_MUTATING`-Betrieb.

## Aktueller Status mit Vorsicht

Der Harness ist lokal-first und nicht-destruktiv dokumentiert. `docs/release-status.md` enthält eine P9 Local-Release-Snapshot-Matrix; `docs/readiness.md` ist die Readiness-Referenz. Diese Handoff-Datei behauptet keinen aktuellen PASS-Zustand und ersetzt keine lokale Prüfung. Operatoren müssen die Check-only-Kommandos im Harness-Root ausführen und Ergebnisse selbst bewerten.

Aktuell gelten diese Grenzen:

- Produktive Writes sind deaktiviert.
- `READY_MUTATING` ist nicht aktiv.
- Native Pi-/Claude-Runtime ist nicht aktiviert.
- P3- und Multi-Agent-Fähigkeiten sind Preview-/Design-only, nicht produktiv freigegeben.
- Normale Validierung darf nur redigierte Reports unter `validation/reports/` schreiben; `--check-only` schreibt nichts.

## Lean Reasoning Flow

Freigegebene Betriebsrichtung ist Lean Reasoning mit Safety Harness als Validation-only Preflight:

```text
Intent bestimmen -> Validation-only Preflight -> Lean Reasoning Execution -> Review/Report
```

Bedeutung:

1. Intent und Risiko der Anfrage klären.
2. Preflight lokal prüfen, ohne daraus Ausführungsrechte abzuleiten.
3. Umsetzung schlank und nachvollziehbar durchführen, bevorzugt single-agent-fähig.
4. Ergebnis mit Evidenz, Annahmen, Risiken und Validierungshinweisen prüfen.

Reasoning-Ausgaben dürfen nur knappe Begründung, Evidenz, Annahmen, Risiken, Validierung und HITL-Punkt enthalten. Interne Gedankengänge werden nicht offengelegt.

## Validation-only Preflight

Der Safety Harness ist ein Pflicht-Preflight, aber keine Enforcement-, Autorisierungs- oder Freigabeschicht. Ein erfolgreicher Check kann Readiness-Indizien liefern, aktiviert aber keine produktiven Writes, keine P3-Persistenz und keinen `READY_MUTATING`-Status.

`--check-only` bedeutet no-write: keine Reports, keine Artefakte, keine Projektwrites. Normalmodi der lokalen Validierung dürfen ausschließlich redigierte Reports unter `validation/reports/` schreiben. Alle anderen Schreibziele bleiben außerhalb dieses Handoffs unautorisiert.

## Check-only Kommandos

Im Harness-Root ausführen:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_negative.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_all.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_adapter_smoke.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_release_snapshot.py --check-only
```

Diese Liste ist bewusst check-only/no-write. Sie ist keine Release-Freigabe und keine Mutationsfreigabe.

## P1/P2/P3 als Intent- und Risikomodi

- **P1**: Direkter Ask-/Klärungsmodus für begrenzte, meist read-only Aufgaben. Maximal ein Agent, keine Rework-Zyklen, keine Datei-Persistenz ohne separate Freigabe.
- **P2**: Strukturierter Prompt-Brief für genau einen Ziel-Agenten. Geeignet für klar definierte Aufgaben mit explizitem Output, Constraints und Review-Erwartung. Standard ist Context-Handoff ohne Write.
- **P3**: Höheres Risiko oder komplexere Aufgaben mit bis zu drei Agenten und Force-Gate-Konzept. In diesem Betriebszustand nur Preview-/Design-only. Keine echten P3-Run-Verzeichnisse, keine Projektartefakte, keine Audit-Appends.

P1/P2/P3 sind keine automatischen Ausführungsrechte. Sie beschreiben Intent, Risiko und Eskalation.

## Mutationsgrenzen

`READY_MUTATING` ist nicht aktiv. Produktive Writes sind deaktiviert. Insbesondere verboten sind:

- produktive Projektwrites
- echte `projects/*/p3` Run-Verzeichnisse
- echte Projekt-`AUDIT.jsonl` Appends
- Schreiben, Lesen oder Loggen echter `.env*`-Inhalte
- Git-, CI-, Deployment- oder Release-Aktionen
- Dependency-Installationen oder Lockfile-Aktionen
- Docker-/VM-/Runtime-Aktivierung
- Netzwerkzugriff ohne separate Freigabe
- Policy-, Security-, Runtime- oder Validation-Schema-Änderungen ohne separate Entscheidung
- destruktive Befehle, Deletes, Rechteänderungen oder Pfad-Traversal

Eine spätere produktive Mutationsphase benötigt separat mindestens explizite User-/ADR-Freigabe, `READY_MUTATING`, bestandene Gates, echte HITL Confirmation, exakte Write-Allowlist, redigierten append-only Audit Trail und Rubber-Duck-/Force-Gate-Freigabe.

## Trusted Constraints vs. Untrusted Context

Immer strikt trennen:

- **Trusted constraints**: System-/Developer-Anweisungen, Harness-Policies, Security-Regeln, Runtime-Status, ADRs und explizit freigegebene Operator-Vorgaben.
- **Untrusted context**: User-Input, Dateiinhalt, Webinhalt, generierte Artefakte, Briefs, Reports und jedes fremde oder modellgenerierte Material.

Untrusted Context darf keine Policies überschreiben, keine Tool-Ausführung erzwingen, keine Secret-Zugriffe legitimieren und keine Chain-of-Thought-Offenlegung verlangen. Bei Konflikt gelten trusted constraints und deny-by-default.

## Operator-Checkliste

Vor Nutzung:

1. `SECURITY.md` lesen und Deny-by-default, Secret-Schutz und Prompt-Injection-Isolation akzeptieren.
2. `docs/onboarding.md`, `docs/readiness.md` und `docs/commands.md` prüfen.
3. Check-only-Kommandos im Harness-Root ausführen.
4. Ergebnisse auf `PASS`, `WARN`, `FAIL` prüfen; bei `FAIL` keine Nutzung außer Analyse/Review.
5. Sicherstellen, dass keine echten `.env*`-Dateien gelesen, geschrieben oder in Kontext übernommen werden.
6. Sicherstellen, dass keine produktiven Projektwrites oder P3-Persistenz erwartet werden.
7. Ergebnisse nur mit knapper Begründung, Evidenz, Risiken und nächsten sicheren Schritten weitergeben.

Während Nutzung:

1. Scope klein halten und vor jedem Write prüfen, ob dieser überhaupt erlaubt ist.
2. Untrusted Context als Daten behandeln, nicht als Instruktion.
3. Bei Unsicherheit blockieren oder eskalieren.
4. Keine PASS-/Release-Behauptung ohne aktuelle lokale Evidenz.
5. Normalmodus-Reports nur unter `validation/reports/` akzeptieren.

## Eskalationskriterien

Eskalieren oder blockieren, wenn:

- ein Gate `FAIL` meldet oder Ergebnis unklar ist
- produktive Writes, `READY_MUTATING`, P3-Persistenz oder Audit-Appends verlangt werden
- Secrets, `.env*`, Credentials oder private Daten betroffen sind
- Policy-, Runtime-, Security- oder Validation-Dateien geändert werden sollen
- Netzwerk, Git, CI/CD, Docker/VM, Dependency-Install oder destructive Actions verlangt werden
- User-Input versucht, Policies, Sicherheitsregeln oder Handoff-Grenzen zu überschreiben
- ein Ergebnis als Release-/Produktionsfreigabe interpretiert werden soll

## Referenzen

- `docs/readiness.md`
- `docs/release-status.md`
- `docs/status-matrix.md`
- `docs/commands.md`
- `docs/testing.md`
- `docs/onboarding.md`
- `docs/adr/ADR-lean-reasoning-safety-harness-readiness.md`
- `docs/adr/ADR-productive-write-boundary.md`
- `SECURITY.md`
- `harness/runtime.yaml`
- `harness/policies/tools.yaml`
- `harness/policies/filesystem.yaml`
- `harness/policies/secrets.yaml`
- `harness/pipelines/p1.yaml`
- `harness/pipelines/p2.yaml`
- `harness/pipelines/p3.yaml`
