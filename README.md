# 00Z — The ZEN Agent

<p align="left">
  <img src="assets/00z-logo.png" alt="00Z logo" width="250">
</p>

**Experimental local, security-first agent harness template for structured AI-agent workflows, with adapter contracts for Claude- and pi-agent-oriented usage.**

[![Status](https://img.shields.io/badge/status-experimental-orange)](docs/readiness.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Language](https://img.shields.io/badge/lang-Python%20%2F%20YAML-green)](docs/architecture.md)

> ⚠️ 00Z is experimental. It is intentionally conservative, local-first, and not production software.

## Status at a glance

| Area | Status |
| --- | --- |
| Local validation tools | Implemented |
| Reasoning contracts | Implemented |
| Safety/policy gates | Implemented as local checks |
| Pi/Claude adapter contracts | Present as contracts/scaffolding |
| Native Pi/Claude runtime | Not bundled |
| Native LLM provider connector | Not included |
| Productive project writes | Disabled by default |
| Dependency installation | Not required for the first demo |
| GitHub/deploy automation | Not included |

## In short

00Z is a **local-first safety harness** for experimenting with AI-agent architecture. It makes prompts, policies, reasoning, memory concepts, adapters, pipelines, and validation boundaries explicit and inspectable.

Use it to study or prototype structured AI-agent workflows without claiming a production runtime, automatic deployment flow, or native LLM provider connector.

## Reasoning-first safety design

One of 00Z's core strengths is its **explicit reasoning layer**. Reasoning is treated as a controlled quality and audit mechanism, not as hidden magic and not as chain-of-thought disclosure.

The repository separates reasoning into inspectable artifacts:

- `harness/reasoning/reasoning_catalog.yaml` defines safe reasoning methods, evidence rules, budgets, and forbidden outputs.
- `harness/reasoning/reasoning_routing.yaml` maps task types, risk levels, pipelines, and context budgets to suitable reasoning methods.
- `harness/reasoning/reasoning_output.schema.json` defines a compact, auditable output contract for reasoning summaries.
- `kontext/reasoning/` provides human-readable protocol and routing references.

The design favors:

- evidence-backed answers over uncheckable internal reasoning
- dynamic method selection based on task type and risk
- explicit complexity levels: `simple`, `standard`, `complex`, `critical`
- bounded outputs with token budgets and evidence limits
- no private scratchpad persistence
- no chain-of-thought disclosure
- HITL points for review, escalation, or blocking decisions

In practice, 00Z aims to make reasoning **reviewable, budgeted, and safety-gated** while keeping productive writes and runtime activation disabled until explicitly approved.

## Install with curl

00Z intentionally does **not** recommend `curl | bash`.
Instead, download the installer, inspect it, and run it locally.
Run it from the directory where you want the `00Z/` folder to be created.

```bash
curl -fsSL https://raw.githubusercontent.com/svenbecht/00Z/main/install.sh -o /tmp/00z-install.sh
less /tmp/00z-install.sh
bash /tmp/00z-install.sh
cd 00Z
```

The installer only downloads and extracts the repository.
It does **not** use `sudo`, install dependencies, or execute project code automatically.

Optional: install a specific tag or into a custom directory once tags are published:

```bash
bash /tmp/00z-install.sh --ref v0.1.0 --ref-type tag --dir ./00Z-v0.1.0
```

## Quick start

Run from the repository root after clone or install:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only
```

Short form, if `just` is installed:

```bash
just validate
```

Typical successful output:

```text
ZEN VALIDATE: PASS
Mode: check-only/no-write
Summary: PASS=... WARN=... FAIL=0
```

Optional read-only orientation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
```

## What 00Z is

00Z is a YAML-/Markdown-first harness template for making AI-agent workflow boundaries explicit:

- declarative policies, schemas, gates, commands, and pipelines
- local validation tools with no destructive defaults
- reasoning contracts with evidence, risk, validation, and HITL fields
- adapter contracts for Pi and Claude oriented workflows
- memory and context-management concepts
- dry-run-first execution and report boundaries

## What 00Z is not

00Z is **not**:

- a finished Agent OS
- a production API/connector platform
- a native LLM provider connector
- a native Pi or Claude runtime
- a runtime that executes live destructive writes by default
- an automatic deployment or GitHub publishing pipeline

00Z does not currently include a native LLM provider connector. Custom LLM provider support would require a future provider-runtime layer with explicit network, secret, validation, and safety boundaries.

## Current capabilities

- **YAML-first harness** with machine-readable schemas
- **Reasoning contracts** for safe, reviewable reasoning summaries
- **Agent and prompt templates** in Markdown
- **Pi and Claude adapter contracts** (`native_runtime_implemented: false`)
- **5-layer memory concept** in Markdown artifacts
- **P1/P2/P3 pipeline model** for intent, escalation, and review-oriented workflow design
- **Local validation tooling** with `--check-only` no-write mode
- **Explicit write-boundary design** where productive writes stay disabled until separate approval and gates exist

## Typical workflow

```text
Read docs/welcome.md
→ run the validation demo
→ inspect readiness/status docs
→ plan changes
→ keep mutation gated
→ run explicit snapshot/handoff after review
```

## Project structure

```text
core/          identity, orchestrator, boot protocol
harness/       policies, schemas, pipelines, commands, reasoning contracts
adapters/      Pi and Claude adapter contract placeholders
agents/        system agents and templates
prompts/       prompt templates and snapshots
kontext/       memory and reasoning artifacts
validation/    gate definitions, fixtures, reports
tools/         local validators and smoke tests
docs/          public and operator documentation
```

## Core docs

- [`docs/getting-started.md`](docs/getting-started.md)
- [`docs/welcome.md`](docs/welcome.md)
- [`docs/commands.md`](docs/commands.md)
- [`docs/readiness.md`](docs/readiness.md)
- [`docs/release-status.md`](docs/release-status.md)
- [`docs/architecture.md`](docs/architecture.md)

## Safety boundaries

- No production-ready runtime claims
- No native Pi/Claude runtime activation
- No native LLM provider connector
- No API/connector platform claims
- No automatic dependency installation
- No `.env` secret read/write behavior
- No built-in GitHub/deploy publishing flow
- Productive writes require explicit gates and human confirmation

## Release posture

This repository is documented as an **experimental local release**. For current status, see:

- [`docs/release-status.md`](docs/release-status.md)
- [`docs/readiness.md`](docs/readiness.md)

## Who it is for

- developers exploring AI-agent architecture
- builders who want safer local AI workflow templates
- reviewers and learners studying gate-based design
- people interested in explicit reasoning, validation, and safety boundaries

## License

00Z is licensed under the [MIT License](LICENSE).

## About the name

`00Z` is short for **The ZEN Agent**: a compact, configurable template you can adapt to your own agent workflow.
