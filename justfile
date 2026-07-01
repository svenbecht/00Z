set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

_default:
    @just --list

validate:
    PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_validate.py --check-only

negative:
    PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_negative.py --check-only

test-all:
    PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_test_all.py --check-only

adapter-smoke:
    PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_adapter_smoke.py --check-only

review-validate:
    PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_review_validate.py --check-only

audit-deep:
    PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_audit_deep.py

release-snapshot:
    PYTHONDONTWRITEBYTECODE=1 python3 tools/zen_release_snapshot.py --check-only

check:
    @just validate
    @just negative
    @just test-all
    @just adapter-smoke
    @just review-validate
    @just release-snapshot
