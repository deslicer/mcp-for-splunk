"""List Workflows Tool

Provides a comprehensive listing of all available workflows from both core (built-in)
and contrib (user-contributed) sources in the MCP Server for Splunk.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from .shared.config import AgentConfig
from .shared.tools import SplunkToolRegistry
from .shared.workflow_manager import WorkflowManager

logger = logging.getLogger(__name__)

# Import contrib workflow loader
try:
    from contrib.workflows.loaders import WorkflowLoader
    CONTRIB_LOADER_AVAILABLE = True
except ImportError:
    CONTRIB_LOADER_AVAILABLE = False
    WorkflowLoader = None
    logger.warning("Contrib workflow loader not available")


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
        category_filter: Optional[str] = None
    ) -> Dict[str, Any]:
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
                "warnings": []
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
                await ctx.info(f"🎯 Filtered to {len(all_workflows)} workflows in category '{category_filter}'")

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

    async def _discover_core_workflows(self, ctx: Context) -> Dict[str, Any]:
        """Discover core (built-in) workflows from WorkflowManager."""
        try:
            # Create a minimal config for WorkflowManager
            config = AgentConfig(
                api_key="dummy",  # Not needed for workflow discovery
                model="gpt-4o",
                temperature=0.7,
                max_tokens=4000
            )

            # Create tool registry (also not needed for workflow discovery)
            tool_registry = SplunkToolRegistry()

            # Create WorkflowManager to get built-in workflows
            workflow_manager = WorkflowManager(config, tool_registry)

            # Get all workflows from the manager
            workflows = workflow_manager.list_workflows()

            core_workflows = {}
            for workflow in workflows:
                core_workflows[workflow.workflow_id] = {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "source": "core",
                    "category": self._determine_workflow_category(workflow.workflow_id, workflow.name),
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
                            "context_requirements": task.context_requirements
                        }
                        for task in workflow.tasks
                    ],
                    "validation_status": "valid",  # Core workflows are always valid
                    "file_path": "built-in"
                }

            logger.info(f"Discovered {len(core_workflows)} core workflows")
            return core_workflows

        except Exception as e:
            logger.error(f"Error discovering core workflows: {e}", exc_info=True)
            raise

    async def _discover_contrib_workflows(self, ctx: Context) -> Dict[str, Any]:
        """Discover contrib (user-contributed) workflows from contrib/workflows/."""
        if not CONTRIB_LOADER_AVAILABLE:
            logger.warning("Contrib workflow loader not available")
            return {}

        try:
            # Create workflow loader
            loader = WorkflowLoader("contrib/workflows")

            # Load all workflows
            workflows = loader.load_all_workflows()

            # Get loading report for validation info
            loading_report = loader.get_loading_report()

            contrib_workflows = {}
            for workflow_id, workflow in workflows.items():
                # Determine file path and category from loader
                file_path = "unknown"
                category = "custom"

                # Try to determine category from file structure
                workflow_files = loader.discover_workflows()
                for file in workflow_files:
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)
                            if data.get("workflow_id") == workflow_id:
                                file_path = str(file)
                                # Extract category from path
                                path_parts = Path(file).parts
                                if len(path_parts) >= 3 and path_parts[-3] == "workflows":
                                    category = path_parts[-2]  # Directory name
                                break
                    except:
                        continue

                # Only include workflows that are actually from contrib directory
                # Check if the file path is in the contrib/workflows directory
                if "contrib/workflows" in file_path or file_path.startswith("contrib/workflows"):
                    contrib_workflows[workflow_id] = {
                        "workflow_id": workflow.workflow_id,
                        "name": workflow.name,
                        "description": workflow.description,
                        "source": "contrib",
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
                                "context_requirements": task.context_requirements
                            }
                            for task in workflow.tasks
                        ],
                        "validation_status": "valid",  # Successfully loaded workflows are valid
                        "file_path": file_path
                    }

            # Add information about any failed workflows (only contrib ones)
            for error in loading_report.get("errors", []):
                error_file = error['file']
                # Only include errors from contrib directory
                if "contrib/workflows" in error_file or error_file.startswith("contrib/workflows"):
                    error_workflow_id = f"error_{Path(error_file).stem}"
                    contrib_workflows[error_workflow_id] = {
                        "workflow_id": error_workflow_id,
                        "name": f"Failed: {Path(error_file).name}",
                        "description": f"Workflow failed to load: {error['error']}",
                        "source": "contrib",
                        "category": "error",
                        "task_count": 0,
                        "has_dependencies": False,
                        "default_context": {},
                        "tasks": [],
                        "validation_status": "error",
                        "validation_error": error['error'],
                        "file_path": error_file
                    }

            logger.info(f"Discovered {len(contrib_workflows)} valid contrib workflows, {len([e for e in loading_report.get('errors', []) if 'contrib/workflows' in e.get('file', '')])} errors")
            return contrib_workflows

        except Exception as e:
            logger.error(f"Error discovering contrib workflows: {e}", exc_info=True)
            raise

    def _determine_workflow_category(self, workflow_id: str, workflow_name: str) -> str:
        """Determine workflow category based on ID and name."""
        workflow_lower = f"{workflow_id} {workflow_name}".lower()

        if any(keyword in workflow_lower for keyword in ["security", "auth", "login", "access", "permission"]):
            return "security"
        elif any(keyword in workflow_lower for keyword in ["performance", "resource", "cpu", "memory", "slow"]):
            return "performance"
        elif any(keyword in workflow_lower for keyword in ["data", "missing", "search", "index"]):
            return "data_analysis"
        elif any(keyword in workflow_lower for keyword in ["health", "status", "check", "monitor"]):
            return "health"
        else:
            return "general"

    def _format_detailed(self, workflows: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format detailed workflow information."""
        return {
            "format": "detailed",
            "discovery_metadata": metadata,
            "total_workflows": len(workflows),
            "workflows": workflows,
            "usage_instructions": {
                "dynamic_troubleshoot_agent": "Use workflow_type parameter with any workflow_id",
                "example": "await dynamic_troubleshoot_agent.execute(ctx=ctx, problem_description='...', workflow_type='workflow_id')",
                "available_workflow_ids": list(workflows.keys())
            },
            "categories": self._get_category_summary(workflows)
        }

    def _format_summary(self, workflows: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format summary workflow information."""
        summary_workflows = {}
        for workflow_id, workflow in workflows.items():
            summary_workflows[workflow_id] = {
                "name": workflow["name"],
                "source": workflow["source"],
                "category": workflow["category"],
                "task_count": workflow["task_count"],
                "has_dependencies": workflow["has_dependencies"],
                "validation_status": workflow["validation_status"]
            }

        return {
            "format": "summary",
            "discovery_metadata": metadata,
            "total_workflows": len(workflows),
            "workflows": summary_workflows,
            "categories": self._get_category_summary(workflows)
        }

    def _format_ids_only(self, workflows: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
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
            }
        }

    def _format_by_category(self, workflows: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
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
            "category_summary": self._get_category_summary(workflows)
        }

    def _get_category_summary(self, workflows: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of workflows by category."""
        category_summary = {}
        for workflow in workflows.values():
            category = workflow["category"]
            if category not in category_summary:
                category_summary[category] = {
                    "count": 0,
                    "core_count": 0,
                    "contrib_count": 0,
                    "workflow_ids": []
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
            async def info(self, msg): print(f"INFO: {msg}")
            async def error(self, msg): print(f"ERROR: {msg}")
            async def report_progress(self, progress, total): pass

        ctx = MockContext()

        print("Testing list workflows tool...")
        print("=" * 50)

        # Test different formats
        formats = ["detailed", "summary", "ids_only", "by_category"]

        for fmt in formats:
            print(f"\n🔧 Testing {fmt} format:")
            result = await tool.execute(ctx, format_type=fmt)
            print(f"Status: {result.get('status', 'unknown')}")
            if result.get('status') == 'success':
                data = result.get('result', {})
                print(f"Total workflows: {data.get('total_workflows', 0)}")
                print(f"Format: {data.get('format', 'unknown')}")
                if 'categories' in data:
                    print(f"Categories: {list(data['categories'].keys())}")

        print("\n✅ Test completed!")

    asyncio.run(test_list_workflows())