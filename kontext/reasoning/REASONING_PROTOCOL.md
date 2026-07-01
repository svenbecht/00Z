# ZEN Reasoning Protocol

Reasoning-Output ist ein **Audit-Artefakt**, keine Offenlegung interner Gedankengänge.

## Pflichtregeln

1. Keine Chain-of-Thought-Offenlegung.
2. Kein privates Scratchpad speichern.
3. Reasoning-Output ist kurz, prüfbar und budgetiert.
4. Persistierte Outputs müssen zu `harness/reasoning/reasoning_output.schema.json` passen.
5. Auswahl der Methoden erfolgt über `harness/reasoning/reasoning_routing.yaml`.

## Schema-Felder

- `task_id`
- `agent_id`
- `complexity`: `simple | standard | complex | critical`
- `selected_methods`: maximal 3 optionale Methoden
- `zielverstaendnis`
- `evidenzbasis`: maximal 5 Claim/Basis-Paare
- `annahmen`
- `risiken`
- `validierung`
- `hitl_required`
- `hitl_punkt`
- `result_status`: `done | partial | blocked | needs_review`
- `no_chain_of_thought_disclosure: true`

## Markdown-Ausgabe

```markdown
## REASONING_OUTPUT
- Task: <task_id>
- Agent: <agent_id>
- Complexity: <simple|standard|complex|critical>
- Methoden: <max 3>
- Zielverständnis: <kurz>
- Evidenz: <Claim — Basis>
- Annahmen: <kurz>
- Risiken: <kurz>
- Validierung: <kurz>
- HITL nötig: <true|false>
- HITL-Punkt: <kurz>
- Status: <done|partial|blocked|needs_review>
- Keine CoT-Offenlegung: true
```

## Budget

- Ziel: ≤ 500 Tokens pro Reasoning-Output.
- Hard Limit: 700 Tokens.
- Bei Budgetdruck: Evidenzpunkte priorisieren, optionale Methoden reduzieren, nicht Sicherheitsvalidierung entfernen.
