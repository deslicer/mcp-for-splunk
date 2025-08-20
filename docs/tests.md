# Tests Quick Start

Get your first green run in minutes. This guide covers the fastest way to run tests locally and, optionally, against the bundled Splunk container.

## Prerequisites

- Python 3.10+ and the `uv` package manager
- Docker (optional, required only for the Splunk container scenario)

## Run the Test Suite (fast path)

```bash
uv run pytest -q
```

You'll see a concise summary of passing tests. This is the quickest way to validate your environment.

## Run With Splunk Container

Use this when you want tests that interact with a live Splunk instance:

```bash
make test-with-splunk
```

This will:
- Start the Splunk container from `docker-compose-splunk.yml`
- Wait for Splunk to become ready (up to ~5 minutes)
- Execute the tests against the running Splunk

Note on Splunk licensing: When using the `so1` Splunk container, supply your own Splunk Enterprise license if required. The compose files include a commented example mount:
`# - ./lic/splunk.lic:/tmp/license/splunk.lic:ro`. Create a `lic/` directory and mount your license file, or add the license via the Splunk Web UI after startup.

## Useful Make Targets

```bash
# All tests (verbose)
make test

# Fast subset (skips tests marked slow)
make test-fast

# Unit-only / integration-only
make test-unit
make test-integration

# Full suite with coverage report
make test-all

# Quick health checks
make test-health
```

## Next Steps

- Detailed guidance: [Testing Guide](guides/TESTING.md)
- Install/setup help: [Installation](getting-started/installation.md)
- Docker help: [Docker Deployment](guides/deployment/DOCKER.md)
- Windows-specific steps: [Windows Guide](WINDOWS_GUIDE.md)

## Interactive Testing with MCP Inspector

```bash
open http://localhost:6274  # MCP Inspector web interface
```

1. Ensure that Streamable HTTP is set
2. Update URL from default to: `http://localhost:8001/mcp/` (Docker) or `http://localhost:8002/mcp/` (dev compose)
3. Click "Connect" button at the bottom
4. Test tools and resources interactively


