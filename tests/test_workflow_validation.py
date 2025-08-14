import pytest

from contrib.workflows.loaders import WorkflowLoader


@pytest.fixture
def workflow_loader():
    return WorkflowLoader()


def test_dynamic_context_validation(workflow_loader):
    workflow_data = {
        "default_context": {"custom_var": "value"},
        "tasks": [{"context_requirements": ["custom_var", "earliest_time", "unknown_var"]}],
    }
    result = workflow_loader._validate_context(workflow_data)
    assert len(result[0]) == 0  # No errors
    assert "unknown_var" in " ".join(result[1])  # Warning for unknown


def test_instruction_alignment_checks(workflow_loader):
    task = {
        "instructions": "Use {var1} and tool1",
        "context_requirements": ["var1", "var2"],
        "required_tools": ["tool1", "tool2"],
    }
    errors, warnings = workflow_loader._validate_task(task, 0)
    assert "var2" in " ".join(warnings)  # Missing context use
    assert "tool2" in " ".join(warnings)  # Missing tool mention


def test_performance_limits(workflow_loader):
    workflow_data = {"tasks": [{} for _ in range(25)]}  # 25 tasks
    result = workflow_loader._validate_workflow_structure(workflow_data, "test.json")
    assert "more than 20 tasks" in " ".join(result["warnings"])


def test_error_suggestions(workflow_loader):
    workflow_data = {}  # Missing all fields
    result = workflow_loader._validate_workflow_structure(workflow_data, "test.json")
    assert "Ensure all required fields" in " ".join(result["suggestions"])


def test_security_scan(workflow_loader):
    task = {"instructions": "Run | delete command"}
    errors, warnings = workflow_loader._validate_task(task, 0)
    assert "dangerous keywords" in " ".join(warnings)
