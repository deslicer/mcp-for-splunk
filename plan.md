# Test Suite Action Plan

## Overview
Based on the test run using `make test`, there are 43 failed tests, 117 passed, 14 errors, and various warnings. The failures primarily stem from:
- Splunk connection issues (Connection refused, degraded mode).
- Code refactoring (e.g., agents moved to workflows, missing attributes).
- Assertion mismatches (e.g., expected keys not in responses, description mismatches).
- TypeErrors in handling tool results.

The errors in `test_workflow_runner.py` indicate outdated imports/references after potential refactoring (e.g., agents to workflows).

This plan categorizes failures, proposes troubleshooting steps, and suggests updates/removals to achieve a clean test suite. Prioritize fixes that enable Splunk-dependent tests, then address refactoring impacts.

## Step 1: Environment Setup and Verification
Many failures are due to Splunk not being available. Tests assume a connected Splunk instance but run in degraded mode.

### Actions:
- Verify if tests require Splunk Docker: Run `make docker-up` before tests to start Splunk container.
- Update Makefile: Add a new target `test-with-splunk` that runs `docker-up`, waits for Splunk health, then runs tests, and `docker-down` after.
- For CI: Ensure Docker Compose starts Splunk in test workflows.
- Retest after fix: Rerun `make test` with Splunk up to confirm which failures resolve.

### Expected Impact:
- Resolves ~30-35 failures related to {'empty_result': True} responses from tools expecting Splunk data.

## Step 2: Categorize and Fix Failing Tests

### Category 1: Splunk Connection-Dependent Failures
Affected tests (examples):
- test_health_check_before_operations
- test_health_check_success
- test_list_indexes_success
- test_run_oneshot_search_basic
- test_list_apps_success
- All tests asserting on 'status', 'results', etc., but getting {'empty_result': True}

#### Troubleshooting:
- Confirm Splunk is running and accessible (e.g., curl http://localhost:8000).
- Check test fixtures: Ensure `conftest.py` or test setup connects to Splunk properly.
- If connection still fails: Debug `src/client/splunk_client.py` for connection logic; possible config issues (env vars like SPLUNK_HOST, port).

#### Updates:
- Update tests to handle degraded mode: Add assertions for degraded responses or skip if not connected (use pytest.mark.skipif).
- Mock Splunk client for unit tests: Use `unittest.mock` to simulate responses without real connection.
- Do not remove: These test core functionality; fix to make them pass.

### Category 2: Refactoring-Related Errors
Affected: All 14 errors in `tests/test_workflow_runner.py` (AttributeError: module 'src.tools.agents.shared' has no attribute 'tools').

#### Troubleshooting:
- Search codebase: Agents seem moved to `src/tools/agents_backup/` or integrated into `src/tools/workflows/shared/`.
- Check git history: Review commits for agent refactoring (e.g., AGENTS_REMOVAL_SUMMARY.md was deleted, indicating removal).

#### Updates:
- Update imports: Change to `src.tools.workflows.shared` or equivalent.
- Refactor tests: Align with new workflow structure (e.g., use `workflow_manager` instead of old agent tools).
- If agents were removed: Consider removing these tests if functionality is deprecated, or migrate to test workflow equivalents.
- Priority: High – These are errors, not failures; fix to unblock suite.

### Category 3: Assertion Mismatches
Affected:
- contrib/health/test_get_degraded_splunk_features.py: Description mismatch (expected vs. actual tool description).

#### Troubleshooting:
- Compare expected vs. actual: The actual has more details; possibly updated in code.
- Check source: Look in `contrib/tools/health/get_degraded_splunk_features.py` for description.

#### Updates:
- Update expected string in test to match current description.
- Do not remove: Keeps test relevant.

### Category 4: TypeErrors in Comprehensive Tests
Affected: ~10 tests in `test_mcp_server_comprehensive.py` (e.g., 'CallToolResult' object is not subscriptable).

#### Troubleshooting:
- Inspect code: Likely treating a result object as a dict; check how `CallToolResult` is used/returned.
- Possible change: Recent updates to tool calling/return types.

#### Updates:
- Modify assertions: Use object attributes (e.g., result.data['status']) instead of subscripting.
- Add type checks: Ensure responses are dicts before asserting.
- Do not remove: These are integration tests; critical for coverage.

## Step 3: General Improvements
- Reduce warnings: Investigate overwriting registrations; possibly refactor registry to avoid duplicates.
- Add test categories: Mark tests as unit/integration/Splunk-dependent for selective running.
- Coverage: After fixes, run with `--cov` to ensure >80% coverage; add tests for new features.
- Removal criteria: Only remove if functionality is deprecated (e.g., old agent tests); document in changelog.

## Step 4: CI/CD Integration and Quality Checks
To ensure ongoing test reliability and code quality, integrate GitHub Actions for automated testing and linting. Start with basic test running on push, then expand to include linting and pre-commits.

### Actions:
- Create GitHub Workflow: Add `.github/workflows/test.yml` for running on push and pull requests.
  - Steps:
    - Checkout code.
    - Set up Python and uv.
    - Install dependencies: `uv sync --dev`.
    - Run linting: `uv run ruff check .` and `uv run mypy .` (fix any issues found).
    - Run tests: Use `make test-with-splunk` (from Step 1) or directly `uv run pytest tests/ -v` with Splunk service in workflow (use Docker Compose as a service).
  - Handle Splunk: Define a service in the workflow to start Splunk container for integration tests.
- Add Pre-Commit Hooks: Install pre-commit and add `.pre-commit-config.yaml` with hooks for Ruff, Black, mypy, and trailing whitespace checks. Run `pre-commit install` locally.
- Scope: This is in scope as it prevents regressions and enforces quality post-fixes.
- Retest: After implementation, push a test commit to verify the workflow runs successfully.

### Expected Impact:
- Automates verification, catches issues early, and ensures the project remains in working state.

## Timeline
1. Day 1: Fix environment (Splunk setup), retest.
2. Day 2: Fix refactoring errors and TypeErrors.
3. Day 3: Address mismatches, clean warnings, final run.

## Verification
- Run `make test` after each step; aim for 0 failures/errors.
- If blocked (e.g., persistent connection issues), document and seek user input.
