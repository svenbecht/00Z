---
type: "memory_hot"
priority: 1
max_tokens: 700
updated: "2026-05-21"
---

# Semantic Profile

## Projekt

| Feld | Wert |
|---|---|
| Name | 00Z |
| Typ | Agent-Harness / Prompt-Orchestrierung |
| Ziel | Skalierbares, kostenbewusstes Agent-System für Pi Agent und Claude Code |
| Sprache | Deutsch |
| Primärformat | Markdown + YAML/JSON Schemas |

## Design-Prinzipien

- Kontext ist budgetiert, nicht pauschal.
- Reasoning ist dynamisch und risikobasiert, nicht immer maximal.
- Handoffs nutzen Summary + Referenzen vor Volltext.
- Große Dateien werden gecacht und nur bei Bedarf vollständig geladen.
- Pi und Claude verwenden gemeinsame Harness-Policies mit adapter-spezifischen Hinweisen.
