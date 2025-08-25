# AI Workflows Hands‑On Lab

Accelerate your understanding of MCP Server for Splunk by creating a custom tool and, optionally, building an AI-powered troubleshooting workflow.
This instruction has been tailored for an supervised lab, for full documentation, see [README.md](README.md).

## Objectives
This lab is split into three parts for new users
1. **Set up the project**
   - Set up the project and run the server
3. **Create a custom tool**
   - Create a custom Splunk tool using helper scripts (beginner-friendly)
   - Validate and run your tool in MCP Inspector
4. **Create and run a workflow** *(Extra)*
   - Generate a workflow, include your tool, validate, and execute it

---

## Part 1 — Set up the project (🔧)

Prepare your environment and to run the mcp server.

### Prerequisites

- Python 3.10+ and UV package manager
- Splunk test instance will be provided to you by email, let the instructor know if you haven't received an email.

### Clone Github Repository

```bash
git clone https://github.com/deslicer/mcp-for-splunk.git
cd mcp-for-splunk
# Checkout dev1666 branch in git, this branch has a prepared .env file for you.
git checkout dev1666
```

### Option 1 - Local Service - Recommended
```bash
# Start the uv application using command line
# Linux/MacOS
./scripts/build_and_run.sh --local

# Windows Powershell
./scripts/build_and_run.ps1 --local

# Windows
./scripts/build_and_run.bat --local
```

### Option 2 - Docker Solution - Optional
*This warning shall be ignored at this time*
  - WARN[0000] The "OPENAI_API_KEY" variable is not set. Defaulting to a blank string.
```bash
# Ensure that Docker Desktop is started on your laptop
docker ps
# Download and build the MCP server using Docker
# Linux/MacOS
./scripts/build_and_run.sh --docker
# To stop the containers
./scripts/build_and_run.sh --stop

# Windows Powershell
./scripts/build_and_run.ps1 --docker

# Windows
./scripts/build_and_run.bat --docker
```


### MCP Inspector

- Open `http://localhost:6274`

- Click Connect to browse and run tools

![MCP server connect](/media/mcp_server_connect.png)

## Part 1 - Verification - Local Service
1. Connect and list `server_info` resource.
2. After you have connected to the MCP server, click the
`server_info` in the **Resources** column.
3. To the right, the response message from `server_inf` is displayed.

4. Click on the green text in text: value field.

If you see ```"status":"running"``` in the text you have complete **Part 1** ✅


![MCP server connect](/media/mcp_server_connect_docker.png)

## Part 1 - Verification - Docker Solution
1. Connect and list `server_info` resource.
2. After you have connected to the MCP server, click the
`server_info` in the **Resources** column.
3. To the right, the response message from `server_inf` is displayed.

4. Click on the green text in text: value field.

If you see ```"status":"running"``` in the text you have complete **Part 1** ✅



---

## Part 2 — Create a custom tool (🧩)

Build your first tool with the generator, validate it, and run it in MCP Inspector.

### 1. Generate a tool with the helper script (🚀)

```bash
# Interactive generator (recommended)
./contrib/scripts/generate_tool.py
```

When prompted:

- Select the template: choose either the simple example or the Splunk Search template
- Choose a category: for example `devops` or `examples`
- Provide a tool name: for example `hello_world` or `basic_health_search`

The generator creates files under `contrib/tools/<category>/` and includes boilerplate with `BaseTool`, `ToolMetadata`, and an `execute` method. It may also add starter tests under `tests/contrib/` depending on the template.

Helpful reference: see the contributor guide at `contrib/README.md` and the Tool Development Guide at `docs/contrib/tool_development.md`.

### 2. Understand the tool structure (quick tour)

- Your class inherits from `BaseTool`
- Metadata lives in `METADATA = ToolMetadata(...)`
- Main logic goes in `async def execute(self, ctx: Context, **kwargs)`

Example minimal tool structure:

```python
from typing import Any, Dict
from fastmcp import Context
from src.core.base import BaseTool, ToolMetadata

class HelloWorldTool(BaseTool):
    """A simple example tool that returns a greeting."""

    METADATA = ToolMetadata(
        name="hello_world",
        description="Say hello to someone",
        category="examples",
        tags=["example", "tutorial"],
        requires_connection=False
    )

    async def execute(self, ctx: Context, name: str = "World") -> Dict[str, Any]:
        message = f"Hello, {name}!"
        return self.format_success_response({"message": message})
```

For Splunk-backed tools, set `requires_connection=True` and use `await self.get_splunk_service(ctx)` inside `execute`.

### 3. Validate the tool (🔎)

```bash
# Validate your tool for structure and metadata
./contrib/scripts/validate_tools.py contrib/tools/<category>/<your_tool>.py

# Optional: run contrib tests
./contrib/scripts/test_contrib.py
```

Expected output includes a success message or specific actionable validation errors to fix.

### 4. Run the tool in MCP Inspector (🖥️)

With the server running (`docker compose up -d` or `./scripts/build_and_run.sh`), open MCP Inspector and:

- Select your tool by its `METADATA.name` (for example `hello_world`)
- Provide parameters (for example `{ "name": "Splunk" }`)
- Click Run and review the formatted result

For Splunk tools, verify your `.env` connection settings. If you see connection errors, confirm `MCP_SPLUNK_HOST`, `MCP_SPLUNK_USERNAME`, and `MCP_SPLUNK_PASSWORD` are set and the Splunk instance is reachable.

### 5. Troubleshooting your tool

- Missing tool in Inspector: ensure the file is under `contrib/tools/<category>/` and the class inherits `BaseTool`
- Validation errors: re-run the validator for precise hints
- Splunk errors: verify credentials and try a simple search first

---

## Part 3 — (Extra) Create and run a workflow (🚀)

Use the workflow utilities to list workflows, generate a template, include your tool, validate it, and execute the workflow in MCP Inspector.

### Before you start

Workflows use AI models and require an OpenAI key.

```bash
# In your .env (add now if you skipped earlier)
OPENAI_API_KEY=sk-...
```

### A. Discover available workflows (📚)

Use the `list_workflows` tool to see core and contrib workflows.

```python
from fastmcp import Context
from src.tools.workflows.list_workflows import create_list_workflows_tool

# Assume you have an async FastMCP Context named ctx
lister = create_list_workflows_tool()
result = await lister.execute(ctx, format_type="summary")
print(result)
```

In MCP Inspector:

- Select tool: `list_workflows`
- Params: `{ "format_type": "summary" }`
- Run and note `workflow_id` values you can execute

### B. Get workflow requirements and schema (🔎)

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

### C. Generate a workflow template and include your tool (🧪)

```python
from src.tools.workflows.workflow_builder import WorkflowBuilderTool

builder = WorkflowBuilderTool("workflow_builder", "workflows")
tmpl = await builder.execute(ctx, mode="template", template_type="minimal")

template = tmpl["result"]["template"]
template["workflow_id"] = "custom_health_check"
template["name"] = "Custom Health Check"
template["description"] = "Basic Splunk health verification"

# Reference your tool so it’s available to tasks
template["required_tools"] = ["hello_world"]  # replace with your tool name

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

### D. Run your workflow (end-to-end)

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

### E. MCP Inspector track (no-code)

You can do Part 2 entirely in MCP Inspector:

- `workflow_requirements` → `{ "format_type": "quick" }`
- `workflow_builder` → `{ "mode": "template", "template_type": "minimal" }`
- Copy the template JSON, edit fields, then validate with `workflow_builder` → `{ "mode": "validate", "workflow_data": <your JSON> }`
- Save the JSON under `contrib/workflows/<category>/<workflow_id>.json`
- `list_workflows` → confirm presence
- `workflow_runner` → set parameters and execute

---

## Troubleshooting

- Missing OpenAI credentials (for workflows): set `OPENAI_API_KEY` in `.env`
- Splunk connection errors: verify Splunk host/creds or use the Docker Splunk
- Workflow not discovered: ensure file path is `contrib/workflows/<category>/<id>.json` and JSON is valid
- Tool not discovered: confirm it lives under `contrib/tools/<category>/` and defines a `BaseTool` subclass with `METADATA`

---

## Next Steps

- Explore core workflows: `missing_data_troubleshooting`, `performance_analysis`
- Build domain-specific workflows for your org (security, data quality, performance)
- Contribute your workflows and tools via PRs

Related docs: [Workflows Guide](../guides/workflows/README.md), [Workflow Runner Guide](../guides/workflows/workflow_runner_guide.md), [Agent Tracing (legacy)](../guides/workflows/agent-tracing-guide.md), [Tool Development Guide](../contrib/tool_development.md), [Contrib Guide](../contrib/contributing.md).
