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

## Remaining Work

### A. CI/CD: GitHub Actions for tests (in scope now)
- Add `.github/workflows/test.yml` to run on push and PR:
  - Checkout → Setup Python/uv → `uv sync --dev` → `uv run pytest -q`
  - Optional: start Splunk service (docker compose) for integration path, or mock-only fast path
- Add a follow-up workflow for lint/type checks:
  - `uv run ruff check src/ tests/`
  - `uv run mypy src/`

### B. Pre-commit (optional next)
- Introduce `.pre-commit-config.yaml` with ruff, black, end-of-file-fixer, trailing-whitespace
- Document `pre-commit install` in contributing docs

### C. Warnings hygiene (nice-to-have)
- Investigate duplicate registration warnings; consider idempotent registration or conditioned logging

## Verification
- CI workflow green on PRs (tests) and optionally lint/type checks
- Local: `make test` (fast) or `make test-with-splunk` (integration)
