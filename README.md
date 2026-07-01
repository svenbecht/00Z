# 00Z

**Experimental local ZEN agent template for Pi and Claude, focused on security gates, reasoning, pipelines, memory, and structured AI workflows.**

> Status: **experimental** · **not production-ready** · local-first · security-first

00Z is an early Agent-Orchestration/Harness concept. It is designed as a configurable template for building safer AI-agent workflows with explicit validation gates, structured reasoning, memory concepts, and pipeline boundaries.

It is **not** a finished Agent OS, not a production runtime, and not an API/connector platform.

## Why 00Z exists

AI-agent projects can quickly become hard to reason about: prompts, memory, tools, permissions, pipelines, and safety rules often live in different places or are not validated at all.

00Z explores a stricter structure:

- define agent behavior in readable Markdown/YAML artifacts
- keep safety boundaries explicit
- validate configuration before mutation
- separate planning, execution, memory, and release readiness
- support Pi and Claude oriented workflows without pretending to be a complete runtime

The name **00Z** means: a ZEN-style agent template you can adapt for yourself — inspired by the idea of a configurable agent framework rather than a fixed product.

## Current capabilities

- YAML-first harness configuration
- Markdown-based agent and prompt specifications
- Pi/Claude adapter structure
- 5-layer memory concept
- dynamic reasoning and pipeline model
- security, placeholder, filesystem, prompt-injection, and policy gates
- non-destructive local validation tools
- explicit write-boundary design: productive writes remain disabled until separate gates and human confirmation exist

## Quickstart: validation demo

The strongest first demo is the local validation gate.

Requirements:

- Python 3.10+
- run from the repository root
- no dependency installation required for the basic demo

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only
```

Typical output shape:

```text
ZEN VALIDATE: PASS
Mode: check-only/no-write
Summary: PASS=... WARN=... FAIL=0
```

Important nuance:

- `FAIL=0` is the main success condition
- `WARN` can still appear in minimal environments
- optional libraries can affect validation depth

`--check-only` is intentionally read-only/no-write. It does not generate reports and is the safest way to inspect the current harness state.

For the supported first-release setup path, see [`docs/getting-started.md`](docs/getting-started.md).

## Optional onboarding preview

For a read-only orientation flow:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
```

This is a local helper only. It does not activate a native Pi or Claude runtime.

## Example workflow

A typical local workflow is:

```text
Read docs/welcome.md
→ run the validation demo
→ inspect readiness/status docs
→ plan changes
→ keep mutation gated
→ snapshot/handoff only after explicit review
```

Core commands and concepts are documented in:

- [`docs/getting-started.md`](docs/getting-started.md)
- [`docs/welcome.md`](docs/welcome.md)
- [`docs/commands.md`](docs/commands.md)
- [`docs/readiness.md`](docs/readiness.md)
- [`docs/release-status.md`](docs/release-status.md)

## Safety boundaries

00Z is intentionally conservative.

Current boundaries:

- no production-ready runtime claim
- no native Pi/Claude runtime activation claim
- no API/connector platform claim
- no automatic dependency installation
- no automatic GitHub, deployment, or publish flow
- no reading or writing real `.env` secrets
- productive project writes remain disabled unless future gates, explicit human approval, and audit mechanisms are implemented

## Project structure

```text
core/          identity, orchestrator, boot protocol
harness/       machine-readable configuration, policies, schemas
adapters/      Pi and Claude adapter structure
agents/        system agents and templates
prompts/       prompt templates and snapshots
kontext/       memory and reasoning artifacts
validation/    gate definitions, fixtures, reports
tools/         local validation and smoke-test utilities
docs/          public and operator documentation
```

## Release posture

The first public GitHub release is intended as an **experimental** release.

See:

- [`docs/release-status.md`](docs/release-status.md)
- [`docs/readiness.md`](docs/readiness.md)

## Who this is for

00Z is currently most useful for:

- developers exploring AI-agent architecture
- people interested in safer local AI workflows
- reviewers looking at early-stage agent orchestration design
- builders who want to study gates, memory concepts, and structured prompt/harness design

It is also part of a learning journey: the project is intentionally public-facing, but still experimental and evolving.

## License

00Z is licensed under the [MIT License](LICENSE).
