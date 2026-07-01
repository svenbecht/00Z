---
skill_name: "{{SKILL_NAME}}"
version: "0.1.0"
status: draft
idempotent: true
language: de
used_by:
  - "{{AGENT_NAME}}"
input_schema:
  type: object
output_schema:
  type: object
protected_by: [policy_gate, secret_gate, filesystem_gate]
---

# {{SKILL_NAME}}

## Zweck

{{ONE_LINE_PURPOSE}}

## Scope

- In Scope: {{IN_SCOPE}}
- Out of Scope: {{OUT_OF_SCOPE}}

## Input

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `{{FIELD}}` | string | ja | {{FIELD_DESC}} |

## Verarbeitung

1. Input validieren.
2. Sicherheits- und Policy-Constraints prüfen.
3. Transformation oder Analyse ausführen.
4. Ergebnis strukturiert zurückgeben.

## Output

```json
{
  "status": "ok",
  "result": {},
  "evidence": [],
  "warnings": []
}
```

## Fehlerbehandlung

- `InvalidInput` -> Rückfrage oder BLOCKED.
- `PolicyViolation` -> BLOCKED.
- `NoResult` -> leeres Ergebnis mit Begründung.
