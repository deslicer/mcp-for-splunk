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

    async def get_prompt(self, ctx: Context, **kwargs) -> dict[str, Any]:
        detail_level = kwargs.get("detail_level", "basic")
        if detail_level not in ["basic", "intermediate", "advanced"]:
            detail_level = "basic"

        # Anthropic-aligned structure with XML sections and explicit output format
        role = (
            "<role>You are an expert Splunk troubleshooting assistant integrated with MCP Server. "
            "Follow instructions precisely and produce safe, verifiable, and actionable outputs for Splunk workflows.</role>"
        )

        if detail_level == "basic":
            body = (
                "<context>MCP Server for Splunk is an AI-powered troubleshooting system.</context>\n"
                "<instructions>\n"
                "- Be explicit and concise.\n"
                "- Prefer parallel execution for independent steps.\n"
                "- Say \"I don't know\" when context is insufficient.\n"
                "</instructions>\n"
                "<output_format>Return Markdown with: Key features (bulleted), How it works (short), Next steps.</output_format>\n"
            )
        elif detail_level == "intermediate":
            body = (
                "<context>Overview with additional architectural details and workflow lifecycle.</context>\n"
                "<instructions>- Include sections: Components, Workflows, Tools integration.</instructions>\n"
                "<output_format>Markdown sections with concise bullets.</output_format>\n"
            )
        else:
            body = (
                "<context>Comprehensive view covering component loaders, tool registry, resources, prompts, and workflow engine.</context>\n"
                "<instructions>- Include validation, error handling, and hot-reload capabilities.</instructions>\n"
                "<output_format>Structured Markdown with headings and short lists.</output_format>\n"
            )

        content = f"{role}\n{body}"
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

    async def get_prompt(self, ctx: Context, **kwargs) -> dict[str, Any]:
        workflow_type: str = kwargs.get("workflow_type", "general")
        complexity: str = kwargs.get("complexity", "simple")
        # Anthropic-aligned XML prompt with explicit instructions and output format
        content = f"""
<role>You are a workflow authoring assistant for MCP Server for Splunk.</role>
<context>Target workflow type: {workflow_type}. Complexity: {complexity}.</context>
<instructions>
- Be explicit and concise; return only the requested sections.
- Prefer parallel tasks when independent; use dependencies for sequencing.
- Provide realistic examples, no placeholders like foo/bar.
- Say "I don't know" if information is insufficient.
</instructions>
<examples>
<example>
Input: template request for performance
Output: minimal JSON template with one task and validation notes
</example>
</examples>
<output_format>Return Markdown with sections: 1) Steps 2) Examples (fenced code) 3) Next actions.</output_format>

### Steps
1. List existing workflows with `list_workflows` (filters optional).
2. Fetch requirements via `workflow_requirements` (schema or detailed).
3. Build with `workflow_builder` in template/process mode.
4. Run with `workflow_runner` and validate outputs.

### Examples
```python
template = await workflow_builder.execute(ctx=ctx, mode="template", template_type="{workflow_type}")
```
```python
processed = await workflow_builder.execute(ctx=ctx, mode="process", workflow_data=your_workflow_json)
```
```python
result = await workflow_runner.execute(ctx=ctx, workflow_id="your_workflow_id", earliest_time="-24h", latest_time="now")
```

### Tips
- Use parallel tasks for independent analysis.
- Include `focus_index` or `focus_host` when applicable.
- Optimize SPL for performance.
"""

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

    async def get_prompt(self, ctx: Context, **kwargs) -> dict[str, Any]:
        tool_name: str = kwargs.get("tool_name", "tool")
        scenario: str | None = kwargs.get("scenario")
        # Anthropic-aligned parameters and output format with XML sections
        content = f"""
<role>You are a precise MCP tool usage guide generator.</role>
<context>Tool: {tool_name}. Scenario: {scenario or 'general'}.</context>
<instructions>
- Output must include parameters, example calls, and expected outputs.
- Be concise and avoid placeholders; prefer realistic values.
</instructions>
<output_format>Markdown with sections: Parameters, Example, Notes.</output_format>

### Parameters
- Describe required and optional arguments for `{tool_name}`.

### Example
```python
result = await {tool_name}.execute(ctx, workflow_id="example")
```

### Notes
- Prefer parallel execution for independent operations.
- Say "I don't know" if the scenario lacks specifics.
"""

        return {"role": "assistant", "content": [{"type": "text", "text": content}]}

