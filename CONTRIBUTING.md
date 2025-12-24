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

## Releasing

Releases are automated via GitHub Actions when a version tag is pushed.

### Automated (Recommended)

1. Merge a **release-please** PR (auto-created on version-bumping commits)
2. Release-please creates a tag and triggers `.github/workflows/release.yml`
3. Package is built with `uv build` and published to PyPI

### Manual Release

```bash
# Bump version in pyproject.toml, then:
git tag v0.5.0
git push origin v0.5.0
```

### Using as a Dependency

```toml
# In your project's pyproject.toml
dependencies = ["mcp-server-for-splunk>=0.4.0"]

# With optional Sentry monitoring
dependencies = ["mcp-server-for-splunk[sentry]>=0.4.0"]
```

