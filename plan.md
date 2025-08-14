# Test Suite Action Plan

## Current Status

- Test suite: 174 passed, 2 skipped, 0 failed (local run)
- Splunk container: running reliably; Makefile target added to wait for readiness

## Completed

- Environment setup for tests with Splunk (Makefile `test-with-splunk` target with readiness check)
- Fixed refactoring fallout in `tests/test_workflow_runner.py`; relaxed progress assertions
- Resolved assertion mismatches in contrib health tool tests; aligned description expectations
- Standardized tool call result handling across tests (`result.data` vs legacy `contents[0].text`)
- Stabilized tests against real Splunk data (non-deterministic ordering/volumes)

- CI: Added GitHub Actions for tests and lint/type checks
  - `.github/workflows/test.yml` runs unit/fast tests on push/PR; optional integration path with Splunk via manual trigger
  - `.github/workflows/lint.yml` runs Ruff and Mypy on push/PR
- Pre-commit: Added `.pre-commit-config.yaml` (black, ruff, eof-fixer, trailing-whitespace) and documented usage in `docs/community/contributing.md`

## Remaining Work

### A. CI/CD: GitHub Actions for tests

Done.

### B. Pre-commit

Done.

### C. Warnings hygiene (nice-to-have)
- Investigate duplicate registration warnings; consider idempotent registration or conditioned logging

## Verification

- CI workflow green on PRs (tests) and optionally lint/type checks
- Local: `make test` (fast) or `make test-with-splunk` (integration)
