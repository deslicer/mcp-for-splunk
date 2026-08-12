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

## Part 3 — (Extra) Author a workflow definition (🚀)

Use the workflow tools to list workflows, generate a template, include your tool, and validate JSON in MCP Inspector. Built-in OpenAI `workflow_runner` execution was removed — orchestrate task tools from your MCP client.

### A. Discover available workflows (📚)

In MCP Inspector:

- Select tool: `list_workflows`
- Params: `{ "format_type": "summary" }`
- Run and note `workflow_id` values

### B. Get workflow requirements and schema (🔎)

- `workflow_requirements` → `{ "format_type": "quick" }` or `{ "format_type": "schema" }`

Key takeaways:

- Required fields: `workflow_id`, `name`, `description`, `tasks`
- Tasks include `task_id`, `name`, `description`, `instructions`
- Optional fields: `required_tools`, `dependencies`, `context_requirements`

### C. Generate and validate a template (🧪)

- `workflow_builder` → `{ "mode": "template", "template_type": "minimal" }`
- Edit the JSON (`workflow_id`, `required_tools`, task instructions)
- Validate with `workflow_builder` → `{ "mode": "validate", "workflow_data": <your JSON> }`
- Save under `contrib/workflows/<category>/<workflow_id>.json`
- Re-run `list_workflows` to confirm discovery

### D. MCP Inspector track (no-code)

- `workflow_requirements` → `{ "format_type": "quick" }`
- `workflow_builder` → template / validate
- Call the Splunk tools referenced by your tasks directly (for example `get_splunk_health`, `run_oneshot_search`)

---

## Troubleshooting

- Splunk connection errors: verify Splunk host/creds or use the Docker Splunk
- Workflow not discovered: ensure file path is `contrib/workflows/<category>/<id>.json` and JSON is valid
- Tool not discovered: confirm it lives under `contrib/tools/<category>/` and defines a `BaseTool` subclass with `METADATA`

---

## Next Steps

- Explore core workflows: `missing_data_troubleshooting`, `performance_analysis`
- Build domain-specific workflows for your org (security, data quality, performance)
- Contribute your workflows and tools via PRs

Related docs: [Workflows Guide](../guides/workflows/README.md), [Tool Development Guide](../contrib/tool_development.md), [Contrib Guide](../contrib/contributing.md).