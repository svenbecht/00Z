# 00Z — Claude Autoload

Bei neuer Session bzw. erstem Chat im Harness-Root natürlich und kompakt auf Deutsch begrüßen. Keine Tools, Validatoren, Python-Skripte oder ZEN-Intents automatisch starten.

Quellen für die Startausgabe: `docs/welcome.md` und `core/BOOT_PROTOCOL.md`.

Sichere Reihenfolge nennen:

1. „ZEN Status“ — read-only Status prüfen.
2. „ZEN Validate“ / „Validiere ZEN“ — Validierung bewusst starten; bis Gates `PASS` nur read-only arbeiten.
3. „Initialisiere ZEN Memory“ — nur gated und mit expliziter Bestätigung persistieren.
4. „ZEN Snapshot“ — redigierten Handoff ohne Secrets vorbereiten.

Bis Readiness-/Policy-/Secret-/Filesystem-/Prompt-Injection-Gates `PASS` sind: keine mutierenden Aktionen. Keine `.env*` lesen; `.env.example` nur als leeres Template behandeln.
