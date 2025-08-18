#!/usr/bin/env python3

"""
Dynamic Micro-Agents Architecture Demo

This demo showcases the new dynamic micro-agent architecture that solves
OpenAI rate limiting issues through task-driven parallelization:

1. **Dynamic Agent Template**: One agent implementation for all tasks
2. **Task-Driven Parallelization**: Any independent task becomes a parallel micro-agent
3. **Workflow Flexibility**: Different use cases define their own task sets
4. **Automatic Dependency Resolution**: System determines optimal execution order
5. **Efficient Resource Usage**: Creates only needed agents based on tasks

Key advantages over the previous specific agent files approach:
- No need for specific agent files (license_agent.py, index_agent.py, etc.)
- Flexible task definitions that can be reused across workflows
- Automatic parallelization based on task dependencies
- Dynamic scaling - create as many agents as needed
- Workflow reusability across different use cases
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.tools.agents.dynamic_coordinator import DynamicCoordinator
from src.tools.agents.shared import (
    AgentConfig,
    SplunkDiagnosticContext,
    SplunkToolRegistry,
    TaskDefinition,
    create_splunk_tools,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_basic_dynamic_workflow():
    """Demo 1: Basic dynamic workflow execution."""

    print("\n" + "=" * 80)
    print("🚀 DEMO 1: Basic Dynamic Workflow Execution")
    print("=" * 80)

    # Create configuration
    config = AgentConfig(api_key="demo-api-key", model="gpt-4", temperature=0.1)

    # Create tool registry
    tool_registry = SplunkToolRegistry()
    create_splunk_tools(tool_registry)

    # Create dynamic coordinator
    coordinator = DynamicCoordinator(config, tool_registry)

    print("✅ Dynamic coordinator created")

    # List available workflows
    workflows = coordinator.list_available_workflows()
    print(f"\n📋 Available Workflows ({len(workflows)}):")

    for workflow in workflows:
        print(f"\n🔧 {workflow['name']}")
        print(f"   ID: {workflow['workflow_id']}")
        print(f"   Tasks: {workflow['total_tasks']}")
        print(f"   Execution Phases: {workflow['execution_phases']}")
        print(f"   Parallel Efficiency: {workflow['parallel_efficiency']:.1%}")
        print(f"   Description: {workflow['description']}")

        # Show task breakdown
        print("   📝 Tasks:")
        for task in workflow["tasks"]:
            deps = (
                f" (depends on: {', '.join(task['dependencies'])})"
                if task["dependencies"]
                else " (independent)"
            )
            print(f"      • {task['name']}{deps}")

    # Create diagnostic context
    diagnostic_context = SplunkDiagnosticContext(
        earliest_time="-24h",
        latest_time="now",
        indexes=["main", "security", "web"],
        sourcetypes=["access_combined", "syslog"],
        sources=[],
    )

    print("\n🎯 Diagnostic Context Created:")
    print(f"   Time Range: {diagnostic_context.earliest_time} to {diagnostic_context.latest_time}")
    print(f"   Target Indexes: {diagnostic_context.indexes}")
    print(f"   Target Sourcetypes: {diagnostic_context.sourcetypes}")

    # Demo health check workflow (simplest)
    print("\n🏥 Executing Health Check Workflow...")
    health_result = await coordinator.execute_health_check(diagnostic_context)

    print("✅ Health Check Result:")
    print(f"   Status: {health_result['status']}")
    print(f"   Overall Status: {health_result['workflow_execution']['overall_status']}")
    print(f"   Execution Time: {health_result['performance_metrics']['total_execution_time']:.2f}s")
    print(f"   Tasks Completed: {health_result['workflow_execution']['total_tasks']}")


async def demo_missing_data_workflow():
    """Demo 2: Missing data workflow with parallel execution."""

    print("\n" + "=" * 80)
    print("🔍 DEMO 2: Missing Data Workflow - Parallel Task Execution")
    print("=" * 80)

    # Create configuration and coordinator
    config = AgentConfig(api_key="demo-api-key", model="gpt-4", temperature=0.1)
    tool_registry = SplunkToolRegistry()
    create_splunk_tools(tool_registry)
    coordinator = DynamicCoordinator(config, tool_registry)

    # Create diagnostic context for missing data scenario
    diagnostic_context = SplunkDiagnosticContext(
        earliest_time="-2h",
        latest_time="now",
        indexes=["security", "firewall"],
        sourcetypes=["cisco:asa", "pan:traffic"],
        sources=[],
    )

    problem_description = "Security dashboard shows no firewall events for the last 2 hours"

    print(f"🎯 Problem: {problem_description}")
    print("🔍 Analyzing with dynamic micro-agents...")

    # Execute missing data workflow
    result = await coordinator.execute_missing_data_analysis(
        diagnostic_context, problem_description
    )

    print("\n📊 Missing Data Analysis Results:")
    print(f"   Overall Status: {result['workflow_execution']['overall_status']}")
    print(f"   Execution Time: {result['performance_metrics']['total_execution_time']:.2f}s")
    print(f"   Parallel Efficiency: {result['workflow_execution']['parallel_efficiency']:.1%}")
    print(f"   Execution Phases: {result['workflow_execution']['execution_phases']}")
    print(f"   Total Tasks: {result['workflow_execution']['total_tasks']}")

    print("\n🔧 Task Execution Summary:")
    for task in result["task_results"]:
        status_icon = {"healthy": "✅", "warning": "⚠️", "critical": "🔴", "error": "❌"}.get(
            task["status"], "❓"
        )
        print(f"   {status_icon} {task['task']}: {task['status']} ({task['execution_time']:.2f}s)")

        # Show findings
        if task["findings"]:
            for finding in task["findings"][:2]:  # Show first 2 findings
                print(f"      📋 {finding}")

        # Show recommendations
        if task["recommendations"]:
            for rec in task["recommendations"][:1]:  # Show first recommendation
                print(f"      💡 {rec}")

    print("\n📈 Performance Metrics:")
    print(f"   Successful Tasks: {result['performance_metrics']['successful_tasks']}")
    print(f"   Failed Tasks: {result['performance_metrics']['failed_tasks']}")
    print(f"   Parallel Phases: {result['performance_metrics']['parallel_phases']}")

    # Show workflow summary
    summary = result["summary"]
    print("\n📋 Workflow Summary:")
    print("   Task Status Breakdown:")
    for status, count in summary["task_status_breakdown"].items():
        if count > 0:
            print(f"      {status.title()}: {count}")


async def demo_custom_workflow_creation():
    """Demo 3: Creating custom workflows on-the-fly."""

    print("\n" + "=" * 80)
    print("🛠️ DEMO 3: Custom Workflow Creation - Task-Driven Flexibility")
    print("=" * 80)

    # Create configuration and coordinator
    config = AgentConfig(api_key="demo-api-key", model="gpt-4", temperature=0.1)
    tool_registry = SplunkToolRegistry()
    create_splunk_tools(tool_registry)
    coordinator = DynamicCoordinator(config, tool_registry)

    print("🎯 Creating a custom workflow for network security analysis...")

    # Define custom tasks for network security analysis
    custom_tasks = [
        TaskDefinition(
            task_id="firewall_connectivity",
            name="Firewall Connectivity Check",
            description="Verify firewall data ingestion and connectivity",
            instructions="""
You are checking firewall connectivity and data ingestion.

**Task:** Verify firewall logs are being received
**Context:** Target indexes: {indexes}, sourcetypes: {sourcetypes}

**Analysis:**
1. Check for recent firewall events in target indexes
2. Verify sourcetype distribution
3. Analyze data volume trends
4. Identify any ingestion gaps

**Output:** Return DiagnosticResult with connectivity status and data flow analysis.
            """,
            required_tools=["run_oneshot_search", "list_indexes"],
            dependencies=[],  # Independent task
            context_requirements=["indexes", "sourcetypes", "earliest_time", "latest_time"],
        ),
        TaskDefinition(
            task_id="threat_detection_status",
            name="Threat Detection Status",
            description="Check threat detection and alerting status",
            instructions="""
You are checking threat detection and alerting status.

**Task:** Verify threat detection systems are operational
**Time Range:** {earliest_time} to {latest_time}

**Analysis:**
1. Check for security alerts and detections
2. Verify correlation rules are firing
3. Analyze alert volume and patterns
4. Identify any detection gaps

**Output:** Return DiagnosticResult with threat detection status and alert analysis.
            """,
            required_tools=["run_oneshot_search"],
            dependencies=[],  # Independent task
            context_requirements=["earliest_time", "latest_time"],
        ),
        TaskDefinition(
            task_id="network_baseline_analysis",
            name="Network Baseline Analysis",
            description="Analyze network traffic patterns and baselines",
            instructions="""
You are analyzing network traffic patterns and baselines.

**Task:** Check network traffic patterns and establish baselines
**Dependencies:** Use firewall connectivity results for context

**Analysis:**
1. Analyze traffic volume patterns
2. Check for unusual network activity
3. Establish baseline metrics
4. Identify anomalies or deviations

**Output:** Return DiagnosticResult with network baseline analysis and anomaly detection.
            """,
            required_tools=["run_oneshot_search"],
            dependencies=["firewall_connectivity"],  # Depends on firewall check
            context_requirements=["indexes", "earliest_time", "latest_time"],
        ),
    ]

    # Create custom workflow
    custom_workflow = coordinator.create_custom_workflow_from_tasks(
        workflow_id="network_security_analysis",
        workflow_name="Network Security Analysis",
        task_definitions=custom_tasks,
    )

    print(f"✅ Custom workflow created: {custom_workflow.name}")
    print(f"   Tasks: {len(custom_workflow.tasks)}")

    # Show task dependency analysis
    print("\n📊 Task Dependency Analysis:")
    for task in custom_workflow.tasks:
        if task.dependencies:
            print(f"   🔗 {task.name} → depends on: {', '.join(task.dependencies)}")
        else:
            print(f"   🔀 {task.name} → independent (can run in parallel)")

    # Create diagnostic context
    diagnostic_context = SplunkDiagnosticContext(
        earliest_time="-4h",
        latest_time="now",
        indexes=["security", "network", "firewall"],
        sourcetypes=["cisco:asa", "palo_alto", "network_traffic"],
        sources=[],
    )

    problem_description = "Network security monitoring dashboard shows anomalies"

    print(f"\n🎯 Problem: {problem_description}")
    print("🚀 Executing custom workflow with dynamic micro-agents...")

    # Execute custom workflow
    result = await coordinator.execute_custom_workflow(
        custom_workflow, diagnostic_context, problem_description
    )

    print("\n📊 Custom Workflow Results:")
    print(f"   Workflow: {result['workflow_execution']['workflow_name']}")
    print(f"   Overall Status: {result['workflow_execution']['overall_status']}")
    print(f"   Execution Time: {result['performance_metrics']['total_execution_time']:.2f}s")
    print(f"   Parallel Efficiency: {result['workflow_execution']['parallel_efficiency']:.1%}")
    print(f"   Execution Phases: {result['workflow_execution']['execution_phases']}")

    print("\n🔧 Task Execution Details:")
    for task in result["task_results"]:
        status_icon = {"healthy": "✅", "warning": "⚠️", "critical": "🔴", "error": "❌"}.get(
            task["status"], "❓"
        )
        print(f"   {status_icon} {task['task']}: {task['status']} ({task['execution_time']:.2f}s)")


async def demo_performance_comparison():
    """Demo 4: Performance comparison - Parallel vs Sequential execution."""

    print("\n" + "=" * 80)
    print("⚡ DEMO 4: Performance Comparison - Parallel vs Sequential")
    print("=" * 80)

    # Create configuration and coordinator
    config = AgentConfig(api_key="demo-api-key", model="gpt-4", temperature=0.1)
    tool_registry = SplunkToolRegistry()
    create_splunk_tools(tool_registry)
    coordinator = DynamicCoordinator(config, tool_registry)

    # Create diagnostic context
    diagnostic_context = SplunkDiagnosticContext(
        earliest_time="-1h",
        latest_time="now",
        indexes=["main", "security"],
        sourcetypes=["access_combined"],
        sources=[],
    )

    print("🎯 Comparing execution strategies for missing data workflow...")

    # Get the missing data workflow to analyze its parallelization
    workflows = coordinator.list_available_workflows()
    missing_data_workflow = next(
        w for w in workflows if w["workflow_id"] == "missing_data_troubleshooting"
    )

    print(f"\n📊 Workflow Analysis: {missing_data_workflow['name']}")
    print(f"   Total Tasks: {missing_data_workflow['total_tasks']}")
    print(f"   Execution Phases: {missing_data_workflow['execution_phases']}")
    print(f"   Parallel Efficiency: {missing_data_workflow['parallel_efficiency']:.1%}")

    # Show execution phases
    print("\n🔀 Parallel Execution Plan:")

    # Simulate the dependency analysis
    workflow_manager = coordinator.workflow_manager
    workflow_def = workflow_manager.get_workflow("missing_data_troubleshooting")
    dependency_graph = workflow_manager._build_dependency_graph(workflow_def.tasks)
    execution_phases = workflow_manager._create_execution_phases(
        workflow_def.tasks, dependency_graph
    )

    for i, phase in enumerate(execution_phases):
        print(f"   Phase {i+1} (parallel): {', '.join(phase)}")

    # Calculate theoretical speedup
    sequential_time = len(workflow_def.tasks)  # If all tasks ran sequentially
    parallel_time = len(execution_phases)  # With parallel execution
    theoretical_speedup = sequential_time / parallel_time

    print("\n⚡ Performance Benefits:")
    print(f"   Sequential Execution: {sequential_time} time units")
    print(f"   Parallel Execution: {parallel_time} time units")
    print(f"   Theoretical Speedup: {theoretical_speedup:.1f}x")
    print(f"   Efficiency Gain: {(1 - 1/theoretical_speedup) * 100:.1f}%")

    # Execute the workflow to get actual timing
    print("\n🚀 Executing workflow to measure actual performance...")
    result = await coordinator.execute_missing_data_analysis(
        diagnostic_context, "Performance comparison test"
    )

    print("\n📈 Actual Performance Results:")
    print(f"   Total Execution Time: {result['performance_metrics']['total_execution_time']:.2f}s")
    print(
        f"   Workflow Execution Time: {result['performance_metrics']['workflow_execution_time']:.2f}s"
    )
    print(f"   Parallel Phases Executed: {result['performance_metrics']['parallel_phases']}")
    print(f"   Tasks Completed: {result['performance_metrics']['tasks_completed']}")

    # Show token/context efficiency benefits
    print("\n🧠 Context Efficiency Benefits:")
    print("   ✅ Each micro-agent receives only relevant context for its task")
    print("   ✅ No massive context windows sent to every LLM call")
    print("   ✅ Reduced OpenAI rate limiting through smaller requests")
    print("   ✅ Parallel execution reduces overall wait time")
    print("   ✅ Dynamic scaling - only create agents needed for tasks")


async def main():
    """Run all dynamic micro-agent demos."""

    print("🚀 Dynamic Micro-Agents Architecture Demo")
    print("=" * 80)
    print(
        """
This demo showcases the new dynamic micro-agent architecture that solves
OpenAI rate limiting issues through innovative task-driven parallelization:

🎯 Key Innovation: One Dynamic Agent Template
   Instead of creating specific agent files (license_agent.py, index_agent.py),
   we use ONE dynamic agent template that can be configured for any task.

🔀 Task-Driven Parallelization
   Any independent task automatically becomes a parallel micro-agent.
   The system analyzes dependencies and creates optimal execution phases.

⚡ Automatic Scaling
   Create exactly as many agents as needed based on the number of tasks.
   No fixed agent architecture - completely flexible and efficient.

🛠️ Workflow Flexibility
   Different use cases can define their own task sets and reuse the same
   underlying agent infrastructure.

Let's see this in action...
    """
    )

    try:
        # Run all demos
        await demo_basic_dynamic_workflow()
        await demo_missing_data_workflow()
        await demo_custom_workflow_creation()
        await demo_performance_comparison()

        print("\n" + "=" * 80)
        print("🎉 DEMO COMPLETE - Dynamic Micro-Agents Architecture")
        print("=" * 80)
        print(
            """
✅ Demonstrated Features:

1. 🎯 Dynamic Agent Template
   - One agent implementation handles all tasks
   - No need for specific agent files
   - Configurable instructions, tools, and context

2. 🔀 Task-Driven Parallelization
   - Independent tasks run in parallel automatically
   - Dependency resolution creates optimal execution phases
   - Maximum parallel efficiency based on task relationships

3. 🛠️ Workflow Flexibility
   - Built-in workflows for common scenarios
   - Custom workflow creation on-the-fly
   - Reusable task definitions across different use cases

4. ⚡ Performance Benefits
   - Parallel execution reduces overall time
   - Smaller context windows per agent reduce rate limiting
   - Dynamic scaling creates only needed agents
   - Efficient resource utilization

5. 🧠 Context Efficiency
   - Each agent gets only relevant context for its task
   - No massive instruction sets sent to every LLM call
   - Reduced token usage and OpenAI rate limiting
   - Better focus and accuracy per task

This architecture provides maximum flexibility while solving the original
OpenAI rate limiting problem through intelligent task decomposition and
parallel execution.
        """
        )

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        return False

    return True


if __name__ == "__main__":
    # Run the demo
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
