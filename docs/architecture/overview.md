# MCP Server for Splunk – Architecture Overview

## High-level architecture

The MCP Server for Splunk is a modular system that exposes Splunk capabilities to LLMs through the Model Context Protocol (MCP). It organizes code into clear subsystems for maintainability and extensibility:

- **Core framework (`src/core/`)**: Base abstractions, registries, discovery/loading, context handling, client identity, and enhanced config extraction.
- **Tools (`src/tools/`)**: Actionable operations (search, metadata, admin, health, KV Store, workflows).
- **Resources (`src/resources/`)**: Read-only, URI-addressable data for context (Splunk documentation, configuration, health, search results).
- **Workflows (`src/tools/workflows/`)**: Dependency-aware diagnostic workflows and supporting utilities.
- **Client connectivity (`src/client/`)**: Splunk SDK wrapper and connection helpers.
- **Routes/UI (`src/routes/`)**: Lightweight HTTP status pages and assets.
- **Prompts (`src/prompts/`)**: Prompt assets for agents.
- **Contrib (`contrib/`)**: Community extensions with examples and validation.

## Current directory structure (trimmed)

```text
mcp-server-for-splunk/
├─ src/
│  ├─ server.py
│  ├─ core/
│  │  ├─ base.py
│  │  ├─ registry.py
│  │  ├─ discovery.py
│  │  ├─ loader.py
│  │  ├─ context.py
│  │  ├─ shared_context.py
│  │  ├─ client_identity.py
│  │  ├─ enhanced_config_extractor.py
│  │  └─ utils.py
│  ├─ client/
│  │  └─ splunk_client.py
│  ├─ routes/
│  │  ├─ health.py
│  │  ├─ templates/health.html
│  │  └─ static/health.css
│  ├─ resources/
│  │  ├─ base.py
│  │  ├─ splunk_docs.py
│  │  └─ splunk_config.py
│  ├─ tools/
│  │  ├─ admin/ apps.py users.py config.py tool_enhancer.py
│  │  ├─ alerts/ alerts.py
│  │  ├─ health/ status.py
│  │  ├─ kvstore/ collections.py data.py
│  │  ├─ metadata/ indexes.py sources.py sourcetypes.py get_metadata.py
│  │  ├─ search/ oneshot_search.py job_search.py saved_search_tools.py
│  │  └─ workflows/
│  │     ├─ core/*.json
│  │     ├─ shared/ dynamic_agent.py parallel_executor.py workflow_manager.py retry.py tools.py
│  │     ├─ list_workflows.py workflow_builder.py workflow_runner.py summarization_tool.py workflow_requirements.py
│  │     └─ core/*.json
│  └─ prompts/
└─ contrib/
```

## Core components

- **Base & registry**: `src/core/base.py` defines base classes; `src/core/registry.py` manages registration and discovery.
- **Discovery & loader**: `src/core/discovery.py` and `src/core/loader.py` implement dynamic capability loading.
- **Shared context**: `src/core/context.py` and `src/core/shared_context.py` provide request/session context.
- **Client identity & config**: `src/core/client_identity.py` and `src/core/enhanced_config_extractor.py` secure per-client Splunk connections.

## Resources subsystem

Resources are read-only and often client-scoped:

- **Splunk documentation**: `splunk-docs://...` URIs (cheat sheet, SPL reference, admin, troubleshooting) via `src/resources/splunk_docs.py` with HTML processing.
- **Splunk runtime**: Configuration (`splunk://config/{config_file}`), health, apps, indexes, saved searches, and recent search results via `src/resources/splunk_config.py`.
- **Registration**: `src/resources/__init__.py` registers all resource types at import.
- **Security**: Client isolation and helpful error payloads guide credentials when missing.

See the **Resources Reference**: [../reference/resources.md](../reference/resources.md)

## Tools subsystem

Tools implement actions and integrate with Splunk APIs:

- Search, metadata, admin, health, KV Store, and workflow orchestration utilities under `src/tools/`.

See the **Tools Reference**: [../reference/tools.md](../reference/tools.md)

## Workflows subsystem

- **Definitions**: JSON workflows under `src/tools/workflows/core/` and contrib workflows.
- **Execution**: `workflow_runner.py` with `shared/parallel_executor.py`, retry/backoff, summarization, and dynamic agent integration.

Read more:
- [../guides/workflows/workflows-overview.md](../guides/workflows/workflows-overview.md)
- [../guides/workflows/workflow_runner_guide.md](../guides/workflows/workflow_runner_guide.md)

## Request flow (simplified)

1. Client invokes a tool (`tools/call`) or reads a resource (`resources/read`).
2. Server extracts Splunk credentials (headers or environment), builds/uses a client-scoped connection, and validates access.
3. Tools perform actions; resources return read-only content.
4. Results serialize with appropriate content types (e.g., `application/json`, `text/markdown`).

## Multi-tenant security & isolation

- **Client identity**: Deterministic, non-sensitive identifiers enforce isolation and auditing.
- **URI validation**: Resource URIs must match the active client scope.
- **Helpful errors**: Resources return actionable guidance when configuration is missing.

## Testing & operations

- **Tests**: See `tests/` and [../guides/TESTING.md](../guides/TESTING.md). Use scripts in `scripts/` for CI-like runs.
- **Health route**: `src/routes/health.py` renders `routes/templates/health.html` with `routes/static/health.css`.

## Extensibility

- **Add tools**: Implement under `src/tools/<category>/` and follow project conventions.
- **Add resources**: Implement under `src/resources/` and register with the registry.
- **Add workflows**: Contribute definitions and shared utilities under `src/tools/workflows/`.

## Related documentation

- **Tools Reference**: [../reference/tools.md](../reference/tools.md)
- **Resources Reference**: [../reference/resources.md](../reference/resources.md)
- **Workflows Overview**: [../guides/workflows/workflows-overview.md](../guides/workflows/workflows-overview.md)
- **Integration Guide**: [../guides/integration/README.md](../guides/integration/README.md)
- **Deployment Guides**: [../guides/deployment/README.md](../guides/deployment/README.md)
