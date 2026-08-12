"""Load workflow JSON definitions without OpenAI / agents runtime."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .definitions import TaskDefinition, WorkflowDefinition

logger = logging.getLogger(__name__)


class WorkflowCatalog:
    """In-memory catalog of workflow definitions discovered from JSON files."""

    def __init__(self) -> None:
        self.workflows: dict[str, WorkflowDefinition] = {}

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register or replace a workflow by id."""
        self.workflows[workflow.workflow_id] = workflow

    def list_workflows(self) -> list[WorkflowDefinition]:
        """Return all registered workflows."""
        return list(self.workflows.values())

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Return one workflow by id."""
        return self.workflows.get(workflow_id)

    def load_directory(self, directory: str | Path) -> int:
        """Load ``*.json`` workflows under directory (recursive). Returns count."""
        root = Path(directory)
        if not root.exists():
            logger.warning("Workflow directory does not exist: %s", root)
            return 0

        loaded = 0
        for path in sorted(root.rglob("*.json")):
            if path.name.startswith("."):
                continue
            try:
                workflow = self._load_file(path)
            except Exception as exc:
                logger.warning("Skipping invalid workflow %s: %s", path, exc)
                continue
            self.register_workflow(workflow)
            loaded += 1
        return loaded

    def _load_file(self, path: Path) -> WorkflowDefinition:
        data = json.loads(path.read_text(encoding="utf-8"))
        tasks = [
            TaskDefinition(
                task_id=task["task_id"],
                name=task.get("name", task["task_id"]),
                description=task.get("description", ""),
                instructions=task.get("instructions", ""),
                required_tools=list(task.get("required_tools") or []),
                dependencies=list(task.get("dependencies") or []),
                context_requirements=list(task.get("context_requirements") or []),
                expected_output_format=task.get("expected_output_format", "diagnostic_result"),
                timeout_seconds=int(task.get("timeout_seconds", 300)),
            )
            for task in data.get("tasks") or []
        ]
        return WorkflowDefinition(
            workflow_id=data["workflow_id"],
            name=data.get("name", data["workflow_id"]),
            description=data.get("description", ""),
            tasks=tasks,
            default_context=dict(data.get("default_context") or {}),
        )


def build_default_catalog() -> WorkflowCatalog:
    """Load core + contrib workflow JSON into a catalog."""
    catalog = WorkflowCatalog()
    catalog.load_directory("src/tools/workflows/core")
    catalog.load_directory("contrib/workflows")
    return catalog
