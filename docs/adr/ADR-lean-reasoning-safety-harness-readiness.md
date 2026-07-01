# ADR: Lean Reasoning Safety Harness Readiness

## Status

Freigegeben als Architektur-/Readiness-Entscheidung. Keine Aktivierung eines Full Harness, keiner P3-Produktiv-Writes und keiner Multi-Agent-Runtime durch dieses ADR.

## Datum

2026-06-11

## Kontext

00Z benötigt eine belastbare Readiness-Entscheidung für den nächsten Ausbau der Reasoning- und Safety-Pipeline. Die bisherige Richtung zeigt, dass ein vollständiger Harness mit umfassender Runtime-Orchestrierung, Multi-Agent-Enforcement und produktiven Schreibpfaden zum aktuellen Zeitpunkt unverhältnismäßig ist.

Gleichzeitig dürfen Safety-Anforderungen nicht verwässert werden: Validierung muss vor jeder riskanten Ausführung verpflichtend erfolgen, produktive Writes müssen weiterhin blockiert bleiben, und P3/Multi-Agent-Fähigkeiten dürfen nicht als freigegebene Runtime missverstanden werden.

Diese ADR legt daher fest, dass 00Z vorerst auf einen schlanken Reasoning-Flow mit Safety Harness setzt. Der Harness ist nicht als vollwertige Runtime-Enforcement-Schicht zu verstehen, sondern als verpflichtender Validation-only Preflight und als klare Boundary für Intent, Eskalation und spätere Runtime-Erweiterungen.

## Zentrale Befunde

- Ein Full Harness würde aktuell mehr Komplexität erzeugen als Nutzen stiften.
- Die vorhandenen P1/P2/P3-Konzepte sind als schlanke Intent- und Escalation-Modi sinnvoll, dürfen aber keine implizite produktive Ausführungsfreigabe bedeuten.
- Validation-only ist als Pflicht-Preflight ausreichend, wenn produktive Mutationen und P3-Writes blockiert bleiben.
- P3, Multi-Agent und produktive Projektwrites sind noch nicht runtime-sicher, solange echte Enforcement-Mechanismen fehlen.
- Bestehende ADR-Grenzen zu produktiven Writes bleiben gültig und werden durch diese Entscheidung nicht gelockert.

## Entscheidung

00Z nutzt vorerst **Lean Reasoning + Safety Harness** statt eines Full Harness.

Konkret gilt:

1. **Kein Full Harness**
   - Keine Einführung einer umfassenden Runtime-Orchestrierung.
   - Kein zusätzlicher Multi-Agent-Produktionspfad.
   - Keine produktive Write-Freigabe durch dieses ADR.

2. **Lean Reasoning bleibt der Standardpfad**
   - Reasoning bleibt einfach, nachvollziehbar und agentisch handhabbar.
   - Der primäre Flow bleibt single-agent-fähig und vermeidet unnötige Chain-Komplexität.

3. **Safety Harness als Validation-only Pflicht-Preflight**
   - Validierung ist vor relevanten Ausführungen verpflichtend.
   - Der Preflight prüft Readiness, Policy-/Boundary-Erwartungen und bekannte Blocker.
   - Validation-only darf nicht als produktive Freigabe interpretiert werden.

4. **P1/P2/P3 bleiben schlanke Intent-/Escalation-Modi**
   - P1: normale, begrenzte Umsetzung innerhalb klarer Scope-Grenzen.
   - P2: erhöhte Sorgfalt, zusätzliche Validierung und explizitere Review-Erwartung.
   - P3: Preview-/Design-Modus für höhere Risiken, komplexere Artefakte oder spätere Runtime-Fähigkeiten.

5. **P3, Multi-Agent und produktive Writes bleiben Preview/design-only**
   - Keine produktiven P3-Writes.
   - Keine Multi-Agent-Runtime-Freigabe.
   - Keine mutierenden Produktivpfade ohne echte Runtime-Enforcement-Schicht.

## Pipeline-Empfehlung

Empfohlener Standardpfad:

```text
Intent bestimmen -> Validation-only Preflight -> Lean Reasoning Execution -> Review/Report
```

Für einfache Aufgaben reicht ein schlanker Single-Agent-Flow mit anschließender Prüfung. Für P2/P3-Aufgaben wird der Preflight strenger ausgelegt, ohne daraus einen Full Harness abzuleiten.

Nicht empfohlen:

- Full-Harness-Einführung ohne nachgewiesenen Enforcement-Bedarf.
- Multi-Agent-Produktivbetrieb ohne Runtime-Gates.
- Produktive Writes auf Basis von Preview-, Design- oder Validation-only-Ergebnissen.
- Automatische Eskalation von P3 zu produktiver Ausführung.

## Forschungsvalidierung

Die Entscheidung folgt einer pragmatischen Validierungshypothese:

- Lean Reasoning reduziert operative Komplexität und senkt Wartungsrisiken.
- Pflicht-Preflight verbessert Safety, ohne den Entwicklungsfluss durch unnötige Runtime-Orchestrierung zu blockieren.
- Preview/design-only für P3 und Multi-Agent schützt vor Scheinsicherheit, solange Enforcement nur konzeptionell vorliegt.
- Eine spätere Erweiterung zu echtem Runtime-Enforcement bleibt möglich, muss aber separat belegt, implementiert und freigegeben werden.

Die aktuelle Forschungs- und Architekturvalidierung unterstützt daher eine inkrementelle Readiness-Strategie statt eines sofortigen Full Harness.

## Konsequenzen

- 00Z bleibt bewusst schlank und wartbar.
- Safety wird über verpflichtende Validierung, klare Grenzen und Review-Erwartungen hergestellt.
- P1/P2/P3 werden als Modi für Intent, Risiko und Eskalation verstanden, nicht als automatische Ausführungsrechte.
- Produktive Writes bleiben durch bestehende Boundaries blockiert.
- P3- und Multi-Agent-Artefakte dürfen dokumentiert, simuliert oder reviewed werden, aber nicht produktiv mutieren.
- Eine spätere Runtime-Enforcement-Schicht benötigt eine separate ADR und explizite Freigabe.

## Risiken / Blocker

1. **Scheinsicherheit durch Validation-only**
   - Risiko: Der Preflight wird fälschlich als Runtime-Enforcement verstanden.
   - Gegenmaßnahme: Klare Benennung als Validation-only und keine produktive Write-Freigabe.

2. **Scope-Creep in Richtung Full Harness**
   - Risiko: Zusätzliche Gates, Chains oder Agenten erhöhen Komplexität ohne belastbaren Nutzen.
   - Gegenmaßnahme: Full Harness bleibt explizit Nicht-Ziel.

3. **P3-/Multi-Agent-Missverständnis**
   - Risiko: Preview- oder Design-Artefakte werden als produktionsreif interpretiert.
   - Gegenmaßnahme: P3/Multi-Agent bleiben preview/design-only bis echte Runtime-Enforcement existiert.

4. **Fehlende Runtime-Enforcement-Schicht**
   - Blocker für produktive Writes, P3-Produktivbetrieb und Multi-Agent-Runtime.
   - Erforderlich wären mindestens echte Gates, überprüfbare Confirmation, allowlisted Write-Boundaries und append-only Auditability.

5. **Unzureichende Akzeptanzkriterien**
   - Risiko: Validierung bleibt zu allgemein.
   - Gegenmaßnahme: Preflight-Ergebnisse müssen explizit dokumentieren, ob Ausführung erlaubt, blockiert oder nur als Preview zulässig ist.

## Umsetzungsschritte

### P0: Readiness-Basis sichern

- Lean Reasoning als Standardpfad dokumentieren.
- Validation-only Preflight als verpflichtenden Schritt festlegen.
- Bestehende produktive Write-Boundaries unverändert beibehalten.
- P3/Multi-Agent/Produktiv-Writes in Dokumentation und Reports klar als preview/design-only markieren.

### P1: Schlanke Intent-Modi stabilisieren

- P1/P2/P3 als Risiko-, Intent- und Eskalationsmodi konsistent verwenden.
- Preflight-Ausgaben standardisieren: `allowed`, `blocked`, `preview-only` oder äquivalent.
- Review-Erwartungen je Modus dokumentieren.
- Keine zusätzlichen Agenten oder Chains einführen, solange der Use Case single-agent-fähig ist.

### P2: Enforcement-Readiness vorbereiten

- Anforderungen für spätere Runtime-Enforcement-Schicht sammeln.
- Gate-Erwartungen, Confirmation-Modell, Write-Allowlists und Auditability spezifizieren.
- Separaten Architekturentscheid für echte Runtime-Enforcement vorbereiten, falls produktive Writes oder Multi-Agent-Runtime benötigt werden.
- Preview-Artefakte weiter validieren, aber nicht produktiv aktivieren.

## Akzeptanzkriterien

Diese ADR ist erfüllt, wenn:

- eindeutig dokumentiert ist: **Kein Full Harness**.
- eindeutig dokumentiert ist: **Lean Reasoning + Safety Harness** ist die freigegebene Richtung.
- eindeutig dokumentiert ist: **Validation-only ist Pflicht-Preflight**.
- eindeutig dokumentiert ist: **P1/P2/P3 bleiben schlanke Intent-/Escalation-Modi**.
- eindeutig dokumentiert ist: **P3/Multi-Agent/Produktiv-Writes bleiben Preview/design-only bis echte Runtime-Enforcement existiert**.
- keine produktiven Schreibpfade, Multi-Agent-Runtime oder P3-Produktivfunktionen durch diese ADR aktiviert werden.
- Risiken, Blocker, Pipeline-Empfehlung, Forschungsvalidierung und nächste Schritte P0/P1/P2 enthalten sind.

## Finale Empfehlung

00Z soll jetzt keinen Full Harness einführen. Die empfohlene Architektur ist ein schlanker, nachvollziehbarer Lean-Reasoning-Flow mit Safety Harness als verpflichtendem Validation-only Preflight. P1/P2/P3 bleiben nützliche Intent- und Eskalationsmodi, jedoch ohne produktive Runtime-Rechte. P3, Multi-Agent und produktive Writes dürfen erst aktiviert werden, wenn echte Runtime-Enforcement-Mechanismen implementiert, validiert und separat freigegeben sind.
