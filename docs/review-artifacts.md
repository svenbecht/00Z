# 00Z Review Artifacts

Status: `contract-first`
Runtime: keine Reviewer-Agenten, keine Chain, keine produktiven Writes

## Zweck

Die 00Z Reviewer-Schicht validiert strukturierte Review-Ergebnisse, ohne Reviewer automatisch zu starten. Sie ist eine Artefakt- und Qualitätsgrenze nach dem Prinzip:

```text
shared context -> reviewer input -> reviewer result JSON -> validation -> coordinator decision später
```

## Reviewer-Domains

- `security`
- `code-quality`
- `docs`
- `pipeline`
- `reasoning`

## Ergebnisformat

Reviewer schreiben JSON nach dem Schema:

```text
harness/schemas/reviewer-result.schema.json
```

Pflichtfelder je Finding:

- `severity`
- `category`
- `title`
- `evidence`
- `recommendation`
- `confidence`
- `source`
- `domain`
- `fingerprint`

Zusatzregeln:

- `critical` braucht `blockingReason`.
- `critical` darf nicht `confidence=low` haben.
- File-bezogene Findings brauchen `file` und positive `line`.
- Nicht-kritische Findings dürfen kein `blockingReason` enthalten.
- `fingerprint` muss deterministisch sein.

## Lokale Validierung

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_review_validate.py --check-only
just review-validate
```

## Fixtures

```text
validation/fixtures/review/valid/
validation/fixtures/review/invalid/
```

Invalid Fixtures müssen vom Validator abgelehnt werden. Wenn ein invalid Fixture plötzlich passt, ist das ein Validator-Fehler.

## Grenzen

Diese Schicht aktiviert nicht:

- echte Reviewer-Agenten,
- permanente Agent-Teams,
- Chains,
- produktive Projektwrites,
- native TUI-Aktionen,
- Git-/CI-/Deployment-Flows.
