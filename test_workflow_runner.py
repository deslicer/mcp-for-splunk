#!/usr/bin/env python3

import os
import sys

# Set a dummy API key for testing
os.environ["OPENAI_API_KEY"] = "dummy_key_for_testing"

from src.tools.workflows.shared.workflow_manager import WorkflowManager
from src.tools.workflows.shared.config import AgentConfig
from src.tools.workflows.shared.tools import SplunkToolRegistry

def test_workflow_loading():
    print("Testing workflow loading...")
    print("=" * 50)
    
    # Create config and tool registry
    config = AgentConfig(
        api_key="dummy",
        model="gpt-4o",
        temperature=0.7,
        max_tokens=4000
    )
    tool_registry = SplunkToolRegistry()
    
    # Create workflow manager
    workflow_manager = WorkflowManager(config, tool_registry)
    
    # List all workflows
    workflows = workflow_manager.list_workflows()
    
    print(f"✅ Total workflows loaded: {len(workflows)}")
    print("\nWorkflow details:")
    
    core_workflows = []
    contrib_workflows = []
    
    for workflow in workflows:
        # Try to determine if it's core or contrib based on workflow_id
        if workflow.workflow_id in ["missing_data_troubleshooting", "performance_analysis"]:
            core_workflows.append(workflow)
        else:
            contrib_workflows.append(workflow)
        
        print(f"  - {workflow.workflow_id}: {workflow.name} ({len(workflow.tasks)} tasks)")
    
    print(f"\n📊 Summary:")
    print(f"  - Core workflows: {len(core_workflows)}")
    print(f"  - Contrib workflows: {len(contrib_workflows)}")
    
    # Check if simple_health_check is available
    simple_health_check = workflow_manager.get_workflow("simple_health_check")
    if simple_health_check:
        print(f"\n✅ simple_health_check workflow found!")
        print(f"  - Name: {simple_health_check.name}")
        print(f"  - Description: {simple_health_check.description}")
        print(f"  - Tasks: {len(simple_health_check.tasks)}")
    else:
        print(f"\n❌ simple_health_check workflow NOT found!")
        
        # List all available workflow IDs
        available_ids = [w.workflow_id for w in workflows]
        print(f"  Available workflow IDs: {available_ids}")

if __name__ == "__main__":
    test_workflow_loading()
