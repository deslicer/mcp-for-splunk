#!/usr/bin/env python3
"""
Test script for the parallel execution system.

This script validates that the parallel execution architecture is working correctly
without requiring a full Splunk environment or API keys.
"""

import asyncio
import sys
import os
import time
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from tools.agents.shared.workflow_manager import WorkflowManager, WorkflowDefinition
    from tools.agents.shared.parallel_executor import ParallelWorkflowExecutor
    from tools.agents.shared.config import AgentConfig
    from tools.agents.shared.tools import SplunkToolRegistry
    from tools.agents.shared.context import SplunkDiagnosticContext
    from tools.agents.summarization_tool import create_summarization_tool
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

class MockContext:
    """Mock FastMCP context for testing."""
    
    def __init__(self):
        self.progress = 0
        self.total = 100
        self.messages = []
    
    async def report_progress(self, progress: int, total: int):
        self.progress = progress
        self.total = total
        print(f"📊 Progress: {progress}/{total} ({progress/total*100:.1f}%)")
    
    async def info(self, message: str):
        self.messages.append(('info', message))
        print(f"ℹ️  {message}")
    
    async def warning(self, message: str):
        self.messages.append(('warning', message))
        print(f"⚠️  {message}")
    
    async def error(self, message: str):
        self.messages.append(('error', message))
        print(f"❌ {message}")

async def test_workflow_manager():
    """Test WorkflowManager initialization and workflow retrieval."""
    print("\n" + "="*60)
    print("TESTING WORKFLOW MANAGER")
    print("="*60)
    
    try:
        # Create mock config
        config = AgentConfig(
            api_key="test-key",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4000
        )
        
        # Create tool registry
        tool_registry = SplunkToolRegistry()
        
        # Initialize WorkflowManager
        workflow_manager = WorkflowManager(config=config, tool_registry=tool_registry)
        print(f"✅ WorkflowManager initialized with {len(workflow_manager.workflows)} workflows")
        
        # Test workflow retrieval
        workflows = workflow_manager.list_workflows()
        print(f"✅ Found {len(workflows)} workflows:")
        for workflow in workflows:
            print(f"   - {workflow.workflow_id}: {workflow.name} ({len(workflow.tasks)} tasks)")
        
        # Test specific workflow retrieval
        missing_data_workflow = workflow_manager.get_workflow("missing_data_troubleshooting")
        if missing_data_workflow:
            print(f"✅ Retrieved missing_data_troubleshooting workflow with {len(missing_data_workflow.tasks)} tasks")
        else:
            print("❌ Failed to retrieve missing_data_troubleshooting workflow")
        
        return workflow_manager
        
    except Exception as e:
        print(f"❌ WorkflowManager test failed: {e}")
        return None

async def test_parallel_executor():
    """Test ParallelWorkflowExecutor initialization."""
    print("\n" + "="*60)
    print("TESTING PARALLEL EXECUTOR")
    print("="*60)
    
    try:
        # Create mock config
        config = AgentConfig(
            api_key="test-key",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4000
        )
        
        # Create tool registry
        tool_registry = SplunkToolRegistry()
        
        # Initialize ParallelWorkflowExecutor
        parallel_executor = ParallelWorkflowExecutor(config=config, tool_registry=tool_registry)
        print("✅ ParallelWorkflowExecutor initialized successfully")
        
        return parallel_executor
        
    except Exception as e:
        print(f"❌ ParallelWorkflowExecutor test failed: {e}")
        return None

async def test_summarization_tool():
    """Test SummarizationTool initialization."""
    print("\n" + "="*60)
    print("TESTING SUMMARIZATION TOOL")
    print("="*60)
    
    try:
        # Create mock config
        config = AgentConfig(
            api_key="test-key",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4000
        )
        
        # Create tool registry
        tool_registry = SplunkToolRegistry()
        
        # Initialize SummarizationTool
        summarization_tool = create_summarization_tool(config=config, tool_registry=tool_registry)
        print("✅ SummarizationTool initialized successfully")
        
        return summarization_tool
        
    except Exception as e:
        print(f"❌ SummarizationTool test failed: {e}")
        return None

async def test_dependency_analysis():
    """Test dependency analysis and phase creation."""
    print("\n" + "="*60)
    print("TESTING DEPENDENCY ANALYSIS")
    print("="*60)
    
    try:
        # Create mock config and registry
        config = AgentConfig(api_key="test-key", model="gpt-4o", temperature=0.7, max_tokens=4000)
        tool_registry = SplunkToolRegistry()
        
        # Initialize WorkflowManager
        workflow_manager = WorkflowManager(config=config, tool_registry=tool_registry)
        
        # Get a workflow for testing
        workflow = workflow_manager.get_workflow("missing_data_troubleshooting")
        if not workflow:
            print("❌ Could not retrieve workflow for dependency testing")
            return False
        
        print(f"✅ Testing dependency analysis for {workflow.name}")
        print(f"   Total tasks: {len(workflow.tasks)}")
        
        # Test dependency graph building
        dependency_graph = workflow_manager._build_dependency_graph(workflow.tasks)
        print(f"✅ Built dependency graph with {len(dependency_graph)} entries")
        
        # Test execution phase creation
        execution_phases = workflow_manager._create_execution_phases(workflow.tasks, dependency_graph)
        print(f"✅ Created {len(execution_phases)} execution phases")
        
        for i, phase in enumerate(execution_phases):
            print(f"   Phase {i+1}: {len(phase)} tasks - {phase}")
        
        # Calculate parallel efficiency
        efficiency = workflow_manager._calculate_parallel_efficiency(workflow.tasks, execution_phases)
        print(f"✅ Parallel efficiency: {efficiency:.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Dependency analysis test failed: {e}")
        return False

async def test_diagnostic_context():
    """Test SplunkDiagnosticContext creation."""
    print("\n" + "="*60)
    print("TESTING DIAGNOSTIC CONTEXT")
    print("="*60)
    
    try:
        # Create diagnostic context
        diagnostic_context = SplunkDiagnosticContext(
            earliest_time="-24h",
            latest_time="now",
            focus_index="test_index",
            focus_host="test_host",
            complexity_level="moderate"
        )
        
        print(f"✅ Created diagnostic context:")
        print(f"   Time range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}")
        print(f"   Focus index: {diagnostic_context.focus_index}")
        print(f"   Focus host: {diagnostic_context.focus_host}")
        print(f"   Complexity: {diagnostic_context.complexity_level}")
        
        return diagnostic_context
        
    except Exception as e:
        print(f"❌ Diagnostic context test failed: {e}")
        return None

async def run_all_tests():
    """Run all tests and report results."""
    print("🚀 STARTING PARALLEL EXECUTION SYSTEM TESTS")
    print("="*80)
    
    start_time = time.time()
    test_results = {}
    
    # Test 1: WorkflowManager
    workflow_manager = await test_workflow_manager()
    test_results['workflow_manager'] = workflow_manager is not None
    
    # Test 2: ParallelWorkflowExecutor
    parallel_executor = await test_parallel_executor()
    test_results['parallel_executor'] = parallel_executor is not None
    
    # Test 3: SummarizationTool
    summarization_tool = await test_summarization_tool()
    test_results['summarization_tool'] = summarization_tool is not None
    
    # Test 4: Dependency Analysis
    dependency_success = await test_dependency_analysis()
    test_results['dependency_analysis'] = dependency_success
    
    # Test 5: Diagnostic Context
    diagnostic_context = await test_diagnostic_context()
    test_results['diagnostic_context'] = diagnostic_context is not None
    
    # Summary
    total_time = time.time() - start_time
    passed = sum(test_results.values())
    total = len(test_results)
    
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"Total execution time: {total_time:.2f} seconds")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Parallel execution system is ready for use.")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please review the errors above.")
        return False

if __name__ == "__main__":
    # Set environment variables for testing
    os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")
    os.environ.setdefault("OPENAI_MODEL", "gpt-4o")
    
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1) 