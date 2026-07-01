---
id: 00Z-orchestrator
version: 0.1.0
status: scaffold
language: de
state_machine: ../harness/state_machine.yaml
---

# 00Z Orchestrator

Der Orchestrator routet ZEN-Trigger auf Commands und Pipelines.

## Trigger

- `ZEN NEW`
- `ZEN MEMORY INIT`
- `ZEN NEW BUILD`
- `ZEN STATUS`
- `ZEN PLAN`
- `ZEN SNAPSHOT`
- `ZEN P1`
- `ZEN P2`
- `ZEN P3`
- `ZEN RESET`
- `ZEN VALIDATE`

## Routing vs. Run-State

- Trigger-State-Machine: `harness/state_machine.yaml` ist autoritative Quelle für ZEN-Trigger und Routing auf Commands/Pipelines.
- Routing-States wie `IDLE`, `PIPELINE`, `P3_PIPELINE`, `VALIDATE` beschreiben nur die Command-/Pipeline-Auswahl.
- Run-State-Lifecycle: `harness/state_machine.yaml#run_state_model` und `harness/runtime.yaml#run_state_model` steuern Security, Lifecycle, Mutation und Fehlerzustände.
- `ZEN VALIDATE` routet auf `harness/commands/zen-validate.yaml` und nutzt die lokale Validator Runtime `tools/zen_validate.py`.

## Regeln

- Lade zuerst `core/BOOT_PROTOCOL.md`.
- Prüfe Policies vor Tool-Nutzung.
- P3 endet immer mit Force Gate.
