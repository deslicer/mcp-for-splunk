"""List Workflows Tool

Provides a comprehensive listing of all available workflows from both core (built-in)
and contrib (user-contributed) sources in the MCP Server for Splunk.
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata

from .shared.workflow_catalog import WorkflowCatalog

logger = logging.getLogger(__name__)


class ListWorkflowsTool(BaseTool):
    """
    List Available Workflows Tool.

    This tool provides a comprehensive listing of all available workflows in the
    MCP Server for Splunk system, including both core (built-in) workflows and
    contrib (user-contributed) workflows.

    ## Key Features:
    - **Core Workflows**: Lists built-in workflows like missing_data_troubleshooting and performance_analysis
    - **Contrib Workflows**: Discovers and lists user-contributed workflows from contrib/workflows/
    - **Detailed Information**: Provides workflow metadata including name, description, task count, and dependencies
    - **Categorization**: Groups workflows by source (core vs contrib) and category
    - **Validation Status**: Shows validation status for contrib workflows
    - **Multiple Formats**: Supports different output formats for various use cases

    ## Output Formats:
    - **detailed**: Complete workflow information with descriptions and metadata (default)
    - **summary**: Brief overview with workflow IDs, names, and basic stats
    - **ids_only**: Simple list of workflow IDs for programmatic use
    - **by_category**: Workflows grouped by category (security, performance, etc.)

    ## Workflow Sources:

    ### Core Workflows
    Built-in workflows provided by the system:
    - **missing_data_troubleshooting**: Systematic troubleshooting for missing data issues
    - **performance_analysis**: Comprehensive system performance diagnostics

    ### Contrib Workflows
    User-contributed workflows from contrib/workflows/:
    - Automatically discovered from JSON files
    - Validated against workflow schema
    - Categorized by directory structure (security/, performance/, etc.)

    ## Use Cases:
    - Discovering available troubleshooting workflows
    - Understanding workflow capabilities and requirements
    - Selecting appropriate workflow for specific problems
    - Validating contrib workflow availability
    - Integration with dynamic troubleshoot agent

    ## Integration:
    Workflows listed by this tool can be used with the dynamic troubleshoot agent:
    ```
    await dynamic_troubleshoot_agent.execute(
        ctx=context,
        problem_description="Your issue description",
        workflow_type="workflow_id_from_this_list"
    )
    ```
    """

    METADATA = ToolMetadata(
        name="list_workflows",
        description="""List all available workflows from core and contrib sources.

This tool provides a comprehensive listing of troubleshooting workflows available in the
MCP Server for Splunk system. It discovers and lists both built-in core workflows and
user-contributed workflows from the contrib directory.

## Output Formats:
- **detailed**: Complete workflow information with descriptions and metadata (default)
- **summary**: Brief overview with workflow IDs, names, and basic statistics
- **ids_only**: Simple list of workflow IDs for programmatic use
- **by_category**: Workflows organized by category (security, performance, etc.)

## Workflow Sources:
- **Core Workflows**: Built-in system workflows (missing_data_troubleshooting, performance_analysis)
- **Contrib Workflows**: User-contributed workflows from contrib/workflows/ directory

## Key Information Provided:
- Workflow ID and human-readable name
- Description and purpose of each workflow
- Number of tasks and dependency information
- Source (core vs contrib) and validation status
- Category and organizational information
- Integration instructions for dynamic troubleshoot agent

## When to use
- Use when you need to discover which workflows exist before running one
- Use to filter by category or get just workflow IDs for programmatic selection

## Arguments
- **format_type** (optional): "detailed" (default), "summary", "ids_only", or "by_category"
- **include_core** (optional): Include built-in workflows (default: true)
- **include_contrib** (optional): Include contrib workflows (default: true)
- **category_filter** (optional): Filter by category (e.g., "security", "performance")

## Outputs
- Workflow listings in the requested format, discovery metadata, and category summaries
- Note: Only workflows available in this server are listed (core + any contrib present)

Perfect for discovering available troubleshooting capabilities and selecting the right
workflow for specific Splunk problems.""",
        category="workflows",
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, self.METADATA.description)
        self.category = category

    async def execute(
        self,
        ctx: Context,
        format_type: str = "detailed",
        include_core: bool = True,
        include_contrib: bool = True,
        category_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        List available workflows from core and contrib sources.

        Args:
            format_type: Output format - "detailed", "summary", "ids_only", or "by_category"
            include_core: Whether to include core (built-in) workflows
            include_contrib: Whether to include contrib (user-contributed) workflows
            category_filter: Optional category filter (e.g., "security", "performance")

        Returns:
            Dict containing workflow listings and metadata
        """
        try:
            await ctx.info("🔍 Discovering available workflows...")

            # Collect workflows from both sources
            core_workflows = {}
            contrib_workflows = {}
            discovery_metadata = {
                "core_available": False,
                "contrib_available": False,
                "core_count": 0,
                "contrib_count": 0,
                "errors": [],
                "warnings": [],
            }

            # Discover core workflows
            if include_core:
                try:
                    core_workflows = await self._discover_core_workflows(ctx)
                    discovery_metadata["core_available"] = True
                    discovery_metadata["core_count"] = len(core_workflows)
                    await ctx.info(f"✅ Found {len(core_workflows)} core workflows")
                except Exception as e:
                    error_msg = f"Failed to discover core workflows: {str(e)}"
                    discovery_metadata["errors"].append(error_msg)
                    logger.error(error_msg, exc_info=True)
                    await ctx.error(error_msg)

            # Discover contrib workflows
            if include_contrib:
                try:
                    contrib_workflows = await self._discover_contrib_workflows(ctx)
                    discovery_metadata["contrib_available"] = True
                    discovery_metadata["contrib_count"] = len(contrib_workflows)
                    await ctx.info(f"✅ Found {len(contrib_workflows)} contrib workflows")
                except Exception as e:
                    error_msg = f"Failed to discover contrib workflows: {str(e)}"
                    discovery_metadata["errors"].append(error_msg)
                    logger.error(error_msg, exc_info=True)
                    await ctx.error(error_msg)

            # Combine workflows
            all_workflows = {**core_workflows, **contrib_workflows}

            # Apply category filter if specified
            if category_filter:
                filtered_workflows = {}
                for workflow_id, workflow_info in all_workflows.items():
                    if workflow_info.get("category", "").lower() == category_filter.lower():
                        filtered_workflows[workflow_id] = workflow_info
                all_workflows = filtered_workflows
                await ctx.info(
                    f"🎯 Filtered to {len(all_workflows)} workflows in category '{category_filter}'"
                )

            await ctx.info(f"📊 Total workflows discovered: {len(all_workflows)}")

            # Format output based on requested format
            if format_type == "summary":
                result = self._format_summary(all_workflows, discovery_metadata)
            elif format_type == "ids_only":
                result = self._format_ids_only(all_workflows, discovery_metadata)
            elif format_type == "by_category":
                result = self._format_by_category(all_workflows, discovery_metadata)
            else:  # detailed
                result = self._format_detailed(all_workflows, discovery_metadata)

            await ctx.info("✅ Workflow listing completed successfully")
            return self.format_success_response(result)

        except Exception as e:
            error_msg = f"Failed to list workflows: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await ctx.error(error_msg)
            return self.format_error_response(error_msg)

    def _workflow_entry(
        self, workflow, *, source: str, category: str, file_path: str, validation_status: str
    ) -> dict[str, Any]:
        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "source": source,
            "category": category,
            "task_count": len(workflow.tasks),
            "has_dependencies": any(task.dependencies for task in workflow.tasks),
            "default_context": workflow.default_context or {},
            "tasks": [
                {
                    "task_id": task.task_id,
                    "name": task.name,
                    "description": task.description,
                    "required_tools": task.required_tools,
                    "dependencies": task.dependencies,
                    "context_requirements": task.context_requirements,
                }
                for task in workflow.tasks
            ],
            "validation_status": validation_status,
            "file_path": file_path,
            "execution_note": "OpenAI workflow_runner execution was removed; definitions remain for discovery/validation.",
        }

    async def _discover_core_workflows(self, ctx: Context) -> dict[str, Any]:
        """Discover core (built-in) workflows from JSON under core/."""
        try:
            catalog = WorkflowCatalog()
            catalog.load_directory("src/tools/workflows/core")
            core_workflows = {
                workflow.workflow_id: self._workflow_entry(
                    workflow,
                    source="core",
                    category=self._determine_workflow_category(workflow.workflow_id, workflow.name),
                    file_path="src/tools/workflows/core",
                    validation_status="valid",
                )
                for workflow in catalog.list_workflows()
            }
            logger.info("Discovered %s core workflows", len(core_workflows))
            return core_workflows
        except Exception as e:
            logger.error(f"Error discovering core workflows: {e}", exc_info=True)
            raise

    async def _discover_contrib_workflows(self, ctx: Context) -> dict[str, Any]:
        """Discover contrib workflows from contrib/workflows/ JSON files."""
        try:
            catalog = WorkflowCatalog()
            catalog.load_directory("contrib/workflows")
            contrib_workflows = {}
            root = Path("contrib/workflows")
            for workflow in catalog.list_workflows():
                file_path = "contrib/workflows"
                category = "custom"
                for path in root.rglob("*.json"):
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    if data.get("workflow_id") != workflow.workflow_id:
                        continue
                    file_path = str(path)
                    path_parts = path.parts
                    if len(path_parts) >= 3 and path_parts[-3] == "workflows":
                        category = path_parts[-2]
                    break
                contrib_workflows[workflow.workflow_id] = self._workflow_entry(
                    workflow,
                    source="contrib",
                    category=category,
                    file_path=file_path,
                    validation_status="valid",
                )
            logger.info("Discovered %s contrib workflows", len(contrib_workflows))
            return contrib_workflows
        except Exception as e:
            logger.error(f"Error discovering contrib workflows: {e}", exc_info=True)
            raise

    def _determine_workflow_category(self, workflow_id: str, workflow_name: str) -> str:
        """Determine workflow category based on ID and name."""
        workflow_lower = f"{workflow_id} {workflow_name}".lower()

        if any(
            keyword in workflow_lower
            for keyword in ["security", "auth", "login", "access", "permission"]
        ):
            return "security"
        elif any(
            keyword in workflow_lower
            for keyword in ["performance", "resource", "cpu", "memory", "slow"]
        ):
            return "performance"
        elif any(keyword in workflow_lower for keyword in ["data", "missing", "search", "index"]):
            return "data_analysis"
        elif any(keyword in workflow_lower for keyword in ["health", "status", "check", "monitor"]):
            return "health"
        else:
            return "general"

    def _format_detailed(
        self, workflows: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Format detailed workflow information."""
        return {
            "format": "detailed",
            "discovery_metadata": metadata,
            "total_workflows": len(workflows),
            "workflows": workflows,
            "usage_instructions": {
                "dynamic_troubleshoot_agent": "Use workflow_type parameter with any workflow_id",
                "example": "await dynamic_troubleshoot_agent.execute(ctx=ctx, problem_description='...', workflow_type='workflow_id')",
                "available_workflow_ids": list(workflows.keys()),
            },
            "categories": self._get_category_summary(workflows),
        }

    def _format_summary(
        self, workflows: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Format summary workflow information."""
        summary_workflows = {}
        for workflow_id, workflow in workflows.items():
            summary_workflows[workflow_id] = {
                "name": workflow["name"],
                "source": workflow["source"],
                "category": workflow["category"],
                "task_count": workflow["task_count"],
                "has_dependencies": workflow["has_dependencies"],
                "validation_status": workflow["validation_status"],
            }

        return {
            "format": "summary",
            "discovery_metadata": metadata,
            "total_workflows": len(workflows),
            "workflows": summary_workflows,
            "categories": self._get_category_summary(workflows),
        }

    def _format_ids_only(
        self, workflows: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Format workflow IDs only."""
        core_ids = [wf_id for wf_id, wf in workflows.items() if wf["source"] == "core"]
        contrib_ids = [wf_id for wf_id, wf in workflows.items() if wf["source"] == "contrib"]

        return {
            "format": "ids_only",
            "discovery_metadata": metadata,
            "total_workflows": len(workflows),
            "all_workflow_ids": list(workflows.keys()),
            "core_workflow_ids": core_ids,
            "contrib_workflow_ids": contrib_ids,
            "by_category": {
                category: [wf_id for wf_id, wf in workflows.items() if wf["category"] == category]
                for category in set(wf["category"] for wf in workflows.values())
            },
        }

    def _format_by_category(
        self, workflows: dict[str, Any], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Format workflows grouped by category."""
        by_category = {}
        for workflow_id, workflow in workflows.items():
            category = workflow["category"]
            if category not in by_category:
                by_category[category] = {}
            by_category[category][workflow_id] = workflow

        return {
            "format": "by_category",
            "discovery_metadata": metadata,
            "total_workflows": len(workflows),
            "categories": by_category,
            "category_summary": self._get_category_summary(workflows),
        }

    def _get_category_summary(self, workflows: dict[str, Any]) -> dict[str, Any]:
        """Get summary of workflows by category."""
        category_summary = {}
        for workflow in workflows.values():
            category = workflow["category"]
            if category not in category_summary:
                category_summary[category] = {
                    "count": 0,
                    "core_count": 0,
                    "contrib_count": 0,
                    "workflow_ids": [],
                }

            category_summary[category]["count"] += 1
            category_summary[category]["workflow_ids"].append(workflow["workflow_id"])

            if workflow["source"] == "core":
                category_summary[category]["core_count"] += 1
            else:
                category_summary[category]["contrib_count"] += 1

        return category_summary


# Register the tool for automatic discovery
def create_list_workflows_tool() -> ListWorkflowsTool:
    """Factory function to create the list workflows tool."""
    return ListWorkflowsTool("list_workflows", "workflows")


# Main execution for testing
if __name__ == "__main__":
    import asyncio

    async def test_list_workflows():
        """Test the list workflows tool."""
        tool = create_list_workflows_tool()

        # Mock context for testing
        class MockContext:
            async def info(self, msg):
                print(f"INFO: {msg}")

            async def error(self, msg):
                print(f"ERROR: {msg}")

            async def report_progress(self, progress, total):
                pass

        ctx = MockContext()

        print("Testing list workflows tool...")
        print("=" * 50)

        # Test different formats
        formats = ["detailed", "summary", "ids_only", "by_category"]

        for fmt in formats:
            print(f"\n🔧 Testing {fmt} format:")
            result = await tool.execute(ctx, format_type=fmt)
            print(f"Status: {result.get('status', 'unknown')}")
            if result.get("status") == "success":
                data = result.get("result", {})
                print(f"Total workflows: {data.get('total_workflows', 0)}")
                print(f"Format: {data.get('format', 'unknown')}")
                if "categories" in data:
                    print(f"Categories: {list(data['categories'].keys())}")

        print("\n✅ Test completed!")

    asyncio.run(test_list_workflows())
