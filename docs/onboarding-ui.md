# Onboarding UI — 00Z

`tools/zen_onboarding.py` ist eine lokale, dependency-freie Onboarding-Oberfläche für den sicheren First Run. `ZEN ONBOARDING` meint dabei nur diesen lokalen Hilfsaufruf zur read-only Orientierung: kein nativer Pi-/Claude-Adapter-Trigger, keine Runtime-Freigabe und keine echte Pipeline-Ausführung. Angezeigt werden nur Befehle, Trigger und lokal bekannte Aufrufe, die aus vorhandenen Artefakten wie `adapters/*/adapter.yaml`, `harness/commands/*.yaml` und `tools/*.py` belegbar sind.

## Sicherheitsmodell

- stdlib-only, keine Installation nötig
- no-write: keine Reports, keine Projektartefakte, keine Caches
- keine echten `.env*` lesen; vorhandene echte Root-Level-`.env*` werden nur gezählt und als `BLOCKED` markiert
- keine Git-, Docker-, Install-, Browser-, CI/CD- oder Deployment-Aktionen
- keine Secrets ausgeben
- Ausgabe ist standardmäßig no-color; `--linear --no-color` ist für Screenreader, Logs und einfache Terminals gedacht

## Lokaler Start

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
```

Adapter-Sicht wählen:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --adapter pi --linear --no-color
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --adapter claude --linear --no-color
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --adapter local --linear --no-color
```

## Statusmodell der Oberfläche

Lokale Prüfpräfixe:

- `PASS`: Artefakt oder Sicherheitsbedingung ist lokal belegbar.
- `UNKNOWN`: Artefakt fehlt oder kann nicht eindeutig belegt werden; vor Mutationen klären.
- `BLOCKED`: sichere Fortsetzung ist blockiert, z. B. durch vorhandene echte Root-Level-`.env*` oder Root-/Policy-Grenzen.
- `FAILED`: technischer Fehler beim sicheren Lesen belegter Artefakte.

Einheitliches Run-State-Modell als Orientierung, nicht als aktive Runtime-Behauptung:

- `INIT_REQUIRED`: Pflichtdateien oder Initialisierung fehlen; nur lesen/prüfen/planen.
- `CONFIG_INCOMPLETE`: Konfiguration ist unvollständig oder inkonsistent; keine Mutation.
- `READY_READONLY`: Lesen, Prüfen und Planen erlaubt; keine mutierenden Schritte.
- `READY_MUTATING`: Modellzustand für bestandene Mutations-Gates; die Onboarding-UI suggeriert ihn nie als aktuell aktiv.
- `VALIDATING`: Validierung läuft; check-only bleibt no-write.
- `RUNNING`: Modellbegriff für echte Runtime-Ausführung; die Onboarding-Preview behauptet keinen laufenden Run.
- `BLOCKED`: Gate-, Policy-, Secret- oder HITL-Blockade; keine Mutation.
- `DONE`: Modellbegriff für abgeschlossene Runs; die Onboarding-Preview behauptet keinen Live-Abschluss.
- `FAILED`: Technischer oder fachlicher Fehler; Review nötig.

## Zielausgabe-Struktur

1. Header: `Willkommen bei 00Z`.
2. Adapter-Kontext: Root, Ausgabeformat und gewählte Adapter-Sicht (`auto`, `pi`, `claude`, `local`).
3. Sicherheitsgrenze: no-write, keine externen Aktionen, keine Secret-Ausgabe, keine echten `.env*` Reads.
4. Belegte Trigger: nur aus Adapter-/Command-Artefakten nachweisbare Pi-/Claude-/Local-Trigger.
5. Setup-Wizard: sechs lineare Schritte — Root erkannt; Sicherheitsgrenze geprüft; Adapter-Trigger belegt; lokale Readiness-Tools vorhanden; nächster sicherer Schritt `ZEN STATUS`; gated Schritte `ZEN MEMORY INIT`/`ZEN SNAPSHOT` nur mit Gates und Bestätigung.
6. Readiness-Tools: lokale Checks mit lokal bekannten Aufrufen, insbesondere Validator/Smoke im Check-only-Modus.
7. Team-Übersicht: defensiv aus Registry/vorhandenen Dateien; mindestens Orchestrator, PromptEngineerAgent, TasklistAgent, RubberDuckAgent und `agents/templates/agent_template.md`, bei fehlenden Artefakten `UNKNOWN`.
8. Statusmodell: kompakte statische Liste der Run-States ohne aktive `READY_MUTATING`-Behauptung.
9. Start-Checkliste: visuelle Checkboxen ohne Persistenzstatus.
10. Team-Vorlagen: `agents/templates/agent_template.md`, Pflichtfelder, Output Contract und Sicherheitsgrenzen als read-only Orientierung.
11. Live-Aktivität: ausdrücklich lokaler stdout-/`dry-run/read-only` Preview-Prozess; keine echte Live-Runtime, kein Pipeline-Status.
12. Handoff: Zweck, Trusted Constraints, Untrusted Context und Handoff-Checkliste.
13. Review-Modus: `REVIEW_REQUIRED`, `APPROVED`, `REJECTED`, `BLOCKED` und Force-Gate-Hinweis.
14. Commands: vorhandene Command-Spezifikationen mit Modus, `Spec-Status` und lokal bekanntem Aufruf, falls vorhanden.
15. First-Run-Reihenfolge: `ZEN STATUS` → `ZEN VALIDATE` → `ZEN MEMORY INIT` nur gated + Bestätigung → `ZEN SNAPSHOT`.
16. Sichere nächste Schritte bei `UNKNOWN`/`BLOCKED`: keine Mutationen starten, fehlende Artefakte/Gates klären, `.env*` nicht lesen und erst nach `PASS` fortfahren.

## P0/P1-Komponenten

### Start-Checkliste

Visuelle Checkbox-Liste ohne Persistenzstatus:

- `[ ]` docs gelesen
- `[ ]` `ZEN STATUS`
- `[ ]` `ZEN VALIDATE` check-only
- `[ ]` bei `FAIL`/`BLOCKED` keine Mutation
- `[ ]` Memory gated
- `[ ]` Snapshot redigiert

### Team-Übersicht und Team-Vorlagen

Die Oberfläche zeigt nur vorhandene oder aus `agents/agent_registry.yaml` ableitbare System-Agenten. Fehlende Artefakte werden als `UNKNOWN` dargestellt. Es werden keine neuen Agenten erzeugt. `agents/templates/agent_template.md` dient als read-only Orientierung für Pflichtfelder, Output Contract und Sicherheitsgrenzen.

### Live-Aktivität als Preview

Die Sektion beschreibt ausdrücklich einen lokalen stdout-/`dry-run/read-only` Preview-Prozess. Sie darf keine echte Live-Runtime, keine laufenden Pipelines und keine automatischen Runtime-Events behaupten. Vorschläge für Preview-Befehle sind nur Text; Nutzer müssen sie bewusst starten.

### Handoff

Handoff nennt Zweck, Trusted Constraints, Untrusted Context und eine kurze Checkliste: Ziel, Evidenz, Risiken/Blocker, redigierte Secrets und nächster sicherer Schritt.

### Review-Modus

- `REVIEW_REQUIRED`: Prüfung nötig.
- `APPROVED`: nächster Schritt innerhalb der Gates akzeptiert.
- `REJECTED`: Vorschlag nicht umsetzen.
- `BLOCKED`: Policy/Gate/Risiko verhindert Fortsetzung.
- Force-Gate-Hinweis: Override nur bewusst, begründet, gate-konform und bestätigt; die Onboarding-UI setzt keinen Force-Gate.

## Einheitliches Blocker-Format

```text
BLOCKED: <kurze Blockade>
Evidenz: <Datei/Beobachtung/Artefakt>
Risiko: <konkretes Sicherheits- oder Qualitätsrisiko>
Nächster sicherer Schritt: <read-only Prüfung oder Bestätigung einholen>
Nicht tun: <verbotene Mutation/Secret-Read/Runtime-Aktion>
```

Bestehende `.env*`-Blocker dürfen nicht abgeschwächt werden: Die sichtbare Blocker-Zählung bezieht sich auf Root-Level-`.env*`; Inhalte echter `.env*` werden nicht gelesen, nicht kopiert und nicht ausgegeben.

## UX-Blueprint

- **User-Journey**: Willkommen → Adapter-Kontext → Sicherheitsgrenze → belegte Adapter-Trigger → Setup-Wizard → lokale Readiness-Tools → Team-Übersicht → Statusmodell → Start-Checkliste → Team-Vorlagen → Live-Preview → Handoff/Review → Command-Spezifikationen → First-Run-Schritte → sichere nächste Schritte bei `UNKNOWN`/`BLOCKED`.
- **TUI-Design**: lineare Sektionen, keine Farbe als Pflichtsignal, klare Präfixe (`PASS`, `UNKNOWN`, `BLOCKED`).
- **Interaction-Model**: keine versteckten automatischen Aktionen; Nutzer führt belegte Checks bewusst selbst aus.
- **Accessibility**: `--linear --no-color`, kurze Zeilen, keine Cursor-Steuerung, keine Mausabhängigkeit.
- **UX-Metriken**: Task-Completion = Nutzer findet belegten ersten Check; Error-Rate = keine erfundenen Commands; Time-on-Task = First-Run Orientierung ohne Doku-Suche.
