# ZEN Reasoning Index — Operatives Routing

**Rolle:** Menschlich lesbarer Index für dynamisches Reasoning.
**Maschinenlesbare Quelle:** `harness/reasoning/reasoning_routing.yaml`.

## Routing-Kurzmatrix

| Task-Typ | Trigger-Beispiele | Standard | Komplex/Kritisch |
|---|---|---|---|
| Implementation | implementiere, baue, scaffold | `decomposition` | + `plan_and_solve`, + `self_critique` |
| Architektur | architektur, design, blueprint | `step_back` | + `tree_of_options`, + `meta_cognitive_summary` |
| Analyse/Audit | analysiere, prüfe, audit | `step_back` | + `verification`, + `meta_cognitive_summary` |
| Debugging | bug, fehler, crash | `verification` | + `self_critique`, + `mid_trajectory_validation` |
| Agent/Pipeline | agent, skill, pipeline, handoff | `decomposition` | + `mid_trajectory_validation`, + `milestone_review` |
| Context/Memory | kontext, memory, cache, budget | `context_budget_check` | + `verification`, + `risk_gate` |
| Security/Policy | security, secret, protected | `verification` | + `risk_gate`, + `meta_cognitive_summary` |

## Pipeline Defaults

| Pipeline | Complexity | Methoden |
|---|---|---|
| P1 | `simple` | keine optionalen Methoden |
| P2 | `standard` | `decomposition` |
| P3 | `complex` | `decomposition`, `mid_trajectory_validation` |
| Force Gate | `critical` | `verification`, `risk_gate`, `meta_cognitive_summary` |

## Eskalation

Auf `critical` eskalieren, wenn Security Policies, Adapter-Bootregeln, geschützte Pfade, Force Gates oder Hard-Budget-Limits betroffen sind.

## Ausgabe-Policy

- Keine Chain-of-Thought-Offenlegung.
- Maximal 3 optionale Methoden.
- Maximal 5 Evidenzpunkte.
- Reasoning-Output kurz, schemafähig und budgetiert halten.
