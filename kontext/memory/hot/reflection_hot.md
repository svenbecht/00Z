---
type: "memory_hot"
priority: 0
max_tokens: 500
updated: "2026-05-21"
---

# Reflection Hot

> Immer zuerst laden. Nur aktive Fehler, kritische Anti-Patterns und ungelöste Risiken.

## Aktive Fehler

| Datum | Schwere | Fehler | Vermeidungsregel |
|---|---:|---|---|
| — | — | — | — |

## Kritische Anti-Patterns

- Keinen Vollkontext laden, wenn Summary + Referenz reichen.
- Keine maximale Reasoning-Tiefe ohne Komplexitäts-/Risikogrund.
- Keine Agent-Handoffs ohne kompakten Summary-Block.
- Keine Cold-Memory-Dateien im Boot-Profil laden.
