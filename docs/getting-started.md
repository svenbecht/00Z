# Getting Started with 00Z

## Purpose

This guide explains the **supported first public entry path** for 00Z.

It is intentionally conservative:

- local-first
- read-only/non-destructive first
- no native runtime claim
- no production-write claim

If you only want to understand what 00Z is and verify the repository state safely, this is the correct starting point.

## What you need

Minimum prerequisites:

- Python 3.10+
- a local checkout or extracted copy of the repository
- terminal access

For the first public demo, you do **not** need:

- Docker
- a database
- cloud credentials
- GitHub tokens
- Pi or Claude runtime activation
- dependency installation

## Repository root

Run commands from the repository root:

```bash
cd 00Z
```

If your local folder still has an older internal name, use that local folder path instead. The important part is: run commands from the harness root containing `README.md`, `tools/`, `docs/`, and `validation/`.

## Supported first demo

The main public demo is:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only
```

Why this is the primary demo:

- safe
- local
- non-destructive
- reproducible
- aligned with 00Z's security-first positioning

## Expected output

The validator always prints a local status summary.

Typical shape:

```text
ZEN VALIDATE: PASS
Mode: check-only/no-write
Summary: PASS=... WARN=... FAIL=0
```

Important nuance:

- `FAIL=0` is the main success condition
- `WARN` can still appear in minimal environments
- optional libraries may affect how much schema validation is available

00Z is designed so the check-only entry path stays usable even in a minimal local environment.

## Optional libraries

`tools/zen_validate.py` can use optional libraries if they are already available locally:

- `PyYAML`
- `jsonschema`

These are **not required** for the basic first demo.

If they are missing, the validator can degrade to warnings instead of full strict schema checks.

## Optional read-only orientation

If you want a guided preview before going deeper:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
```

This command is also local and read-only.

It does **not**:

- activate a native Pi runtime
- activate a native Claude runtime
- start a live pipeline
- unlock mutation

## Supported next local checks

After the validation demo, these are the next safe checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_negative.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_all.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_adapter_smoke.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_release_snapshot.py --check-only
```

These remain local-first and are documented further in:

- [`readiness.md`](readiness.md)
- [`release-status.md`](release-status.md)
- [`welcome.md`](welcome.md)

## What is intentionally not active

For the first public release, 00Z should not be read as a complete runtime product.

Not active / not claimed:

- no production-ready Agent OS
- no API/connector platform
- no automatic deployment path
- no automatic GitHub publish flow
- no productive project writes
- no `READY_MUTATING` claim
- no secret-loading workflow

## Troubleshooting

### `python3` not found

Use a Python 3.10+ environment where `python3` is available.

### Validation shows warnings

Warnings are not automatically a release failure.

Read the summary carefully:

- `FAIL > 0` means the repository state is not clean
- `WARN > 0` can mean optional capabilities are missing or a non-blocking issue was detected

### You are unsure what is safe to run

Start with only these two commands:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_onboarding.py --linear --no-color
```

## Recommended reading order

1. [`README.md`](../README.md)
2. [`getting-started.md`](getting-started.md)
3. [`welcome.md`](welcome.md)
4. [`readiness.md`](readiness.md)
5. [`release-status.md`](release-status.md)

## Public-facing promise

The first public promise of 00Z is modest and precise:

> 00Z is an experimental local ZEN agent template with strong validation, explicit safety boundaries, and structured orchestration concepts for Pi and Claude oriented workflows.
