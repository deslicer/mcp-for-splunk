#!/usr/bin/env python3
"""
Test script for Enhanced Dynamic Troubleshoot Agent with Orchestration and Tracing

This script demonstrates the complete functionality of the enhanced dynamic troubleshoot agent,
including orchestration, tracing, and workflow execution.
"""

import os
import asyncio
import logging
import time
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock FastMCP Context for testing
class MockContext:
    """Mock FastMCP context for testing purposes."""
    
    def __init__(self):
        self.progress_reports = []
        self.info_messages = []
        self.error_messages = []
    
    async def report_progress(self, progress: int, total: int):
        self.progress_reports.append((progress, total))
        logger.info(f"Progress: {progress}/{total} ({progress/total*100:.1f}%)")
    
    async def info(self, message: str):
        self.info_messages.append(message)
        logger.info(f"INFO: {message}")
    
    async def error(self, message: str):
        self.error_messages.append(message)
        logger.error(f"ERROR: {message}")


def setup_test_environment():
    """Set up test environment with required environment variables."""
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not found. Setting mock key for testing.")
        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing"
    
    # Set other OpenAI configuration
    os.environ.setdefault("OPENAI_MODEL", "gpt-4o")
    os.environ.setdefault("OPENAI_TEMPERATURE", "0.7")
    os.environ.setdefault("OPENAI_MAX_TOKENS", "4000")
    
    # Set retry configuration
    os.environ.setdefault("OPENAI_MAX_RETRIES", "3")
    os.environ.setdefault("OPENAI_RETRY_BASE_DELAY", "1.0")
    os.environ.setdefault("OPENAI_RETRY_MAX_DELAY", "60.0")
    
    logger.info("Test environment setup complete")


async def test_dynamic_troubleshoot_agent():
    """Test the enhanced dynamic troubleshoot agent functionality."""
    
    logger.info("="*80)
    logger.info("TESTING ENHANCED DYNAMIC TROUBLESHOOT AGENT")
    logger.info("="*80)
    
    try:
        # Import the enhanced agent (this will test the imports)
        from src.tools.agents.dynamic_troubleshoot_agent import DynamicTroubleshootAgentTool
        logger.info("✅ Successfully imported DynamicTroubleshootAgentTool")
        
        # Create the agent
        logger.info("Creating enhanced dynamic troubleshoot agent...")
        agent = DynamicTroubleshootAgentTool("dynamic_troubleshoot", "troubleshooting")
        logger.info("✅ Agent created successfully")
        
        # Test problem analysis
        logger.info("\n" + "="*60)
        logger.info("TESTING PROBLEM ANALYSIS")
        logger.info("="*60)
        
        test_problems = [
            "My dashboard shows no data for the last 2 hours",
            "Searches are running very slowly since yesterday", 
            "High CPU usage on search heads affecting performance",
            "Quick health check of the system"
        ]
        
        for problem in test_problems:
            detected_type = agent._analyze_problem_type(problem)
            logger.info(f"Problem: '{problem}' → Detected: {detected_type}")
        
        # Test orchestration input creation
        logger.info("\n" + "="*60)
        logger.info("TESTING ORCHESTRATION INPUT CREATION")
        logger.info("="*60)
        
        # Mock workflow result for testing
        mock_workflow_result = {
            "status": "success",
            "coordinator_type": "dynamic_missing_data",
            "task_results": [
                {
                    "task": "license_verification",
                    "status": "healthy",
                    "execution_time": 1.2,
                    "findings": ["License is valid", "Running Enterprise edition"],
                    "recommendations": ["Monitor license usage"]
                },
                {
                    "task": "index_verification", 
                    "status": "warning",
                    "execution_time": 2.1,
                    "findings": ["Index 'security' not found", "Index 'main' accessible"],
                    "recommendations": ["Create missing security index", "Check forwarder configuration"]
                }
            ],
            "summary": {"overall_health": "warning", "critical_issues": 1},
            "performance_metrics": {
                "total_execution_time": 5.3,
                "tasks_completed": 2,
                "successful_tasks": 1,
                "failed_tasks": 0,
                "parallel_phases": 1
            }
        }
        
        # Mock diagnostic context
        from src.tools.agents.shared.context import SplunkDiagnosticContext
        mock_context = SplunkDiagnosticContext(
            earliest_time="-24h",
            latest_time="now",
            focus_index="security",
            focus_host=None,
            complexity_level="moderate"
        )
        
        orchestration_input = agent._create_orchestration_input(
            "Dashboard shows no data",
            mock_workflow_result,
            mock_context
        )
        
        logger.info(f"✅ Orchestration input created successfully")
        logger.info(f"Input length: {len(orchestration_input)} characters")
        logger.info(f"Input preview: {orchestration_input[:200]}...")
        
        # Test workflow availability
        logger.info("\n" + "="*60)
        logger.info("TESTING WORKFLOW AVAILABILITY")
        logger.info("="*60)
        
        available_workflows = agent.dynamic_coordinator.list_available_workflows()
        logger.info(f"Available workflows: {len(available_workflows)}")
        
        for workflow in available_workflows:
            logger.info(f"  - {workflow['workflow_id']}: {workflow['name']}")
            logger.info(f"    Tasks: {workflow['total_tasks']}, Phases: {workflow['execution_phases']}")
            logger.info(f"    Efficiency: {workflow['parallel_efficiency']:.1%}")
        
        logger.info("\n" + "="*60)
        logger.info("TESTING COMPLETE - BASIC FUNCTIONALITY VERIFIED")
        logger.info("="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


async def test_workflow_execution_simulation():
    """Simulate workflow execution without requiring actual Splunk connection."""
    
    logger.info("\n" + "="*80)
    logger.info("SIMULATING WORKFLOW EXECUTION")
    logger.info("="*80)
    
    try:
        # Import required classes
        from src.tools.agents.shared.config import AgentConfig
        from src.tools.agents.shared.tools import SplunkToolRegistry
        from src.tools.agents.shared.workflow_manager import WorkflowManager
        from src.tools.agents.shared.context import SplunkDiagnosticContext
        
        # Create mock configuration
        config = AgentConfig(
            api_key="mock-key",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4000
        )
        
        # Create tool registry
        tool_registry = SplunkToolRegistry()
        
        # Create workflow manager
        workflow_manager = WorkflowManager(config, tool_registry)
        logger.info("✅ Workflow manager created successfully")
        
        # List available workflows
        workflows = workflow_manager.list_workflows()
        logger.info(f"Available workflows: {len(workflows)}")
        
        for workflow in workflows:
            logger.info(f"  - {workflow.workflow_id}: {workflow.name}")
            logger.info(f"    Description: {workflow.description}")
            logger.info(f"    Tasks: {len(workflow.tasks)}")
            
            # Show task details
            for task in workflow.tasks:
                logger.info(f"      * {task.task_id}: {task.name}")
                logger.info(f"        Dependencies: {task.dependencies}")
                logger.info(f"        Tools: {task.required_tools}")
        
        # Test dependency analysis
        logger.info("\n" + "="*60)
        logger.info("TESTING DEPENDENCY ANALYSIS")
        logger.info("="*60)
        
        missing_data_workflow = workflow_manager.get_workflow("missing_data_troubleshooting")
        if missing_data_workflow:
            dependency_graph = workflow_manager._build_dependency_graph(missing_data_workflow.tasks)
            logger.info(f"Dependency graph: {dependency_graph}")
            
            execution_phases = workflow_manager._create_execution_phases(
                missing_data_workflow.tasks, dependency_graph
            )
            logger.info(f"Execution phases: {len(execution_phases)}")
            for i, phase in enumerate(execution_phases):
                logger.info(f"  Phase {i+1}: {phase}")
            
            parallel_efficiency = workflow_manager._calculate_parallel_efficiency(
                missing_data_workflow.tasks, execution_phases
            )
            logger.info(f"Parallel efficiency: {parallel_efficiency:.1%}")
        
        logger.info("✅ Workflow execution simulation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Workflow simulation failed: {e}", exc_info=True)
        return False


async def test_tracing_availability():
    """Test tracing capabilities availability."""
    
    logger.info("\n" + "="*80)
    logger.info("TESTING TRACING CAPABILITIES")
    logger.info("="*80)
    
    try:
        # Test OpenAI Agents SDK availability
        try:
            from agents import Agent, Runner, function_tool, trace, span
            from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
            logger.info("✅ OpenAI Agents SDK available")
            
            # Test tracing imports
            try:
                from agents.tracing import TraceProvider, add_trace_processor, set_trace_processors
                logger.info("✅ OpenAI Agents tracing capabilities available")
                tracing_available = True
            except ImportError:
                logger.warning("⚠️ OpenAI Agents tracing not available")
                tracing_available = False
                
        except ImportError:
            logger.warning("⚠️ OpenAI Agents SDK not available")
            tracing_available = False
        
        # Test workflow manager tracing
        from src.tools.agents.shared.workflow_manager import TRACING_AVAILABLE
        logger.info(f"Workflow manager tracing available: {TRACING_AVAILABLE}")
        
        # Test dynamic troubleshoot agent tracing
        from src.tools.agents.dynamic_troubleshoot_agent import OPENAI_AGENTS_AVAILABLE
        logger.info(f"Dynamic troubleshoot agent OpenAI available: {OPENAI_AGENTS_AVAILABLE}")
        
        return tracing_available
        
    except Exception as e:
        logger.error(f"Tracing test failed: {e}", exc_info=True)
        return False


async def run_comprehensive_test():
    """Run comprehensive test of the enhanced dynamic troubleshoot agent."""
    
    logger.info("🚀 Starting comprehensive test of Enhanced Dynamic Troubleshoot Agent")
    
    # Set up test environment
    setup_test_environment()
    
    # Run tests
    test_results = {}
    
    # Test 1: Basic functionality
    logger.info("\n📋 Test 1: Basic Functionality")
    test_results["basic_functionality"] = await test_dynamic_troubleshoot_agent()
    
    # Test 2: Workflow execution simulation
    logger.info("\n📋 Test 2: Workflow Execution Simulation")
    test_results["workflow_simulation"] = await test_workflow_execution_simulation()
    
    # Test 3: Tracing capabilities
    logger.info("\n📋 Test 3: Tracing Capabilities")
    test_results["tracing"] = await test_tracing_availability()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*80)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        logger.info("🎉 ALL TESTS PASSED - Enhanced Dynamic Troubleshoot Agent is ready!")
    else:
        logger.warning("⚠️ Some tests failed - Check logs for details")
    
    return test_results


if __name__ == "__main__":
    # Run the comprehensive test
    results = asyncio.run(run_comprehensive_test())
    
    # Exit with appropriate code
    all_passed = all(results.values())
    exit(0 if all_passed else 1) 