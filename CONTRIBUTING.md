# Contributing to MCP Server for Splunk

Thanks for your interest in contributing! Please read this guide to get started.

## Code of Conduct

By participating, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

1. Fork and clone the repository
2. Install uv and Python 3.10+
3. Sync dependencies: `uv sync --dev`
4. Run tests: `uv run pytest -q`
5. Lint/types: `uv run ruff check` and `uv run mypy`

## Submitting Changes

1. Create a feature branch
2. Add tests and docs
3. Ensure CI passes locally
4. Open a PR using the template

## Reporting Issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`.


