# Willkommen bei 00Z

Willkommen bei 00Z — einem lokalen, security-first Agent-Harness für Pi und Claude. Das Harness hilft dir, Projekte strukturiert mit Memory, ZEN-Commands, Agenten, Pipelines und Validierungs-Gates zu steuern.

## First-Run Flow

Optionaler sicherer Startpunkt für neue Nutzer: `PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color`. `ZEN ONBOARDING` ist dafür nur ein lokaler Hilfsaufruf zur stdout-only/read-only Orientierung: kein nativer Pi-/Claude-Adapter-Trigger, keine Runtime-Freigabe und keine echte Live-Pipeline. Die lokale Oberfläche schreibt nichts, liest keine Inhalte echter `.env*`, zeigt nur belegte Trigger/Commands aus vorhandenen Artefakten und ersetzt keinen Gate-Durchlauf mit `ZEN STATUS`/`ZEN VALIDATE`. P0/P1-Orientierung umfasst Setup-Wizard/Start-Checkliste, Team-Übersicht sowie Handoff/Review; alles bleibt read-only/no-write, und Commands müssen bewusst gestartet werden.

1. `ZEN STATUS` — aktuellen Harness-/Projektstatus read-only prüfen.
2. `ZEN VALIDATE` — lokale Validierung ausführen; bei `FAIL` keine mutierenden Aktionen starten.
3. `ZEN MEMORY INIT` — Memory/Projektprofil prüfen oder initialisieren, wenn Hot Memory fehlt oder veraltet ist.
4. `ZEN NEW` — neues Projekt vorbereiten, falls noch kein Projekt existiert.
5. `ZEN NEW BUILD` — Projektagenten aus Templates vorbereiten, wenn ein Projekt Agenten braucht.
6. `ZEN SNAPSHOT` — bei Handoff, Kontextwechsel, langer Session oder vor Übergabe einen redigierten Snapshot vorbereiten.

Hinweis: Mutierende Schritte bleiben gated. Ohne `READY_MUTATING`, passende Gates und Bestätigung liefert der Agent nur Intake, Dry-Run oder Planung.

## ZEN-Befehle

| Befehl | Kurzbeschreibung |
|---|---|
| `ZEN ONBOARDING` | Lokaler Hilfsaufruf/read-only Orientierung über `tools/zen_onboarding.py`; kein nativer Pi-/Claude-Adapter-Trigger, keine Runtime- oder Readiness-Freigabe. |
| `ZEN NEW` | Neues Projektprofil vorbereiten; Persistenz nur nach Mutationsfreigabe. |
| `ZEN MEMORY INIT` | Hot Memory und Projektprofil prüfen oder initialisieren. Guarded/mutierend, braucht Gates und Bestätigung. |
| `ZEN NEW BUILD` | Projektagent aus Template spezifizieren/erzeugen; Datei-Erzeugung nur nach Freigabe. |
| `ZEN STATUS` | Read-only Status über Harness, Gates, aktive Projekte und nächste sichere Aktion. |
| `ZEN PLAN` | Plan read-only entwerfen; Persistenz nur nach Freigabe. |
| `ZEN SNAPSHOT` | Redigierten Session-Handoff vorbereiten; darf keine Secrets enthalten. |
| `ZEN P1` | Direkter Ask-/Klärungsmodus ohne Pipeline-Overhead. |
| `ZEN P2` | Prompt Brief für genau einen Ziel-Agenten. |
| `ZEN P3` | Multi-Agent Pipeline mit maximal drei Agenten und Force Gate. |
| `ZEN RESET` | Logischer Session-Reset ohne Deletes, Git-Aktionen oder Systemänderungen. |
| `ZEN VALIDATE` | Source-read-only Validierung; Normalmodus schreibt nur redigierte Reports unter `validation/reports/`. |

## Memory Init

`ZEN MEMORY INIT` ist für Projektprofil, Hot Memory und nächste Aktionen gedacht. Es ist guarded/mutierend: echte Persistenz benötigt `READY_MUTATING`, Policy-/Filesystem-/Secret-/Prompt-Injection-Gates und explizite Bestätigung. Im read-only Zustand soll der Agent nur prüfen, erklären oder einen Dry-Run-Plan liefern.

## Snapshot

`ZEN SNAPSHOT` erstellt einen redigierten Session-Handoff für neue Sessions, Kontextwechsel oder Übergaben. Snapshots dürfen keine Secrets, `.env`-Inhalte, Tokens oder vertrauliche Rohdaten enthalten und benötigen vor Persistenz die passenden Gates und Bestätigung.
