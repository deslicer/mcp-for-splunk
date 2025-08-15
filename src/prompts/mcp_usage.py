import logging
from typing import Any

from fastmcp import Context

from src.core.base import BasePrompt, PromptMetadata


logger = logging.getLogger(__name__)


class MCPOverviewPrompt(BasePrompt):
    METADATA = PromptMetadata(
        name="mcp_overview",
        description="Generate an overview of MCP server capabilities",
        category="mcp_usage",
        tags=["mcp", "overview", "guide"],
        arguments=[
            {
                "name": "detail_level",
                "description": "Level of detail: basic, intermediate, advanced",
                "required": False,
                "type": "string",
            }
        ],
    )

    async def get_prompt(
        self,
        ctx: Context,
        detail_level: str = "basic",
    ) -> dict[str, Any]:
        if detail_level not in ["basic", "intermediate", "advanced"]:
            detail_level = "basic"

        if detail_level == "basic":
            content = """# MCP Server Overview (Basic)

MCP Server for Splunk is an AI-powered troubleshooting system.

Key Features:
- Intelligent workflows for common issues
- Parallel task execution
- Integration with Splunk tools
- Custom workflow support"""
        elif detail_level == "intermediate":
            content = """# MCP Server Overview (Intermediate)

... more details ..."""
        else:
            content = """# MCP Server Overview (Advanced)

... comprehensive details ..."""

        return {"role": "assistant", "content": [{"type": "text", "text": content}]}


class WorkflowCreationPrompt(BasePrompt):
    METADATA = PromptMetadata(
        name="workflow_creation_guide",
        description="Guide for creating custom workflows",
        category="mcp_usage",
        tags=["workflow", "creation", "guide"],
        arguments=[
            {
                "name": "workflow_type",
                "description": "Type of workflow (e.g., security, performance)",
                "required": False,
                "type": "string",
            },
            {
                "name": "complexity",
                "description": "Complexity level: simple, advanced",
                "required": False,
                "type": "string",
            }
        ],
    )

    async def get_prompt(
        self,
        ctx: Context,
        workflow_type: str = "general",
        complexity: str = "simple",
    ) -> dict[str, Any]:
        content = f"""# Workflow Creation Guide ({complexity.capitalize()} - {workflow_type.capitalize()})

This guide walks you through creating custom workflows for MCP Server. Workflows are JSON-defined procedures executed by AI agents for Splunk troubleshooting.

## 1. List Existing Workflows
Use the `list_workflows` tool to discover available workflows (core and contrib).

**Parameters:**
- format_type: "detailed" (default), "summary", "ids_only", "by_category"
- include_core: bool (default: True)
- include_contrib: bool (default: True)
- category_filter: str (optional)

**Example Usage:**
```python
result = await list_workflows.execute(
    ctx=ctx,
    format_type="summary",
    category_filter="{workflow_type}"
)
```

**What to Do Next:** Review existing workflows to avoid duplication.

## 2. Get Workflow Requirements Schema
Use the `workflow_requirements` tool for schema, tools, and guidelines.

**Parameters:**
- format_type: "detailed" (default), "schema", "quick", "examples"

**Example Usage:**
```python
requirements = await workflow_requirements.execute(
    ctx=ctx,
    format_type="detailed"
)
```

**What to Do Next:** Use the schema to structure your JSON.

## 3. Build Your Workflow
Use the `workflow_builder` tool to create/edit/validate workflows.

**Modes:**
- create: Interactive creation
- edit: Modify existing
- validate: Check structure
- template: Generate starter
- process: Validate finished workflow

**Example Usage (Template Mode):**
```python
template = await workflow_builder.execute(
    ctx=ctx,
    mode="template",
    template_type="{workflow_type}"
)
```

**Example Usage (Process Mode):**
```python
processed = await workflow_builder.execute(
    ctx=ctx,
    mode="process",
    workflow_data=your_workflow_json
)
```

**What to Do Next:** Save validated JSON to contrib/workflows/<category>/<workflow_id>.json

## 4. Run Your Workflow
Use the `workflow_runner` tool to execute workflows.

**Parameters:**
- workflow_id: Required ID
- problem_description: Optional issue description
- earliest_time/latest_time: Time range
- focus_index/host/sourcetype: Optional focus
- complexity_level: "basic", "moderate", "advanced"
- enable_summarization: bool (default: True)

**Example Usage:**
```python
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="your_workflow_id",
    problem_description="Test run",
    earliest_time="-24h",
    latest_time="now"
)
```

**Tips for {workflow_type.capitalize()} Workflows:**
- Use relevant tools like run_splunk_search
- Add dependencies for sequential execution
- Include context vars like focus_index

{'Advanced Tips' if complexity == 'advanced' else ''}:
- Use parallel tasks (no dependencies)
- Add custom context in default_context
- Optimize searches for performance"""

        return {"role": "assistant", "content": [{"type": "text", "text": content}]}


class ToolUsagePrompt(BasePrompt):
    METADATA = PromptMetadata(
        name="tool_usage_guide",
        description="Guide for using specific MCP tools",
        category="mcp_usage",
        tags=["tool", "usage", "guide"],
        arguments=[
            {
                "name": "tool_name",
                "description": "Name of the tool (e.g., workflow_runner)",
                "required": True,
                "type": "string",
            },
            {
                "name": "scenario",
                "description": "Specific usage scenario",
                "required": False,
                "type": "string",
            }
        ],
    )

    async def get_prompt(
        self,
        ctx: Context,
        tool_name: str,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        content = f"""# Usage Guide for {tool_name}

How to use the {tool_name} tool.

Parameters:
- workflow_id: Required ID of workflow

Example:
result = await {tool_name}.execute(ctx, workflow_id="example")"""

        if scenario:
            content += f"\n\nScenario: {scenario}\nCustomized example..."""

        return {"role": "assistant", "content": [{"type": "text", "text": content}]}

