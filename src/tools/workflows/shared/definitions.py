"""Workflow definition dataclasses (no LLM / agents dependencies)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskDefinition:
    """Definition of a task within a workflow JSON document."""

    task_id: str
    name: str
    description: str
    instructions: str
    required_tools: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    context_requirements: list[str] = field(default_factory=list)
    expected_output_format: str = "diagnostic_result"
    timeout_seconds: int = 300


@dataclass
class WorkflowDefinition:
    """Definition of a workflow containing multiple tasks."""

    workflow_id: str
    name: str
    description: str
    tasks: list[TaskDefinition]
    default_context: dict[str, Any] = field(default_factory=dict)
