# Create your custom MCP tool (🧩)

Build your first tool with the generator, validate it, and run it in MCP Inspector.

> This lab is Part 2 only. If you haven’t completed Part 1 (server setup), finish that first so your environment and MCP server are ready.

## 1. Generate a tool with the helper script (🚀)

```bash
# Interactive generator (recommended)
uv run python ./contrib/scripts/generate_tool.py
```

### 1.1 Answer the prompts

- Select the template: choose either the simple example or the Splunk Search template
- Choose a category: for example `devops` or `examples`
- Provide a tool name: for example `hello_world` or `basic_health_search`

The generator creates files under `contrib/tools/<category>/` and includes boilerplate with `BaseTool`, `ToolMetadata`, and an `execute` method. It may also add starter tests under `tests/contrib/` depending on the template.

Helpful reference:
- Contributor guide: `contrib/README.md`
- Tool Development Guide: `docs/contrib/tool_development.md`

## 2. Understand the tool structure (quick tour)

- Your class inherits from `BaseTool`
- Metadata lives in `METADATA = ToolMetadata(...)`
- Main logic goes in `async def execute(self, ctx: Context, **kwargs)`

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

- For Splunk-backed tools, set `requires_connection=True` and use `await self.get_splunk_service(ctx)` inside `execute`.

## 3. Validate the tool (🔎)

```bash
# Validate your tool for structure and metadata
uv run python ./contrib/scripts/validate_tools.py contrib/tools/<category>/<your_tool>.py

# Optional: run contrib tests
uv run python ./contrib/scripts/test_contrib.py
```

Expected output includes a success message or specific actionable validation errors to fix.

## 4. Run the tool in MCP Inspector (🖥️)

With the server running (`docker compose up -d` or `./scripts/build_and_run.sh`):

- Open MCP Inspector at `http://localhost:6274`
- Select your tool by its `METADATA.name` (for example `hello_world`)
- Provide parameters (for example `{ "name": "Splunk" }`)
- Click Run and review the formatted result

For Splunk tools, verify your `.env` connection settings. If you see connection errors, confirm `MCP_SPLUNK_HOST`, `MCP_SPLUNK_USERNAME`, and `MCP_SPLUNK_PASSWORD` are set and the Splunk instance is reachable.

## 5. Troubleshooting your tool

- Missing tool in Inspector: ensure the file is under `contrib/tools/<category>/` and the class inherits `BaseTool`
- Validation errors: re-run the validator for precise hints
- Splunk errors: verify credentials and try a simple search first

---

### Teaser: Part 3 — Create and run a workflow

If you have extra time, try Part 3: build and execute a workflow using the workflow tools. You can discover available workflows and run them with parameters, then review results in MCP Inspector. See: [Hands-on Lab — Part 3 (Create and run a workflow)](https://github.com/deslicer/mcp-for-splunk/blob/main/docs/labs/hands-on-lab.md#part-3--extra-create-and-run-a-workflow-).
