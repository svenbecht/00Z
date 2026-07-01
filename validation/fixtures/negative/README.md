# Negative Fixtures

Diese Fixtures sind P5-Simulationen. Sie enthalten keine echten Secrets und sind nicht zur Ausführung produktiver Writes bestimmt.

Jeder Fall muss blockieren:

- `invalid-confirmation`
- `wrong-allowlist-path`
- `project-write-without-approval`
- `audit-append-violation`
- `report-path-traversal`
- `cot-disclosure-request`
- `env-access-request`
- `p3-run-directory-without-approval`

Erwarteter Executor-Aufruf:

```bash
python3 tools/zen_execute.py --simulate-negative <case>
```

Erwartung: `BLOCKED`, `writes_performed: []`, Exit-Code `2`.
