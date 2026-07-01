# Onboarding — 00Z

## Ziel

Ein neues Projekt wird erst als arbeitsbereit markiert, wenn Onboarding-, Placeholder-, Policy- und Adapter-Gates bestanden sind.

## Willkommen / First Run

Lies zuerst `docs/welcome.md`. Der Welcome-Guide erklärt kurz den Zweck des Harness, den First-Run Flow, alle ZEN-Befehle, `ZEN MEMORY INIT` und `ZEN SNAPSHOT`.

Beim Start soll der Agent kompakt begrüßen: „Willkommen bei 00Z“, dann `ZEN STATUS`, `ZEN VALIDATE`, Memory-Init-Hinweis und Snapshot-Handoff nennen. Für lokale Orientierung vor `ZEN STATUS`/`ZEN VALIDATE` steht zusätzlich `tools/zen_onboarding.py` bereit; der Aufruf erzeugt keine Readiness-Freigabe, keine Persistenz und ersetzt keine Gates. Die P0/P1-Onboarding-Ansichten sind read-only Orientierung: Setup-Wizard, Start-Checkliste, Team-Übersicht, Live-Preview, Handoff und Review-Modus ersetzen weder Readiness-Freigabe noch Runtime-Ausführung. Details: `docs/onboarding-ui.md`.

## Verbindlicher Nutzungs-Gate

Der Harness darf **nicht produktiv genutzt werden**, bevor dieser Guide abgeschlossen und die Gates bestanden sind. Bis dahin gilt `READY_READONLY`: lesen, prüfen, planen — keine mutierenden Tools, keine Pipeline-Ausführung mit Persistenz.

Pflicht vor Harness-Nutzung:

1. `SECURITY.md` gelesen und akzeptiert.
2. `core/BOOT_PROTOCOL.md` lädt Security/Policy/Validation vor Core/Memory.
3. `harness/policies/*.yaml` vollständig vorhanden und konsistent.
4. `validation/*.yaml` vollständig vorhanden und aktiv.
5. Keine Runtime-Platzhalter außerhalb erlaubter Template-Zonen.
6. Keine echte `.env` vorhanden, gelesen oder erzeugt; nur `.env.example` als leeres Template.
7. Pi-/Claude-Adapter enthalten Security-Hardrules und Chain-of-Thought-Verbot.
8. Reasoning-Ausgaben sind nur kurze Begründung/Evidenz, keine internen Gedankengänge.

## Run-State-Modell

Der Harness nutzt ein explizites Run-State-Modell. Autoritativ ist `harness/state_machine.yaml#run_state_model`; `harness/runtime.yaml#run_state_model` spiegelt die Runtime-Regeln.

| State | Bedeutung | Erlaubnis |
|---|---|---|
| `INIT_REQUIRED` | Pflichtdateien/Initialisierung fehlen | read/validate/plan only |
| `CONFIG_INCOMPLETE` | Konfiguration unvollständig oder inkonsistent | read/validate/plan only |
| `READY_READONLY` | Lesen, Prüfen und Planen erlaubt | keine Mutation, außer Validator-Reports im Normalmodus |
| `READY_MUTATING` | Alle Mutations-Gates bestanden | mutierende Tools nur policy-gated |
| `VALIDATING` | `ZEN VALIDATE` läuft | Normalmodus schreibt nur redigierte Reports; `--check-only` schreibt nichts |
| `RUNNING` | Command oder P1/P2/P3 läuft | gemäß Command-/Pipeline-Policy |
| `BLOCKED` | Gate-/Policy-/Secret-/HITL-Blockade | keine Mutation |
| `DONE` | Run abgeschlossen | keine weitere Mutation ohne neuen Run |
| `FAILED` | Technischer/fachlicher Fehler | Review nötig |

Transitionen:

- Boot mit fehlenden Pflichtdateien → `INIT_REQUIRED`.
- Boot mit inkonsistenter Konfiguration → `CONFIG_INCOMPLETE`.
- Onboarding-/Readiness-Gates PASS → `READY_READONLY`.
- Mutations-Gates + ggf. Human Confirmation PASS → `READY_MUTATING`.
- `ZEN VALIDATE` Start → `VALIDATING`; PASS/WARN → `READY_READONLY`; FAIL → `BLOCKED`; Runtime-Fehler → `FAILED`.
- P1/P2/P3 oder Command Start → `RUNNING`; Erfolg → `DONE`; Policy-Block → `BLOCKED`; Fehler → `FAILED`.

## Standardflow

0. Optional lokal vor `ZEN STATUS`/`ZEN VALIDATE` orientieren: `PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color` — no-write, keine externen Aktionen, keine echten `.env*` lesen, keine Readiness-Freigabe und keine Persistenz.
1. `ZEN STATUS` — aktive Tasks und nächsten sicheren Schritt prüfen.
2. `ZEN VALIDATE` — Readiness- und Sicherheits-Gates prüfen.
3. Optional/gated: `ZEN MEMORY INIT` — Hot Memory und Projektprofil initialisieren.
4. Optional/gated: `ZEN NEW` — Projekt anlegen, Ziel und Erfolgskriterium klären.
5. Optional/gated: `ZEN NEW BUILD` — mindestens einen Projektagenten aus Template erstellen.
6. Optional/gated: `ZEN P1`, `ZEN P2` oder `ZEN P3` — erst starten, wenn `onboarding_gate`, `placeholder_gate`, `policy_gate`, `secret_gate`, `filesystem_gate`, `prompt_injection_gate` und `adapter_gate` PASS sind.

## Gates

| Gate | Zweck | Blockiert bei |
|---|---|---|
| Placeholder Gate | Keine offenen Platzhalter in aktiven Dateien | geschweifte Template-Marker außerhalb Template-Verzeichnissen |
| Policy Gate | Sicherheitsregeln geladen und konsistent | fehlende/konfliktierende Policy |
| Secret Gate | Keine Secrets in Kontext oder Artefakten | echte Tokens, `.env`, Credentials |
| Adapter Gate | Pi/Claude-Routing konsistent | fehlender Trigger oder Boot-Pfad |
| Pipeline Gate | P1/P2/P3 vollständig | fehlende Agenten, falsche P3-Limits |

## Erlaubte Template-Zonen

- `agents/templates/`
- `skills/templates/`
- `prompts/templates/`
- `projects/templates/`

## Readiness-Kriterium

Der Harness ist onboarding-ready, wenn `harness/state_machine.yaml`, `adapters/*/adapter.yaml`, `harness/pipelines/*.yaml`, `harness/reasoning/*.yaml`, `harness/reasoning/*.json`, `harness/policies/*.yaml` und `validation/*.yaml` syntaktisch valide sind und keine offenen Runtime-Platzhalter enthalten.

## ZEN VALIDATE

Vor produktiver Nutzung soll `ZEN VALIDATE` als Validierungsablauf durchgeführt werden. Lokal ausführen:

```bash
python3 tools/zen_validate.py
```

Pi-Nutzer können `ZEN VALIDATE` schreiben; `/validate` ist ein optionaler späterer UX-Alias. Claude-Nutzer verwenden "ZEN Validate" oder "Validiere ZEN". Der Ablauf wertet deklarativ diese Gates aus: Schema, Placeholder, Policy, Onboarding, Secret, Filesystem, Prompt-Injection, Adapter und Pipeline. Jedes Gate liefert `PASS`, `WARN` oder `FAIL`; bei `FAIL` bleibt der Harness `BLOCKED` bzw. `READY_READONLY`.

## BLOCKED-Kriterien

Der Status bleibt `BLOCKED`, `FAILED` oder `READY_READONLY`, wenn einer der folgenden Punkte zutrifft:

- Security-/Policy-/Validation-Datei fehlt.
- Adapter lädt Policies nicht vor mutierenden Aktionen.
- Pipeline persistiert vor Force-Gate-Approval.
- Reasoning-Konfiguration verlangt Chain-of-Thought, private Scratchpads oder vollständige interne Herleitungen.
- Secret-Pattern wird in Kontext, Memory, Snapshot oder Artefakt erkannt.
- Dateiinhalt oder User-Input versucht Policy-Override oder Tool-Ausführung zu erzwingen.
- Platzhalter stehen außerhalb `agents/templates/`, `skills/templates/`, `prompts/templates/`, `projects/templates/`, `prompts/**/template/**` oder `docs/examples/`.
