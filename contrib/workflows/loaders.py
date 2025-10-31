"""Workflow Loader System

Automatic discovery and loading system for user-contributed workflows in the
contrib/workflows directory. Provides validation, error handling, and integration
with the WorkflowManager system.
"""

import json
import logging
import re  # Added for regex in _validate_task
from pathlib import Path
from typing import Any

from src.tools.workflows.shared.workflow_manager import TaskDefinition, WorkflowDefinition

logger = logging.getLogger(__name__)


class WorkflowLoadError(Exception):
    """Exception raised when workflow loading fails."""

    pass


class WorkflowLoader:
    """
    Workflow Loader for User-Contributed Workflows.

    This class provides automatic discovery and loading of user-contributed workflows
    from the contrib/workflows directory. It handles validation, error reporting,
    and integration with the existing WorkflowManager system.

    ## Key Features:
    - **Automatic Discovery**: Scans contrib/workflows for JSON workflow files
    - **Comprehensive Validation**: Validates structure, dependencies, and integration
    - **Error Handling**: Detailed error reporting and recovery
    - **Integration Support**: Seamless integration with WorkflowManager
    - **Category Organization**: Supports organized workflow categories

    ## Directory Structure:
    The loader expects workflows to be organized in categories:
    - contrib/workflows/security/
    - contrib/workflows/performance/
    - contrib/workflows/data_quality/
    - contrib/workflows/custom/

    ## Validation:
    - JSON structure validation
    - WorkflowDefinition schema compliance
    - Task dependency validation
    - Tool availability checking
    - Context variable validation

    ## Error Handling:
    - Invalid JSON files are skipped with detailed error logs
    - Validation errors are reported but don't stop other workflows
    - Circular dependencies are detected and reported
    - Missing tools are flagged as warnings
    """

    def __init__(self, workflows_directory: str = "contrib/workflows"):
        """
        Initialize the workflow loader.

        Args:
            workflows_directory: Base directory containing workflow files
        """
        self.workflows_directory = Path(workflows_directory)
        self.loaded_workflows: dict[str, WorkflowDefinition] = {}
        self.load_errors: list[dict[str, Any]] = []
        self.load_warnings: list[dict[str, Any]] = []

        # Available tools for validation
        self.available_tools = {
            "run_splunk_search",
            "run_oneshot_search",
            "run_saved_search",
            "list_splunk_indexes",
            "list_splunk_sources",
            "list_splunk_sourcetypes",
            "get_current_user_info",
            "get_splunk_health",
            "get_splunk_apps",
            "get_alert_status",
            "report_specialist_progress",
        }

        # Available context variables
        self.available_context = {
            "earliest_time",
            "latest_time",
            "focus_index",
            "focus_host",
            "focus_sourcetype",
            "complexity_level",
        }

    def discover_workflows(self) -> list[Path]:
        """
        Discover all workflow JSON files in the workflows directory.

        Returns:
            List of Path objects pointing to workflow JSON files
        """
        workflow_files = []

        # Directories to scan
        directories = [
            self.workflows_directory,  # contrib/workflows
            Path("src/tools/workflows/core/"),  # core workflows
        ]

        for dir_path in directories:
            if not dir_path.exists():
                logger.warning(f"Workflows directory not found: {dir_path}")
                continue

            # Search for JSON files in all subdirectories
            for json_file in dir_path.rglob("*.json"):
                # Skip hidden files and directories
                if any(part.startswith(".") for part in json_file.parts):
                    continue

                workflow_files.append(json_file)
                logger.debug(f"Discovered workflow file: {json_file}")

        logger.info(f"Discovered {len(workflow_files)} workflow files")
        return workflow_files

    def load_all_workflows(self) -> dict[str, WorkflowDefinition]:
        """
        Load all discovered workflows with validation and error handling.

        Returns:
            Dictionary mapping workflow_id to WorkflowDefinition objects
        """
        logger.info("Starting workflow loading process...")

        # Clear previous state
        self.loaded_workflows.clear()
        self.load_errors.clear()
        self.load_warnings.clear()

        # Discover workflow files
        workflow_files = self.discover_workflows()

        if not workflow_files:
            logger.warning("No workflow files found")
            return self.loaded_workflows

        # Load each workflow file
        for workflow_file in workflow_files:
            try:
                workflow = self.load_workflow_file(workflow_file)
                if workflow:
                    self.loaded_workflows[workflow.workflow_id] = workflow
                    logger.info(f"Successfully loaded workflow: {workflow.workflow_id}")
            except Exception as e:
                error = {"file": str(workflow_file), "error": str(e), "type": type(e).__name__}
                self.load_errors.append(error)
                logger.error(f"Failed to load workflow from {workflow_file}: {e}")

        # Report loading summary
        self._log_loading_summary()

        return self.loaded_workflows

    def load_workflow_file(self, file_path: Path) -> WorkflowDefinition | None:
        """
        Load a single workflow file with validation.

        Args:
            file_path: Path to the workflow JSON file

        Returns:
            WorkflowDefinition object if successful, None if failed

        Raises:
            WorkflowLoadError: If the workflow cannot be loaded or validated
        """
        try:
            # Read and parse JSON
            with open(file_path, encoding="utf-8") as f:
                workflow_data = json.load(f)

            # Validate structure
            validation_result = self._validate_workflow_structure(workflow_data, file_path)

            if not validation_result["valid"]:
                # Log errors but continue with warnings
                for error in validation_result["errors"]:
                    self.load_errors.append(
                        {"file": str(file_path), "error": error, "type": "ValidationError"}
                    )

                if validation_result["errors"]:
                    raise WorkflowLoadError(f"Validation failed: {validation_result['errors'][0]}")

            # Log warnings
            for warning in validation_result["warnings"]:
                self.load_warnings.append(
                    {"file": str(file_path), "warning": warning, "type": "ValidationWarning"}
                )

            # Convert to WorkflowDefinition
            workflow = self._create_workflow_definition(workflow_data, file_path)

            logger.debug(f"Successfully loaded and validated workflow: {workflow.workflow_id}")
            return workflow

        except json.JSONDecodeError as e:
            raise WorkflowLoadError(f"Invalid JSON format: {e}") from e
        except FileNotFoundError:
            # File truly missing; suppress underlying stack to keep error concise
            raise WorkflowLoadError(f"File not found: {file_path}") from None
        except Exception as e:
            raise WorkflowLoadError(f"Unexpected error loading workflow: {e}") from e

    def _validate_workflow_structure(
        self, workflow_data: dict[str, Any], file_path: Path
    ) -> dict[str, Any]:
        """
        Validate workflow structure and content.

        Args:
            workflow_data: Parsed workflow JSON data
            file_path: Path to the workflow file (for error reporting)

        Returns:
            Dictionary with validation results
        """
        errors = []
        warnings = []

        # Required fields validation
        required_fields = ["workflow_id", "name", "description", "tasks"]
        for field in required_fields:
            if field not in workflow_data:
                errors.append(f"Missing required field: {field}")

        # Workflow ID validation
        if "workflow_id" in workflow_data:
            workflow_id = workflow_data["workflow_id"]
            if not isinstance(workflow_id, str):
                errors.append("workflow_id must be a string")
            elif not workflow_id.replace("_", "").replace("-", "").isalnum():
                errors.append(
                    "workflow_id must contain only alphanumeric characters, underscores, and hyphens"
                )
            elif len(workflow_id) > 50:
                errors.append("workflow_id must be 50 characters or less")

        # Tasks validation
        if "tasks" in workflow_data:
            tasks = workflow_data["tasks"]
            if not isinstance(tasks, list):
                errors.append("tasks must be a list")
            elif len(tasks) == 0:
                errors.append("workflow must contain at least one task")
            else:
                # Validate individual tasks
                task_ids = set()
                for i, task in enumerate(tasks):
                    task_errors, task_warnings = self._validate_task(task, i)
                    errors.extend(task_errors)
                    warnings.extend(task_warnings)

                    # Check for duplicate task IDs
                    if isinstance(task, dict) and "task_id" in task:
                        task_id = task["task_id"]
                        if task_id in task_ids:
                            errors.append(f"Duplicate task_id: {task_id}")
                        task_ids.add(task_id)

                # Validate dependencies
                dep_errors, dep_warnings = self._validate_dependencies(tasks)
                errors.extend(dep_errors)
                warnings.extend(dep_warnings)

        # Tool validation
        tool_errors, tool_warnings = self._validate_tools(workflow_data)
        errors.extend(tool_errors)
        warnings.extend(tool_warnings)

        # Context validation
        context_errors, context_warnings = self._validate_context(workflow_data)
        errors.extend(context_errors)
        warnings.extend(context_warnings)

        # Performance limits
        if "tasks" in workflow_data and len(workflow_data["tasks"]) > 20:
            warnings.append(
                "Workflow has more than 20 tasks - consider splitting for better performance"
            )

        # Add suggestions based on errors
        suggestions = []
        if errors:
            if any("Missing required field" in e for e in errors):
                suggestions.append(
                    "Ensure all required fields are present: workflow_id, name, description, tasks"
                )
            if any("Duplicate task_id" in e for e in errors):
                suggestions.append("Make task_ids unique within the workflow")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    def _validate_task(self, task: Any, index: int) -> tuple[list[str], list[str]]:
        """Validate individual task structure."""
        errors = []
        warnings = []

        if not isinstance(task, dict):
            errors.append(f"Task {index}: must be an object")
            return errors, warnings

        # Required fields
        required_fields = ["task_id", "name", "description", "instructions"]
        for field in required_fields:
            if field not in task:
                errors.append(f"Task {index}: Missing required field '{field}'")

        # Task ID validation
        if "task_id" in task:
            task_id = task["task_id"]
            if not isinstance(task_id, str):
                errors.append(f"Task {index}: task_id must be a string")
            elif not task_id.replace("_", "").replace("-", "").isalnum():
                errors.append(
                    f"Task {index}: task_id must contain only alphanumeric characters, underscores, and hyphens"
                )
            elif len(task_id) > 50:
                errors.append(f"Task {index}: task_id must be 50 characters or less")

        # Instructions validation
        if "instructions" in task:
            instructions = task["instructions"]
            if not isinstance(instructions, str):
                errors.append(f"Task {index}: instructions must be a string")
            elif len(instructions.strip()) < 20:
                warnings.append(f"Task {index}: instructions seem very brief")

        # Instruction alignment checks
        if "instructions" in task and isinstance(task["instructions"], str):
            instructions = task["instructions"]

            # Check for context vars
            used_vars = set(re.findall(r"\{(\w+)\}", instructions))
            required_context = set(task.get("context_requirements", []))
            missing_context = required_context - used_vars
            if missing_context:
                warnings.append(
                    f"Task {index}: Required context {missing_context} not used in instructions"
                )

            # Check for tools
            required_tools = set(task.get("required_tools", []))
            mentioned_tools = {tool for tool in required_tools if tool in instructions}
            missing_tools = required_tools - mentioned_tools
            if missing_tools:
                warnings.append(
                    f"Task {index}: Required tools {missing_tools} not mentioned in instructions"
                )

        # Basic security scan
        dangerous_keywords = {"delete", "rm", "drop", "shutdown", "restart"}
        if "instructions" in task and any(
            kw in task["instructions"].lower() for kw in dangerous_keywords
        ):
            warnings.append(f"Task {index}: Instructions contain potentially dangerous keywords")

        # Optional fields validation
        if "required_tools" in task:
            tools = task["required_tools"]
            if not isinstance(tools, list):
                errors.append(f"Task {index}: required_tools must be a list")

        if "dependencies" in task:
            deps = task["dependencies"]
            if not isinstance(deps, list):
                errors.append(f"Task {index}: dependencies must be a list")

        if "context_requirements" in task:
            context = task["context_requirements"]
            if not isinstance(context, list):
                errors.append(f"Task {index}: context_requirements must be a list")

        return errors, warnings

    def _validate_dependencies(self, tasks: list[Any]) -> tuple[list[str], list[str]]:
        """Validate task dependencies and detect circular dependencies."""
        errors = []
        warnings = []

        # Build task ID map
        task_ids = set()
        for task in tasks:
            if isinstance(task, dict) and "task_id" in task:
                task_ids.add(task["task_id"])

        # Check dependency references
        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_id = task.get("task_id", "unknown")
            dependencies = task.get("dependencies", [])

            if not isinstance(dependencies, list):
                continue

            for dep in dependencies:
                if not isinstance(dep, str):
                    errors.append(f"Task '{task_id}': dependency must be a string")
                elif dep not in task_ids:
                    errors.append(f"Task '{task_id}': dependency '{dep}' not found in workflow")

        # Check for circular dependencies
        if not errors:  # Only check if basic validation passed
            circular_deps = self._detect_circular_dependencies(tasks)
            if circular_deps:
                errors.append(f"Circular dependencies detected: {' -> '.join(circular_deps)}")

        return errors, warnings

    def _detect_circular_dependencies(self, tasks: list[dict[str, Any]]) -> list[str] | None:
        """Detect circular dependencies using DFS."""
        # Build adjacency list
        graph = {}
        for task in tasks:
            if isinstance(task, dict) and "task_id" in task:
                task_id = task["task_id"]
                dependencies = task.get("dependencies", [])
                graph[task_id] = dependencies

        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> list[str] | None:
            if node not in graph:
                return None

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph[node]:
                if neighbor not in visited:
                    result = dfs(neighbor)
                    if result:
                        return result
                elif neighbor in rec_stack:
                    # Found cycle - return the cycle path
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        for node in graph:
            if node not in visited:
                cycle = dfs(node)
                if cycle:
                    return cycle

        return None

    def _validate_tools(self, workflow_data: dict[str, Any]) -> tuple[list[str], list[str]]:
        from src.core.discovery import discover_tools  # Import here to avoid circular imports
        from src.core.registry import tool_registry  # Import here to avoid circular imports

        errors = []
        warnings = []

        # Get dynamic list of available tools
        available_tools = {tool_metadata.name for tool_metadata in tool_registry.list_tools()}

        # If no tools found, try to discover them
        if not available_tools:
            try:
                discover_tools()
                available_tools = {
                    tool_metadata.name for tool_metadata in tool_registry.list_tools()
                }
            except Exception as e:
                logger.warning(f"Failed to discover tools: {e}")

        for i, task in enumerate(workflow_data.get("tasks", [])):
            required_tools = task.get("required_tools", [])
            for tool in required_tools:
                if tool not in available_tools:
                    errors.append(
                        f"Task {i} ({task.get('task_id', 'unknown')}): unknown tool '{tool}'"
                    )

        return errors, warnings

    def _validate_context(self, workflow_data: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Validate context variable usage."""
        errors = []
        warnings = []

        # Dynamic available context: base known vars + default_context keys
        base_context = {
            "earliest_time",
            "latest_time",
            "focus_index",
            "focus_host",
            "focus_sourcetype",
            "complexity_level",
            "problem_description",
        }
        default_context = set(workflow_data.get("default_context", {}).keys())
        available_context = base_context.union(default_context)

        for task in workflow_data.get("tasks", []):
            if not isinstance(task, dict):
                continue

            task_id = task.get("task_id", "unknown")
            context_requirements = task.get("context_requirements", [])

            if not isinstance(context_requirements, list):
                continue

            for var in context_requirements:
                if not isinstance(var, str):
                    errors.append(f"Task '{task_id}': context variable name must be a string")
                elif var not in available_context:
                    warnings.append(
                        f"Task '{task_id}': context variable '{var}' may not be available"
                    )

        return errors, warnings

    def _create_workflow_definition(
        self, workflow_data: dict[str, Any], file_path: Path
    ) -> WorkflowDefinition:
        """
        Create a WorkflowDefinition object from validated workflow data.

        Args:
            workflow_data: Validated workflow JSON data
            file_path: Path to the workflow file (for metadata)

        Returns:
            WorkflowDefinition object
        """
        # Create task definitions
        tasks = []
        for task_data in workflow_data.get("tasks", []):
            task_def = TaskDefinition(
                task_id=task_data["task_id"],
                name=task_data["name"],
                description=task_data["description"],
                instructions=task_data["instructions"],
                required_tools=task_data.get("required_tools", []),
                dependencies=task_data.get("dependencies", []),
                context_requirements=task_data.get("context_requirements", []),
            )
            tasks.append(task_def)

        # Create workflow definition
        workflow_def = WorkflowDefinition(
            workflow_id=workflow_data["workflow_id"],
            name=workflow_data["name"],
            description=workflow_data["description"],
            tasks=tasks,
            default_context=workflow_data.get("default_context", {}),
        )

        return workflow_def

    def _log_loading_summary(self):
        """Log a summary of the workflow loading process."""
        total_workflows = len(self.loaded_workflows)
        total_errors = len(self.load_errors)
        total_warnings = len(self.load_warnings)

        logger.info("Workflow loading summary:")
        logger.info(f"  Successfully loaded: {total_workflows} workflows")
        logger.info(f"  Errors encountered: {total_errors}")
        logger.info(f"  Warnings generated: {total_warnings}")

        if self.loaded_workflows:
            logger.info("  Loaded workflows:")
            for workflow_id, workflow in self.loaded_workflows.items():
                logger.info(f"    - {workflow_id}: {workflow.name} ({len(workflow.tasks)} tasks)")

        if self.load_errors:
            logger.warning("  Loading errors:")
            for error in self.load_errors:
                logger.warning(f"    - {error['file']}: {error['error']}")

        if self.load_warnings:
            logger.info("  Loading warnings:")
            for warning in self.load_warnings:
                logger.info(f"    - {warning['file']}: {warning['warning']}")

    def get_loading_report(self) -> dict[str, Any]:
        """
        Get a detailed report of the workflow loading process.

        Returns:
            Dictionary containing loading statistics and details
        """
        return {
            "summary": {
                "total_loaded": len(self.loaded_workflows),
                "total_errors": len(self.load_errors),
                "total_warnings": len(self.load_warnings),
            },
            "loaded_workflows": [
                {
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "description": workflow.description,
                    "task_count": len(workflow.tasks),
                    "has_dependencies": any(task.dependencies for task in workflow.tasks),
                }
                for workflow in self.loaded_workflows.values()
            ],
            "errors": self.load_errors,
            "warnings": self.load_warnings,
        }

    def register_workflows_with_manager(self, workflow_manager) -> int:
        """
        Register all loaded workflows with a WorkflowManager instance.

        Args:
            workflow_manager: WorkflowManager instance to register workflows with

        Returns:
            Number of workflows successfully registered
        """
        registered_count = 0

        for workflow_id, workflow in self.loaded_workflows.items():
            try:
                workflow_manager.register_workflow(workflow)
                registered_count += 1
                logger.debug(f"Registered workflow with manager: {workflow_id}")
            except Exception as e:
                logger.error(f"Failed to register workflow '{workflow_id}' with manager: {e}")

        logger.info(
            f"Registered {registered_count} user-contributed workflows with WorkflowManager"
        )
        return registered_count


# Convenience functions for easy integration


def load_user_workflows(
    workflows_directory: str = "contrib/workflows",
) -> dict[str, WorkflowDefinition]:
    """
    Convenience function to load all user-contributed workflows.

    Args:
        workflows_directory: Directory containing workflow files

    Returns:
        Dictionary mapping workflow_id to WorkflowDefinition objects
    """
    loader = WorkflowLoader(workflows_directory)
    return loader.load_all_workflows()


def load_and_register_workflows(
    workflow_manager, workflows_directory: str = "contrib/workflows"
) -> int:
    """
    Convenience function to load and register workflows with a WorkflowManager.

    Args:
        workflow_manager: WorkflowManager instance to register workflows with
        workflows_directory: Directory containing workflow files

    Returns:
        Number of workflows successfully registered
    """
    loader = WorkflowLoader(workflows_directory)
    loader.load_all_workflows()
    return loader.register_workflows_with_manager(workflow_manager)


def validate_workflow_file(file_path: str) -> dict[str, Any]:
    """
    Convenience function to validate a single workflow file.

    Args:
        file_path: Path to the workflow JSON file

    Returns:
        Dictionary with validation results
    """
    loader = WorkflowLoader()
    try:
        with open(file_path, encoding="utf-8") as f:
            workflow_data = json.load(f)
        return loader._validate_workflow_structure(workflow_data, Path(file_path))
    except Exception as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}
