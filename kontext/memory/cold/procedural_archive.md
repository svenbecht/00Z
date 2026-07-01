---
type: "memory_cold"
priority: 3
load_policy: "on_demand"
max_tokens: 1500
updated: "2026-05-21"
---

# Procedural Archive

> Bewährte Workflows und Anti-Patterns. Nicht automatisch laden; nur bei Workflow-/Routine-Fragen.

## Workflows

### Context-Budgetierter Task

1. Intent bestimmen.
2. `harness/context_manifest.yaml` Profil wählen.
3. Hot Memory laden, Cold Memory nur bei Trigger.
4. Reasoning-Depth über `harness/reasoning/reasoning_routing.yaml` wählen.
5. Ergebnis mit Summary + Evidenz ausgeben.

## Anti-Patterns

| Anti-Pattern | Risiko | Alternative |
|---|---|---|
| Vollständiges Archiv beim Boot laden | Hohe Kosten, Lost-in-Middle | Hot Memory + Summary-Cache |
| P3 ohne Handoff-Summary | Kontextduplikate | Summary + Referenzpfade |
