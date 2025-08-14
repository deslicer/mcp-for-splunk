# AI Workflows Hands‑On Lab

Accelerate your understanding of MCP Server for Splunk by creating tools and building AI-powered troubleshooting workflows. In ~30–45 minutes you will discover workflows, generate a new workflow from templates, validate it, and execute it end-to-end.

## Objectives

- Create a custom Splunk tool (optional but recommended)
- Generate a workflow using workflow tools
- Validate and save the workflow under `contrib/workflows/`
- Execute the workflow with rich parameters and view results

## Prerequisites

- Python 3.10+ and UV
- OPENAI_API_KEY in your environment
- Splunk instance (local/remote) or use the included Docker Splunk

### Setup

```bash
# From repo root
cp env.example .env

# Edit .env and set at least:
# OPENAI_API_KEY=sk-...
# MCP_SPLUNK_HOST, MCP_SPLUNK_USERNAME, MCP_SPLUNK_PASSWORD (or use Docker Splunk)

# Start (Docker recommended)
docker compose up -d

# Or run the helper script
./scripts/build_and_run.sh
```

If you prefer a UI, open MCP Inspector and connect to `http://localhost:8001/mcp/`.

---

## Part 1 — Discover available workflows (📚)

Use the `list_workflows` tool to see core and contrib workflows.

### Via Python (async)

```python
from fastmcp import Context
from src.tools.workflows.list_workflows import create_list_workflows_tool

# Assume you have an async FastMCP Context named ctx
lister = create_list_workflows_tool()
result = await lister.execute(ctx, format_type="summary")
print(result)
```

### Via MCP Inspector

- Select tool: `list_workflows`
- Params: `{ "format_type": "summary" }`
- Run and note `workflow_id` values you can execute

---

## Part 2 — Get workflow requirements and schema (🔎)

Use `workflow_requirements` to understand the schema and available context variables.

```python
from src.tools.workflows.workflow_requirements import WorkflowRequirementsTool

req = WorkflowRequirementsTool("workflow_requirements", "workflows")
schema = await req.execute(ctx, format_type="schema")
quick = await req.execute(ctx, format_type="quick")
```

Key takeaways:

- Required fields: `workflow_id`, `name`, `description`, `tasks`
- Tasks include `task_id`, `name`, `description`, `instructions`
- Optional fields: `required_tools`, `dependencies`, `context_requirements`

---

## Part 3 — Generate a workflow template (🧪)

Use `workflow_builder` to generate a ready-to-edit template. Supported templates: `minimal`, `security`, `performance`, `data_quality`, `parallel`, `sequential`.

```python
from src.tools.workflows.workflow_builder import WorkflowBuilderTool

builder = WorkflowBuilderTool("workflow_builder", "workflows")
tmpl = await builder.execute(ctx, mode="template", template_type="minimal")

template = tmpl["result"]["template"]
template["workflow_id"] = "custom_health_check"
template["name"] = "Custom Health Check"
template["description"] = "Basic Splunk health verification"

# Validate the workflow structure
validation = await builder.execute(ctx, mode="validate", workflow_data=template)
assert validation["status"] == "success"
```

Save it to `contrib/workflows/examples/custom_health_check.json`:

```python
import json, pathlib
pathlib.Path("contrib/workflows/examples").mkdir(parents=True, exist_ok=True)
with open("contrib/workflows/examples/custom_health_check.json", "w") as f:
    json.dump(template, f, indent=2)
```

Re-run discovery to see it listed:

```python
await lister.execute(ctx, format_type="summary")
```

---

## Part 4 — Run your workflow (🚀)

Use `workflow_runner` to execute by `workflow_id` with time and focus context.

```python
from src.tools.workflows.workflow_runner import WorkflowRunnerTool

runner = WorkflowRunnerTool("workflow_runner", "workflows")
result = await runner.execute(
    ctx=ctx,
    workflow_id="custom_health_check",  # or your chosen template id
    problem_description="Validate Splunk health for last 24h",
    earliest_time="-24h",
    latest_time="now",
    complexity_level="moderate",
    enable_summarization=True,
)

print(result["status"])               # expected: "success" or "completed"
print(result.get("workflow_name"))     # human-readable name
```

Tips:

- Set `focus_index`, `focus_host`, or `focus_sourcetype` to scope analysis
- Keep `enable_summarization=True` for executive summaries

---

## Part 5 — Optional: Create a custom tool and use it in a workflow (🧩)

You can generate a Splunk search tool and then reference it in your workflow’s `required_tools`.

```bash
# Interactive generator
./contrib/scripts/generate_tool.py

# The script will create files under contrib/tools/<category>/
```

After generating your tool:

- Add its tool name (from `ToolMetadata.name`) into a task’s `required_tools`
- Validate the workflow again using `workflow_builder` (`mode="validate"`)
- Re-run `list_workflows`, then execute with `workflow_runner`

---

## Part 6 — MCP Inspector track (no-code) (🖥️)

You can do the entire lab in MCP Inspector:

- `workflow_requirements` → `{ "format_type": "quick" }`
- `workflow_builder` → `{ "mode": "template", "template_type": "minimal" }`
- Copy the template JSON, edit fields, then validate with `workflow_builder` → `{ "mode": "validate", "workflow_data": <your JSON> }`
- Save the JSON under `contrib/workflows/<category>/<workflow_id>.json`
- `list_workflows` → confirm presence
- `workflow_runner` → set parameters and execute

---

## Troubleshooting

- Missing OpenAI credentials: set `OPENAI_API_KEY` in `.env`
- Splunk connection errors: verify Splunk host/creds or use the Docker Splunk
- Workflow not discovered: ensure file path is `contrib/workflows/<category>/<id>.json` and JSON is valid

---

## Next Steps

- Explore core workflows: `missing_data_troubleshooting`, `performance_analysis`
- Build domain-specific workflows for your org (security, data quality, performance)
- Contribute your workflows and tools via PRs

Related docs: [Workflows Guide](README.md), [Template Replacement Guide](../template-replacement-guide.md), [Agent Tracing Guide](../agent-tracing-guide.md).
