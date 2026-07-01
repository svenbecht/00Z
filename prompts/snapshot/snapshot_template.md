---
type: snapshot-template
version: "0.1.0"
status: template
language: de
secret_scan_required: true
---

# Session Snapshot — <DATE>

## Kontext

| Feld | Wert |
|---|---|
| Workspace | `<WORKSPACE>` |
| Projekt | `<PROJECT>` |
| Phase | `<PHASE>` |
| Adapter | `<ADAPTER>` |

## Ziel der Session

<SESSION_GOAL>

## Geänderte Dateien

| Datei | Änderung | Gate |
|---|---|---|
| `<FILE>` | <CHANGE> | <GATE_STATUS> |

## Entscheidungen

- <DECISION>

## Offene Punkte

- [ ] <OPEN_ITEM>

## Risiken / WARN

- <WARNING>

## Nächster Schritt

<NEXT_STEP>

## Handoff-Hinweis

Vor Nutzung in neuer Session: keine Secrets, keine echten `.env`-Inhalte, keine vertraulichen Tokens.
