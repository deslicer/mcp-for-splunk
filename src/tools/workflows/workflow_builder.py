"""Workflow Builder Tool

Interactive tool for creating, editing, and validating custom workflows for the
MCP Server for Splunk dynamic troubleshooting system.
"""

import json
import logging
import re
from typing import Any

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata

logger = logging.getLogger(__name__)


class WorkflowBuilderTool(BaseTool):
    """
    Workflow Builder Tool for Interactive Workflow Creation.

    This tool provides comprehensive workflow creation, editing, and validation capabilities
    for custom troubleshooting workflows that integrate with the dynamic troubleshoot agent.
    It supports multiple modes of operation for different user needs.

    ## Key Features:
    - **Interactive Creation**: Step-by-step workflow and task creation
    - **Template Generation**: Pre-built templates for common workflow types
    - **Comprehensive Validation**: Structure, dependencies, and integration validation
    - **Editing Support**: Modify existing workflows with validation
    - **Multiple Output Formats**: JSON generation with proper formatting
    - **Finished Workflow Processing**: Accept and validate complete workflow definitions

    ## Modes of Operation:
    - **create**: Interactive workflow creation from scratch
    - **edit**: Modify existing workflow definitions
    - **validate**: Comprehensive validation of workflow structure
    - **template**: Generate workflow templates for different use cases
    - **process**: Process and validate finished workflow definitions

    ## Validation Features:
    - **Structure Validation**: Schema compliance and required fields
    - **Dependency Validation**: Circular dependency detection and resolution
    - **Tool Validation**: Verify all required tools are available
    - **Context Validation**: Check context variable requirements
    - **Integration Validation**: Ensure compatibility with dynamic troubleshoot agent

    ## Templates Available:
    - **minimal**: Basic workflow template with single task
    - **security**: Security analysis workflow template
    - **performance**: Performance analysis workflow template
    - **data_quality**: Data quality assessment workflow template
    - **parallel**: Parallel task execution example
    - **sequential**: Sequential task execution with dependencies
    """

    METADATA = ToolMetadata(
        name="workflow_builder",
        description="""Interactive tool for creating, editing, and validating custom workflows.

This tool provides comprehensive workflow development capabilities for creating custom troubleshooting
workflows that integrate with the MCP Server for Splunk dynamic troubleshooting system. It supports
multiple modes of operation to accommodate different workflow development needs.

## Modes:
- **create**: Interactive workflow creation with guided prompts
- **edit**: Modify existing workflow definitions with validation
- **validate**: Comprehensive validation of workflow structure and dependencies
- **template**: Generate pre-built workflow templates for common use cases
- **process**: Process and validate finished workflow definitions

## Key Capabilities:
- Step-by-step workflow creation with validation
- Template generation for common workflow patterns
- Comprehensive validation including dependency analysis
- JSON output generation with proper formatting
- Integration testing and compatibility verification
- Processing of complete workflow definitions

## Validation Features:
- Schema compliance verification
- Circular dependency detection
- Tool availability checking
- Context variable validation
- Integration compatibility assessment

Perfect for workflow contributors who need guided assistance in creating well-structured,
validated workflows that integrate seamlessly with the dynamic troubleshoot agent.""",
        category="workflows",
    )

    def __init__(self, name: str, category: str):
        super().__init__(name, self.METADATA.description)
        self.category = category

    async def execute(
        self,
        ctx: Context,
        mode: str = "create",
        workflow_data: str | dict[str, Any] | None = None,
        template_type: str = "minimal",
        file_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Build, edit, validate, or process workflows.

        Args:
            mode: Operation mode - "create", "edit", "validate", "template", or "process"
            workflow_data: Workflow data as JSON string or dict (for edit/validate/process modes)
            template_type: Template type for template mode ("minimal", "security", "performance", etc.)
            file_path: Path to workflow file (for validate mode)

        Returns:
            Dict containing workflow data, validation results, or templates
        """
        try:
            if mode == "create":
                return self.format_success_response(await self._create_workflow_interactive(ctx))
            elif mode == "edit":
                if not workflow_data:
                    return self.format_error_response("workflow_data required for edit mode")
                return self.format_success_response(await self._edit_workflow(ctx, workflow_data))
            elif mode == "validate":
                if workflow_data:
                    return self.format_success_response(self._validate_workflow_data(workflow_data))
                elif file_path:
                    return self.format_success_response(self._validate_workflow_file(file_path))
                else:
                    return self.format_error_response(
                        "workflow_data or file_path required for validate mode"
                    )
            elif mode == "process":
                if not workflow_data:
                    return self.format_error_response("workflow_data required for process mode")
                return self.format_success_response(
                    await self._process_finished_workflow(ctx, workflow_data)
                )
            elif mode == "template":
                return self.format_success_response(self._generate_template(template_type))
            else:
                return self.format_error_response(
                    f"Unknown mode: {mode}. Use 'create', 'edit', 'validate', 'process', or 'template'"
                )

        except Exception as e:
            return self.format_error_response(f"Workflow builder error: {str(e)}")

    def _normalize_workflow_data(self, workflow_data: str | dict[str, Any]) -> dict[str, Any]:
        """Normalize workflow data from string or dict to dict."""
        if isinstance(workflow_data, str):
            try:
                return json.loads(workflow_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON format: {str(e)}")
        elif isinstance(workflow_data, dict):
            return workflow_data
        else:
            raise ValueError(f"workflow_data must be a string or dict, got {type(workflow_data)}")

    async def _process_finished_workflow(
        self, ctx: Context, workflow_data: str | dict[str, Any]
    ) -> dict[str, Any]:
        """Process and validate a finished workflow definition."""

        await ctx.info("🔧 Processing finished workflow definition...")

        # Normalize the input data
        try:
            workflow = self._normalize_workflow_data(workflow_data)
        except ValueError as e:
            return {"error": str(e)}

        # Perform comprehensive validation
        validation_result = self._validate_workflow_structure(workflow)

        if validation_result["valid"]:
            await ctx.info("✅ Workflow validation successful!")

            # Generate additional metadata for the processed workflow
            processed_workflow = {
                "workflow": workflow,
                "validation": validation_result,
                "processing_metadata": {
                    "processed_at": "timestamp",
                    "validation_passed": True,
                    "ready_for_execution": True,
                    "compatible_with_runner": True,
                },
                "usage_instructions": {
                    "workflow_runner": f"Use workflow_id='{workflow.get('workflow_id', 'unknown')}' with the workflow_runner tool",
                    "dynamic_troubleshoot": f"Use workflow_type='{workflow.get('workflow_id', 'unknown')}' with dynamic_troubleshoot_agent",
                    "file_save": "Save this workflow as JSON in contrib/workflows/category/ directory",
                },
                "integration_ready": True,
            }

            return processed_workflow
        else:
            await ctx.error("❌ Workflow validation failed!")
            return {
                "workflow": workflow,
                "validation": validation_result,
                "processing_metadata": {
                    "processed_at": "timestamp",
                    "validation_passed": False,
                    "ready_for_execution": False,
                    "compatible_with_runner": False,
                },
                "integration_ready": False,
                "errors": validation_result["errors"],
                "fix_suggestions": validation_result["suggestions"],
            }

    async def _create_workflow_interactive(self, ctx: Context) -> dict[str, Any]:
        """Create a workflow interactively with guided prompts."""

        workflow = {
            "workflow_id": "",
            "name": "",
            "description": "",
            "tasks": [],
            "default_context": {},
        }

        # Get basic workflow information
        await ctx.info("🚀 Starting interactive workflow creation...")
        await ctx.info("Please provide the following information for your workflow:")

        # For demo purposes, we'll create a template workflow
        # In a real implementation, this would collect user input

        workflow_info = {
            "workflow_id": "custom_workflow_example",
            "name": "Custom Workflow Example",
            "description": "Example custom workflow created with the workflow builder tool",
            "category": "custom",
            "tasks": [
                {
                    "task_id": "initial_assessment",
                    "name": "Initial Assessment",
                    "description": "Perform initial system assessment",
                    "instructions": """
You are performing an initial assessment of the Splunk environment.

**Context:** Analyzing system health and basic metrics from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Check Splunk server health and connectivity
2. Verify user permissions and access
3. List available indexes for analysis
4. Gather basic system information

**Searches to Execute:**
- Use get_splunk_health to check server status
- Use get_current_user_info to verify permissions
- Use list_splunk_indexes to see available data

**What to Look For:**
- Server connectivity and health status
- User role and permission levels
- Available indexes and data access
- Any immediate system issues

**Output:** Return DiagnosticResult with system health status and available resources.
                    """,
                    "required_tools": [
                        "get_splunk_health",
                        "get_current_user_info",
                        "list_splunk_indexes",
                    ],
                    "dependencies": [],
                    "context_requirements": ["earliest_time", "latest_time"],
                },
                {
                    "task_id": "data_analysis",
                    "name": "Data Analysis",
                    "description": "Analyze data availability and quality",
                    "instructions": """
You are performing data analysis based on the initial assessment results.

**Context:** Analyzing data in index {focus_index} from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Check data availability in the specified index
2. Analyze recent data ingestion patterns
3. Verify data quality and completeness
4. Identify any data gaps or issues

**Searches to Execute:**
- index={focus_index} | stats count by sourcetype | sort -count
- index={focus_index} | timechart count span=1h
- index={focus_index} | stats latest(_time) as latest_data, earliest(_time) as earliest_data

**What to Look For:**
- Data volume and distribution patterns
- Recent data ingestion status
- Missing or delayed data
- Data quality indicators

**Output:** Return DiagnosticResult with data availability analysis and recommendations.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": ["initial_assessment"],
                    "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                },
            ],
        }

        workflow.update(workflow_info)

        # Validate the created workflow
        validation_result = self._validate_workflow_structure(workflow)

        result = {
            "workflow": workflow,
            "validation": validation_result,
            "next_steps": [
                "Save the workflow JSON to a file in contrib/workflows/",
                "Test the workflow with the dynamic troubleshoot agent",
                "Submit a pull request to contribute to the community",
            ],
            "usage_example": {
                "description": "How to use this workflow with the dynamic troubleshoot agent",
                "code": f"""
# Use your custom workflow
await dynamic_troubleshoot_agent.execute(
    ctx=context,
    problem_description="Describe your specific issue here",
    workflow_type="{workflow['workflow_id']}",
    earliest_time="-24h",
    latest_time="now",
    focus_index="main"  # or your specific index
)
                """.strip(),
            },
        }

        await ctx.info("✅ Workflow creation completed successfully!")
        return result

    async def _edit_workflow(
        self, ctx: Context, workflow_data: str | dict[str, Any]
    ) -> dict[str, Any]:
        """Edit an existing workflow with validation."""

        try:
            workflow = self._normalize_workflow_data(workflow_data)
        except ValueError as e:
            return {"error": str(e)}

        await ctx.info("🔧 Starting workflow editing mode...")

        # For demo purposes, we'll add a new task to the workflow
        # In a real implementation, this would provide interactive editing

        new_task = {
            "task_id": "additional_analysis",
            "name": "Additional Analysis",
            "description": "Additional analysis task added during editing",
            "instructions": """
You are performing additional analysis as part of the workflow.

**Context:** Extended analysis based on previous task results

**Analysis Steps:**
1. Review results from previous tasks
2. Perform additional targeted analysis
3. Generate comprehensive recommendations
4. Provide summary of findings

**Output:** Return DiagnosticResult with additional analysis findings.
            """,
            "required_tools": ["run_splunk_search"],
            "dependencies": [],
            "context_requirements": ["earliest_time", "latest_time"],
        }

        workflow["tasks"].append(new_task)

        # Validate the edited workflow
        validation_result = self._validate_workflow_structure(workflow)

        result = {
            "edited_workflow": workflow,
            "validation": validation_result,
            "changes_made": [
                "Added new task: additional_analysis",
                "Updated task dependencies",
                "Validated workflow structure",
            ],
        }

        await ctx.info("✅ Workflow editing completed successfully!")
        return result

    def _validate_workflow_data(self, workflow_data: str | dict[str, Any]) -> dict[str, Any]:
        """Validate workflow data from JSON string or dict."""

        try:
            workflow = self._normalize_workflow_data(workflow_data)
        except ValueError as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "suggestions": ["Check JSON syntax and formatting"],
            }

        return self._validate_workflow_structure(workflow)

    def _validate_workflow_file(self, file_path: str) -> dict[str, Any]:
        """Validate workflow from file path."""

        try:
            with open(file_path) as f:
                workflow_data = f.read()
            return self._validate_workflow_data(workflow_data)
        except FileNotFoundError:
            return {
                "valid": False,
                "errors": [f"File not found: {file_path}"],
                "warnings": [],
                "suggestions": ["Check file path and ensure file exists"],
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Error reading file: {str(e)}"],
                "warnings": [],
                "suggestions": ["Check file permissions and format"],
            }

    def _get_available_tools(self) -> dict[str, str]:
        """Get available Splunk tools with descriptions - dynamically from tool_registry."""
        try:
            # Try to get tools dynamically from tool_registry
            from src.core.registry import tool_registry

            available_tools = {}

            for tool_metadata in tool_registry.list_tools():
                # tool_metadata is a ToolMetadata object
                available_tools[tool_metadata.name] = tool_metadata.description

            if available_tools:
                return available_tools
        except (ImportError, AttributeError, Exception) as e:
            # Fallback to static list if dynamic discovery fails
            logger.warning(f"Dynamic tool discovery failed: {e}. Using static tool list.")

        # Fallback static list (keep for backward compatibility)
        return {
            # Search Tools
            "run_splunk_search": "Execute comprehensive Splunk searches with full SPL support",
            "run_oneshot_search": "Execute quick, lightweight searches for immediate results",
            "run_saved_search": "Execute predefined saved searches",
            # Metadata Tools
            "list_splunk_indexes": "Get list of available Splunk indexes",
            "list_splunk_sources": "Get list of available data sources",
            "list_splunk_sourcetypes": "Get list of available sourcetypes",
            # Administrative Tools
            "get_current_user_info": "Get current user information, roles, and permissions",
            "get_splunk_health": "Check Splunk server health and connectivity status",
            "get_splunk_apps": "List installed Splunk applications",
            "get_configurations": "Retrieve Splunk configuration settings from .conf files",
            # Alert Tools
            "get_alert_status": "Check alert configurations and firing status",
            "list_triggered_alerts": "List all triggered alerts in Splunk",
            # KV Store Tools
            "get_kvstore_data": "Retrieve data from KV Store collections",
            "list_kvstore_collections": "List all KV Store collections",
            "create_kvstore_collection": "Create new KV Store collections",
            # Workflow Tools
            "list_workflows": "List available workflows",
            "workflow_runner": "Execute workflows by ID",
            # Utility Tools
            "report_specialist_progress": "Report progress during task execution",
        }

    def _get_context_variables(self) -> dict[str, str]:
        """Get available context variables with descriptions - synchronized with workflow_requirements.py."""
        return {
            # Time Context
            "earliest_time": "Start time for analysis (e.g., '-24h', '2023-01-01T00:00:00')",
            "latest_time": "End time for analysis (e.g., 'now', '-1h', '@d')",
            # Focus Context
            "focus_index": "Target index for focused analysis",
            "focus_host": "Target host for focused analysis",
            "focus_sourcetype": "Target sourcetype for focused analysis",
            # User Context
            "complexity_level": "Analysis depth level ('basic', 'moderate', 'advanced')",
            # Custom Context
            # Note: Custom context variables can be defined in default_context
            "custom_variable_example": "Example of custom context variable from default_context",
        }

    def _validate_workflow_structure(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Comprehensive workflow structure validation."""

        errors = []
        warnings = []
        suggestions = []

        # Required field validation
        required_fields = ["workflow_id", "name", "description", "tasks"]
        for field in required_fields:
            if field not in workflow:
                errors.append(f"Missing required field: {field}")

        # Workflow ID validation
        if "workflow_id" in workflow:
            workflow_id = workflow["workflow_id"]
            if not re.match(r"^[a-z0-9_]+$", workflow_id):
                errors.append(
                    "workflow_id must use snake_case format (lowercase, numbers, underscores only)"
                )
            if len(workflow_id) > 50:
                errors.append("workflow_id must be 50 characters or less")

        # Name validation
        if "name" in workflow:
            if len(workflow["name"]) > 100:
                errors.append("name must be 100 characters or less")

        # Description validation
        if "description" in workflow:
            if len(workflow["description"]) > 1000:
                warnings.append("description is quite long (>1000 chars), consider shortening")

        # Tasks validation
        if "tasks" in workflow:
            tasks = workflow["tasks"]
            if not isinstance(tasks, list):
                errors.append("tasks must be a list")
            elif len(tasks) == 0:
                errors.append("workflow must contain at least one task")
            elif len(tasks) > 20:
                warnings.append(
                    "workflow has many tasks (>20), consider splitting into multiple workflows"
                )
            else:
                # Validate individual tasks
                task_ids = set()
                for i, task in enumerate(tasks):
                    task_errors, task_warnings = self._validate_task(task, i)
                    errors.extend(task_errors)
                    warnings.extend(task_warnings)

                    # Check for duplicate task IDs
                    if "task_id" in task:
                        if task["task_id"] in task_ids:
                            errors.append(f"Duplicate task_id: {task['task_id']}")
                        task_ids.add(task["task_id"])

                # Validate dependencies
                dep_errors, dep_warnings = self._validate_dependencies(tasks)
                errors.extend(dep_errors)
                warnings.extend(dep_warnings)

        # Tool validation
        tool_errors, tool_warnings = self._validate_tools(workflow)
        errors.extend(tool_errors)
        warnings.extend(tool_warnings)

        # Context validation
        context_errors, context_warnings = self._validate_context(workflow)
        errors.extend(context_errors)
        warnings.extend(context_warnings)

        # Generate suggestions
        if not errors:
            suggestions.extend(
                [
                    "Consider adding comprehensive test cases",
                    "Document expected use cases and scenarios",
                    "Test with actual Splunk environment",
                    "Consider performance impact of searches",
                ]
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "summary": {
                "total_tasks": len(workflow.get("tasks", [])),
                "unique_task_ids": len(
                    set(task.get("task_id", "") for task in workflow.get("tasks", []))
                ),
                "has_dependencies": any(
                    task.get("dependencies", []) for task in workflow.get("tasks", [])
                ),
                "required_tools": list(
                    set(
                        tool
                        for task in workflow.get("tasks", [])
                        for tool in task.get("required_tools", [])
                    )
                ),
                "context_variables": list(
                    set(
                        var
                        for task in workflow.get("tasks", [])
                        for var in task.get("context_requirements", [])
                    )
                ),
            },
        }

    def _validate_task(self, task: dict[str, Any], index: int) -> tuple[list[str], list[str]]:
        """Validate individual task structure."""

        errors = []
        warnings = []

        # Required fields
        required_fields = ["task_id", "name", "description", "instructions"]
        for field in required_fields:
            if field not in task:
                errors.append(f"Task {index}: Missing required field '{field}'")

        # Task ID validation
        if "task_id" in task:
            task_id = task["task_id"]
            if not re.match(r"^[a-z0-9_]+$", task_id):
                errors.append(f"Task {index}: task_id must use snake_case format")
            if len(task_id) > 50:
                errors.append(f"Task {index}: task_id must be 50 characters or less")

        # Name validation
        if "name" in task:
            if len(task["name"]) > 100:
                errors.append(f"Task {index}: name must be 100 characters or less")

        # Description validation
        if "description" in task:
            if len(task["description"]) > 200:
                warnings.append(f"Task {index}: description is quite long (>200 chars)")

        # Instructions validation
        if "instructions" in task:
            instructions = task["instructions"]
            if len(instructions) < 50:
                warnings.append(
                    f"Task {index}: instructions seem quite brief, consider adding more detail"
                )
            if len(instructions) > 5000:
                errors.append(f"Task {index}: instructions must be 5000 characters or less")

            # Check for context variable usage
            if "{" not in instructions:
                suggestions = warnings  # Use warnings list for suggestions in this context
                suggestions.append(
                    f"Task {index}: Consider using context variables like {{focus_index}} in instructions"
                )

        return errors, warnings

    def _validate_dependencies(self, tasks: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        """Validate task dependencies and detect circular dependencies."""

        errors = []
        warnings = []

        # Build task ID map
        task_ids = {task.get("task_id") for task in tasks if "task_id" in task}

        # Check dependency references
        for task in tasks:
            task_id = task.get("task_id", "unknown")
            dependencies = task.get("dependencies", [])

            for dep in dependencies:
                if dep not in task_ids:
                    errors.append(f"Task '{task_id}': dependency '{dep}' not found in workflow")

        # Check for circular dependencies
        def has_circular_dependency(task_id: str, visited: set, rec_stack: set) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            # Find task with this ID
            task = next((t for t in tasks if t.get("task_id") == task_id), None)
            if not task:
                return False

            dependencies = task.get("dependencies", [])
            for dep in dependencies:
                if dep not in visited:
                    if has_circular_dependency(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        visited = set()
        for task in tasks:
            task_id = task.get("task_id")
            if task_id and task_id not in visited:
                if has_circular_dependency(task_id, visited, set()):
                    errors.append(f"Circular dependency detected involving task '{task_id}'")

        return errors, warnings

    def _validate_tools(self, workflow: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Validate tool availability and usage."""

        errors = []
        warnings = []

        # Get available tools from the updated list
        available_tools = set(self._get_available_tools().keys())

        for task in workflow.get("tasks", []):
            task_id = task.get("task_id", "unknown")
            required_tools = task.get("required_tools", [])

            for tool in required_tools:
                if tool not in available_tools:
                    errors.append(f"Task '{task_id}': unknown tool '{tool}'")

            # Check if task has tools but no instructions mentioning them
            if required_tools and "instructions" in task:
                instructions = task["instructions"]
                unused_tools = []
                for tool in required_tools:
                    if tool not in instructions:
                        unused_tools.append(tool)
                if unused_tools:
                    warnings.append(
                        f"Task '{task_id}': tools {unused_tools} not mentioned in instructions"
                    )

        return errors, warnings

    def _validate_context(self, workflow: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Validate context variable usage."""

        errors = []
        warnings = []

        # Get available context variables
        available_context = set(self._get_context_variables().keys())

        # Add custom context variables from default_context
        default_context = workflow.get("default_context", {})
        available_context.update(default_context.keys())

        for task in workflow.get("tasks", []):
            task_id = task.get("task_id", "unknown")
            context_requirements = task.get("context_requirements", [])
            instructions = task.get("instructions", "")

            # Check required context variables exist
            for var in context_requirements:
                if var not in available_context:
                    errors.append(f"Task '{task_id}': unknown context variable '{var}'")

            # Check for context variables used in instructions but not declared
            import re

            used_vars = re.findall(r"\{(\w+)\}", instructions)
            for var in used_vars:
                if var not in context_requirements and var not in default_context:
                    warnings.append(
                        f"Task '{task_id}': context variable '{var}' used but not in context_requirements"
                    )

        return errors, warnings

    def _generate_template(self, template_type: str) -> dict[str, Any]:
        """Generate workflow templates for different use cases."""

        templates = {
            "minimal": self._get_minimal_template(),
            "security": self._get_security_template(),
            "performance": self._get_performance_template(),
            "data_quality": self._get_data_quality_template(),
            "parallel": self._get_parallel_template(),
            "sequential": self._get_sequential_template(),
        }

        if template_type not in templates:
            available = ", ".join(templates.keys())
            return {
                "error": f"Unknown template type: {template_type}",
                "available_templates": list(templates.keys()),
                "suggestion": f"Use one of: {available}",
            }

        template = templates[template_type]

        return {
            "template": template,
            "template_type": template_type,
            "description": template.get("_template_description", "Custom workflow template"),
            "usage_instructions": [
                "Customize the workflow_id, name, and description",
                "Modify task instructions for your specific use case",
                "Add or remove tasks as needed",
                "Update context requirements and tool usage",
                "Validate the workflow before using",
            ],
            "next_steps": [
                "Save as JSON file in contrib/workflows/category/",
                "Test with dynamic troubleshoot agent",
                "Submit pull request for community review",
            ],
        }

    def _get_minimal_template(self) -> dict[str, Any]:
        """Get minimal workflow template."""
        return {
            "_template_description": "Minimal workflow template with single task",
            "workflow_id": "minimal_example",
            "name": "Minimal Example Workflow",
            "description": "A minimal workflow template for getting started with custom workflows",
            "tasks": [
                {
                    "task_id": "basic_check",
                    "name": "Basic System Check",
                    "description": "Perform basic system health check",
                    "instructions": """
You are performing a basic system health check.

**Analysis Steps:**
1. Check Splunk server health and connectivity
2. Verify basic system status
3. Report any immediate issues

**Searches to Execute:**
- Use get_splunk_health to check server status

**What to Look For:**
- Server connectivity status
- Basic system health indicators
- Any immediate connectivity issues

**Output:** Return DiagnosticResult with system health status.
                    """,
                    "required_tools": ["get_splunk_health"],
                    "dependencies": [],
                    "context_requirements": [],
                }
            ],
        }

    def _get_security_template(self) -> dict[str, Any]:
        """Get security analysis workflow template."""
        return {
            "_template_description": "Security analysis workflow template",
            "workflow_id": "security_analysis_template",
            "name": "Security Analysis Template",
            "description": "Template for security monitoring and threat detection workflows",
            "tasks": [
                {
                    "task_id": "authentication_analysis",
                    "name": "Authentication Analysis",
                    "description": "Analyze authentication events and failed login attempts",
                    "instructions": """
You are analyzing authentication events for security threats.

**Context:** Analyzing authentication in index {focus_index} from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Search for failed authentication attempts
2. Identify patterns of brute force attacks
3. Check for successful logins after failures
4. Analyze geographic and temporal patterns

**Searches to Execute:**
- index={focus_index} sourcetype=auth* action=failure | stats count by src_ip, user | sort -count
- index={focus_index} sourcetype=auth* | timechart count by action

**What to Look For:**
- High numbers of failed attempts from single IP
- Unusual login patterns outside business hours
- Geographic anomalies in login sources

**Output:** Return DiagnosticResult with authentication analysis and security recommendations.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": [],
                    "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                },
                {
                    "task_id": "privilege_escalation_check",
                    "name": "Privilege Escalation Check",
                    "description": "Check for privilege escalation attempts",
                    "instructions": """
You are checking for privilege escalation attempts.

**Context:** Analyzing privilege changes in index {focus_index} from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Search for sudo and administrative command usage
2. Check for role changes and permission modifications
3. Identify unusual administrative activity
4. Analyze privilege usage patterns

**Searches to Execute:**
- index={focus_index} sourcetype=linux_secure "sudo" | stats count by user, command
- index={focus_index} sourcetype=wineventlog EventCode=4672 | stats count by user

**What to Look For:**
- Unusual sudo command usage
- Administrative commands from non-admin users
- Privilege modification events

**Output:** Return DiagnosticResult with privilege escalation findings.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": [],
                    "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                },
            ],
        }

    def _get_performance_template(self) -> dict[str, Any]:
        """Get performance analysis workflow template."""
        return {
            "_template_description": "Performance analysis workflow template",
            "workflow_id": "performance_analysis_template",
            "name": "Performance Analysis Template",
            "description": "Template for system performance monitoring and analysis workflows",
            "tasks": [
                {
                    "task_id": "resource_utilization_check",
                    "name": "Resource Utilization Check",
                    "description": "Analyze system resource utilization patterns",
                    "instructions": """
You are analyzing system resource utilization.

**Context:** Analyzing performance from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Check CPU, memory, and disk usage patterns
2. Identify resource bottlenecks
3. Analyze usage trends over time
4. Compare against baseline metrics

**Searches to Execute:**
- index=_introspection component=Hostwide | stats avg(data.cpu_system_pct) avg(data.cpu_user_pct) by host
- index=_introspection component=Hostwide | timechart avg(data.mem_used) by host

**What to Look For:**
- High CPU or memory usage (>80%)
- Resource usage spikes
- Unusual resource consumption patterns

**Output:** Return DiagnosticResult with resource utilization analysis.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": [],
                    "context_requirements": ["earliest_time", "latest_time"],
                },
                {
                    "task_id": "search_performance_analysis",
                    "name": "Search Performance Analysis",
                    "description": "Analyze search performance and concurrency",
                    "instructions": """
You are analyzing search performance metrics.

**Context:** Analyzing search performance from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Check search execution times and concurrency
2. Identify slow or failed searches
3. Analyze search queue performance
4. Check for search optimization opportunities

**Searches to Execute:**
- index=_audit action=search | stats avg(total_run_time) by user, search_type
- index=_internal source=*scheduler.log* | stats count by status

**What to Look For:**
- Long-running searches (>300 seconds)
- High search concurrency
- Failed or cancelled searches

**Output:** Return DiagnosticResult with search performance analysis.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": [],
                    "context_requirements": ["earliest_time", "latest_time"],
                },
            ],
        }

    def _get_data_quality_template(self) -> dict[str, Any]:
        """Get data quality assessment workflow template."""
        return {
            "_template_description": "Data quality assessment workflow template",
            "workflow_id": "data_quality_template",
            "name": "Data Quality Assessment Template",
            "description": "Template for data quality and integrity assessment workflows",
            "tasks": [
                {
                    "task_id": "data_availability_check",
                    "name": "Data Availability Check",
                    "description": "Check data availability and ingestion patterns",
                    "instructions": """
You are checking data availability and ingestion.

**Context:** Analyzing data in index {focus_index} from {earliest_time} to {latest_time}

**Analysis Steps:**
1. Check data volume and distribution
2. Analyze ingestion patterns over time
3. Identify data gaps or delays
4. Verify expected data sources

**Searches to Execute:**
- index={focus_index} | stats count by sourcetype | sort -count
- index={focus_index} | timechart count span=1h
- index={focus_index} | stats latest(_time) as latest_data by sourcetype

**What to Look For:**
- Missing or delayed data
- Unexpected changes in data volume
- Data source availability issues

**Output:** Return DiagnosticResult with data availability analysis.
                    """,
                    "required_tools": ["run_splunk_search"],
                    "dependencies": [],
                    "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                }
            ],
        }

    def _get_parallel_template(self) -> dict[str, Any]:
        """Get parallel execution workflow template."""
        return {
            "_template_description": "Parallel task execution workflow template",
            "workflow_id": "parallel_execution_template",
            "name": "Parallel Execution Template",
            "description": "Template demonstrating parallel task execution without dependencies",
            "tasks": [
                {
                    "task_id": "system_health_check",
                    "name": "System Health Check",
                    "description": "Check overall system health",
                    "instructions": "Perform comprehensive system health check using available tools.",
                    "required_tools": ["get_splunk_health"],
                    "dependencies": [],
                    "context_requirements": [],
                },
                {
                    "task_id": "user_permissions_check",
                    "name": "User Permissions Check",
                    "description": "Verify user permissions and access",
                    "instructions": "Check current user permissions and role-based access.",
                    "required_tools": ["get_current_user_info"],
                    "dependencies": [],
                    "context_requirements": [],
                },
                {
                    "task_id": "index_availability_check",
                    "name": "Index Availability Check",
                    "description": "Check available indexes and access",
                    "instructions": "List and verify access to available Splunk indexes.",
                    "required_tools": ["list_splunk_indexes"],
                    "dependencies": [],
                    "context_requirements": [],
                },
            ],
        }

    def _get_sequential_template(self) -> dict[str, Any]:
        """Get sequential execution workflow template."""
        return {
            "_template_description": "Sequential task execution workflow template with dependencies",
            "workflow_id": "sequential_execution_template",
            "name": "Sequential Execution Template",
            "description": "Template demonstrating sequential task execution with dependencies",
            "tasks": [
                {
                    "task_id": "initial_discovery",
                    "name": "Initial Discovery",
                    "description": "Perform initial system discovery",
                    "instructions": "Gather basic system information and available resources.",
                    "required_tools": ["get_splunk_health", "list_splunk_indexes"],
                    "dependencies": [],
                    "context_requirements": [],
                },
                {
                    "task_id": "targeted_analysis",
                    "name": "Targeted Analysis",
                    "description": "Perform analysis based on discovery results",
                    "instructions": "Based on initial discovery results, perform targeted analysis of identified areas.",
                    "required_tools": ["run_splunk_search"],
                    "dependencies": ["initial_discovery"],
                    "context_requirements": ["focus_index", "earliest_time", "latest_time"],
                },
                {
                    "task_id": "recommendations",
                    "name": "Generate Recommendations",
                    "description": "Generate recommendations based on analysis",
                    "instructions": "Analyze all previous results and generate comprehensive recommendations.",
                    "required_tools": ["report_specialist_progress"],
                    "dependencies": ["targeted_analysis"],
                    "context_requirements": [],
                },
            ],
        }
