# 00Z — Pi Autoload

Bei neuer Session bzw. erstem Chat im Harness-Root ein kompaktes deutsches Welcome ausgeben. Keine Tools, Validatoren, Shells, Python-Skripte oder ZEN-Commands automatisch starten.

Quellen für die Startausgabe: `docs/welcome.md` und `core/BOOT_PROTOCOL.md`.

Sichere Reihenfolge nennen:

1. `ZEN STATUS` — read-only Status prüfen.
2. `ZEN VALIDATE` — Validierung bewusst starten; bis Gates `PASS` nur read-only arbeiten.
3. `ZEN MEMORY INIT` — nur gated und mit expliziter Bestätigung persistieren.
4. `ZEN SNAPSHOT` — redigierten Handoff ohne Secrets vorbereiten.

Bis Readiness-/Policy-/Secret-/Filesystem-/Prompt-Injection-Gates `PASS` sind: keine mutierenden Aktionen. Keine `.env*` lesen; `.env.example` nur als leeres Template behandeln.
