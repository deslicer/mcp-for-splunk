# Workflows Overview

## Status

OpenAI Agents `workflow_runner` execution was **removed** (Option C) as part of the FastMCP 4 / MCP SDK v2 upgrade. Workflow JSON definitions remain for discovery, authoring, and external orchestration.

## What still ships

- `list_workflows` — discover core + contrib workflow IDs
- `workflow_requirements` — schema and authoring rules
- `workflow_builder` — create, edit, validate, and process workflow JSON

## Typical flow

1. Call `list_workflows` to discover IDs.
2. Call `workflow_requirements` for schema details.
3. Use `workflow_builder` (`template` → `process` → `validate`).
4. Save under `contrib/workflows/<category>/<workflow_id>.json`.
5. Orchestrate task tools from your MCP client or agent (no built-in runner).

## Where workflows live

- Core: `src/tools/workflows/core/`
- Contrib: `contrib/workflows/<category>/<workflow_id>.json`

## Related docs

- [Workflows Guide](README.md)
- Legacy runner notes below remain only for historical reference; do not use them on current builds

## Legacy (removed)

Documents such as `workflow_runner_guide.md`, `openai-agent-integration.md`, and `agent-tracing-guide.md` describe the removed OpenAI Agents execution path. They are kept for migration context only.
