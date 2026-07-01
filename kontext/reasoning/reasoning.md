# ZEN Reasoning Reference — Sicheres dynamisches Reasoning

**Rolle:** Menschlich lesbare Referenz.
**Source of Truth:** `harness/reasoning/reasoning_catalog.yaml` und `harness/reasoning/reasoning_routing.yaml`.

## Grundsatz

Reasoning ist im 00Z ein **steuerbares Qualitäts- und Audit-System**, keine Offenlegung interner Gedankengänge. Agenten nutzen Reasoning intern zur Planung, Prüfung und Risikosteuerung. Extern wird nur eine kurze, prüfbare Zusammenfassung ausgegeben.

## Sicherheitsregel

- Keine Chain-of-Thought-Offenlegung.
- Kein privates Scratchpad persistieren.
- Keine ausführlichen inneren Zwischenschritte ausgeben.
- Stattdessen: Entscheidung, kurze Begründung, Evidenz, Annahmen, Risiken, Validierung, HITL-Punkt.

## Methodengruppen

| Gruppe | Methoden | Zweck |
|---|---|---|
| Pflicht | `chain_of_evidence`, `react_mode` | Evidenz und interne Arbeitsstruktur |
| Struktur | `decomposition`, `plan_and_solve`, `step_back` | Aufgaben begrenzen und planbar machen |
| Qualität | `verification`, `self_critique`, `risk_gate` | Ergebnis prüfen und Risiken klassifizieren |
| Architektur | `tree_of_options`, `meta_cognitive_summary` | Optionen, Annahmen und Trade-offs sichtbar machen |
| Pipeline | `mid_trajectory_validation`, `milestone_review`, `context_budget_check` | P3/Handoff/Budget steuern |

## Komplexitätsstufen

| Stufe | Optionale Methoden | Persistenz | Ziel |
|---|---:|---|---|
| `simple` | 0 | nein | Kurze P1-Antworten ohne Overhead |
| `standard` | 1 | ja | Ein klarer Task oder P2-Brief |
| `complex` | 2 | ja | Mehrere Artefakte, Agent-Handoff, Architektur |
| `critical` | 3 | ja + Gate | Security, Force Gate, hohe Unsicherheit |

## Context-/Kostenregel

Vor jeder größeren Kontextnachladung gilt:

1. Prüfe `harness/context_manifest.yaml`.
2. Prüfe Budget in `harness/budget_policy.yaml`.
3. Lade Summary vor Volltext.
4. Cold Memory nur bei Trigger/Bedarf.
5. Bei Hard Limit stoppen und User fragen.

## Ausgabeformat

Alle persistierten Reasoning-Artefakte müssen gegen `harness/reasoning/reasoning_output.schema.json` validierbar sein. Freitext-Antworten sollen dieselben Felder knapp abbilden.
