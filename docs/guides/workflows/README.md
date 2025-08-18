# Workflows Guide

## Overview

Workflows in MCP Server for Splunk enable automated troubleshooting and validation using JSON-defined tasks executed by dependency-aware parallel micro-agents.

### Core Workflows

- missing_data_troubleshooting
- performance_analysis

### Contrib Workflows

User/custom workflows live under `contrib/workflows/` by category (e.g., `security/`, `performance/`, `examples/`). They are auto-discovered and validated at startup.

## Discovering Workflows (📚)

Use the `list_workflows` tool to see available workflow IDs from both core and contrib sources.

Example call (client side):

```python
result = await list_workflows.execute(ctx, format_type="summary")
print(result)
```

## Executing Workflows (🚀)

Run workflows by ID using the `workflow_runner` tool. Provide time range and optional focus context.

Example call:

```python
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="simple_health_check",  # or missing_data_troubleshooting, performance_analysis
    earliest_time="-24h",
    latest_time="now",
    focus_index=None,
    complexity_level="moderate",
    enable_summarization=True,
)
```

The runner reports frequent progress updates to avoid client timeouts and returns structured results with execution metrics.

## Creating Workflows (🔧)

Workflows are JSON files following the WorkflowDefinition schema. A minimal example:

```json
{
  "workflow_id": "simple_health_check",
  "name": "Simple Health Check",
  "description": "Basic Splunk health verification workflow",
  "tasks": [
    {
      "task_id": "server_health_check",
      "name": "Server Health Check",
      "description": "Check Splunk server health and connectivity",
      "instructions": "Execute health check using get_splunk_health tool and summarize findings.",
      "required_tools": ["get_splunk_health"],
      "dependencies": [],
      "context_requirements": []
    }
  ]
}
```

Place contrib workflows at: `contrib/workflows/<category>/<workflow_id>.json`

## Validation (✅)

- JSON Schema: use the schema returned by `workflow_requirements` with `format_type="schema"`.
- Loader validation: contrib loader validates during discovery; errors surface in logs and via the `list_workflows` output.

## Examples (📎)

See `examples/workflow_runner_demo.py` for a working client that loads `.env` and invokes the server using a real FastMCP client.

## Hands‑On Lab (🧪)

Start here for a guided, end-to-end experience creating and running your own workflow:

- See: [AI Workflows Hands‑On Lab](../../labs/hands-on-lab.md)

## Quick Start (🚀)

1. Prepare environment
   - Copy `.env.example` to `.env` and set `OPENAI_API_KEY`
   - Start the server (Docker recommended): `docker compose up -d`
2. Discover workflows
   - Call `list_workflows` to view available IDs (core + contrib)
3. Run a workflow
   - Use `workflow_runner` with a workflow ID, e.g. `simple_health_check`

Example (Python):

```python
from src.tools.workflows.list_workflows import create_list_workflows_tool
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

# Assume you have an async FastMCP Context named ctx
lister = create_list_workflows_tool()
workflows = await lister.execute(ctx, format_type="summary")

runner = WorkflowRunnerTool("workflow_runner", "workflows")
result = await runner.execute(
    ctx=ctx,
    workflow_id="simple_health_check",
    earliest_time="-24h",
    latest_time="now",
    complexity_level="moderate",
)
print(result["status"], result["workflow_name"])  # e.g., completed Simple Health Check
```
