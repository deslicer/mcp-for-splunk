"""
Workflow Runner Tool Demonstration.

This example demonstrates how to use the WorkflowRunnerTool to execute
different workflows with various parameters and configurations.
"""

import asyncio
import logging
import os
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock FastMCP Context for demonstration
class MockContext:
    """Mock context for demonstration purposes."""
    
    def __init__(self):
        self.progress_updates = []
        self.info_messages = []
        self.error_messages = []
    
    async def report_progress(self, progress: int, total: int = 100):
        """Mock progress reporting."""
        self.progress_updates.append((progress, total))
        logger.info(f"Progress: {progress}/{total} ({progress/total*100:.1f}%)")
    
    async def info(self, message: str):
        """Mock info message."""
        self.info_messages.append(message)
        logger.info(f"INFO: {message}")
    
    async def error(self, message: str):
        """Mock error message."""
        self.error_messages.append(message)
        logger.error(f"ERROR: {message}")


async def demonstrate_workflow_runner():
    """Demonstrate the WorkflowRunnerTool capabilities."""
    
    print("=" * 80)
    print("WORKFLOW RUNNER TOOL DEMONSTRATION")
    print("=" * 80)
    
    # Check environment setup
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. This is required for the WorkflowRunnerTool.")
        print("   Set it in your .env file or environment variables.")
        return
    
    try:
        # Import the workflow runner tool
        from src.tools.workflows.workflow_runner import WorkflowRunnerTool
        
        print("✅ WorkflowRunnerTool imported successfully")
        
        # Create the tool instance
        print("\n🔧 Initializing WorkflowRunnerTool...")
        workflow_runner = WorkflowRunnerTool("workflow_runner", "workflows")
        print("✅ WorkflowRunnerTool initialized")
        
        # Create mock context
        ctx = MockContext()
        
        # Example 1: Execute missing data troubleshooting workflow
        print("\n" + "=" * 60)
        print("EXAMPLE 1: Missing Data Troubleshooting Workflow")
        print("=" * 60)
        
        try:
            result1 = await workflow_runner.execute(
                ctx=ctx,
                workflow_id="missing_data_troubleshooting",
                problem_description="Dashboard shows no data for the last 2 hours",
                earliest_time="-2h",
                latest_time="now",
                focus_index="main",
                complexity_level="moderate",
                enable_summarization=True
            )
            
            print(f"✅ Workflow Status: {result1['status']}")
            print(f"📊 Workflow: {result1['workflow_name']}")
            print(f"⏱️  Execution Time: {result1['execution_metadata']['total_execution_time']:.2f}s")
            print(f"🔄 Tasks: {result1['workflow_execution']['total_tasks']}")
            print(f"✅ Successful: {result1['workflow_execution']['successful_tasks']}")
            print(f"❌ Failed: {result1['workflow_execution']['failed_tasks']}")
            
            if result1['summarization']['enabled']:
                print(f"🧠 Summarization: Completed in {result1['summarization']['execution_time']:.2f}s")
        
        except Exception as e:
            print(f"❌ Example 1 failed: {e}")
        
        # Example 2: Execute performance analysis workflow
        print("\n" + "=" * 60)
        print("EXAMPLE 2: Performance Analysis Workflow")
        print("=" * 60)
        
        try:
            result2 = await workflow_runner.execute(
                ctx=ctx,
                workflow_id="performance_analysis",
                problem_description="Searches are running very slowly since yesterday",
                earliest_time="-24h",
                latest_time="now",
                focus_host="search-head-01",
                complexity_level="advanced",
                enable_summarization=True
            )
            
            print(f"✅ Workflow Status: {result2['status']}")
            print(f"📊 Workflow: {result2['workflow_name']}")
            print(f"⏱️  Execution Time: {result2['execution_metadata']['total_execution_time']:.2f}s")
            print(f"🔄 Tasks: {result2['workflow_execution']['total_tasks']}")
            print(f"⚡ Parallel Efficiency: {result2['workflow_execution']['parallel_efficiency']:.1%}")
            
        except Exception as e:
            print(f"❌ Example 2 failed: {e}")
        
        # Example 3: Execute workflow without summarization
        print("\n" + "=" * 60)
        print("EXAMPLE 3: Workflow Execution Without Summarization")
        print("=" * 60)
        
        try:
            result3 = await workflow_runner.execute(
                ctx=ctx,
                workflow_id="missing_data_troubleshooting",
                problem_description="Quick check for data availability",
                complexity_level="basic",
                enable_summarization=False  # Disable summarization for faster execution
            )
            
            print(f"✅ Workflow Status: {result3['status']}")
            print(f"🧠 Summarization: {result3['summarization']['enabled']}")
            print(f"⏱️  Execution Time: {result3['execution_metadata']['total_execution_time']:.2f}s")
            
        except Exception as e:
            print(f"❌ Example 3 failed: {e}")
        
        # Example 4: Handle workflow not found error
        print("\n" + "=" * 60)
        print("EXAMPLE 4: Error Handling - Workflow Not Found")
        print("=" * 60)
        
        try:
            result4 = await workflow_runner.execute(
                ctx=ctx,
                workflow_id="non_existent_workflow",
                complexity_level="moderate"
            )
            
            if result4['status'] == 'error':
                print(f"❌ Expected Error: {result4['error']}")
                print(f"📋 Available Workflows: {', '.join(result4['available_workflows'])}")
            
        except Exception as e:
            print(f"❌ Example 4 failed: {e}")
        
        # Example 5: Demonstrate parameter flexibility
        print("\n" + "=" * 60)
        print("EXAMPLE 5: Parameter Flexibility")
        print("=" * 60)
        
        try:
            result5 = await workflow_runner.execute(
                ctx=ctx,
                workflow_id="performance_analysis",
                problem_description="Comprehensive system analysis",
                earliest_time="-7d",        # Week-long analysis
                latest_time="now",
                focus_index="security",     # Focus on security index
                focus_host="indexer-03",    # Specific indexer
                focus_sourcetype="syslog",  # Specific sourcetype
                complexity_level="advanced",
                enable_summarization=True
            )
            
            print(f"✅ Workflow Status: {result5['status']}")
            print(f"🎯 Focus Areas:")
            print(f"   - Index: {result5['diagnostic_context']['focus_index']}")
            print(f"   - Host: {result5['diagnostic_context']['focus_host']}")
            print(f"   - Sourcetype: {result5['diagnostic_context']['focus_sourcetype']}")
            print(f"   - Time Range: {result5['diagnostic_context']['earliest_time']} to {result5['diagnostic_context']['latest_time']}")
            print(f"   - Complexity: {result5['diagnostic_context']['complexity_level']}")
            
        except Exception as e:
            print(f"❌ Example 5 failed: {e}")
        
        print("\n" + "=" * 80)
        print("WORKFLOW RUNNER DEMONSTRATION COMPLETED")
        print("=" * 80)
        
        # Summary
        print("\n📋 SUMMARY:")
        print(f"   - Total progress updates: {len(ctx.progress_updates)}")
        print(f"   - Total info messages: {len(ctx.info_messages)}")
        print(f"   - Total error messages: {len(ctx.error_messages)}")
        
        if ctx.info_messages:
            print(f"\n💡 Recent info messages:")
            for msg in ctx.info_messages[-3:]:  # Show last 3 messages
                print(f"   - {msg}")
        
    except ImportError as e:
        print(f"❌ Failed to import WorkflowRunnerTool: {e}")
        print("   Make sure the tool is properly installed and dependencies are met.")
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()


async def demonstrate_workflow_comparison():
    """Demonstrate comparing different workflow executions."""
    
    print("\n" + "=" * 80)
    print("WORKFLOW COMPARISON DEMONSTRATION")
    print("=" * 80)
    
    try:
        from src.tools.workflows.workflow_runner import WorkflowRunnerTool
        from src.tools.workflows.list_workflows import ListWorkflowsTool
        
        # Create tools
        workflow_runner = WorkflowRunnerTool("workflow_runner", "workflows")
        workflow_lister = ListWorkflowsTool("list_workflows", "workflows")
        
        ctx = MockContext()
        
        # First, list available workflows
        print("📋 Listing available workflows...")
        workflows_list = await workflow_lister.execute(ctx=ctx, format_type="summary")
        
        if workflows_list.get('status') == 'success':
            workflows = workflows_list['data']['workflows']
            print(f"✅ Found {len(workflows)} workflows:")
            for workflow_id, info in workflows.items():
                print(f"   - {workflow_id}: {info['name']} ({info['task_count']} tasks)")
        
        # Compare execution times for different complexity levels
        print(f"\n⚡ Comparing execution with different complexity levels...")
        
        complexity_levels = ["basic", "moderate", "advanced"]
        results = {}
        
        for complexity in complexity_levels:
            try:
                print(f"\n🔄 Running with complexity: {complexity}")
                result = await workflow_runner.execute(
                    ctx=ctx,
                    workflow_id="missing_data_troubleshooting",
                    problem_description=f"Test run with {complexity} complexity",
                    complexity_level=complexity,
                    enable_summarization=False  # Disable for fair comparison
                )
                
                results[complexity] = {
                    "status": result["status"],
                    "execution_time": result["execution_metadata"]["total_execution_time"],
                    "tasks": result["workflow_execution"]["total_tasks"],
                    "successful": result["workflow_execution"]["successful_tasks"]
                }
                
                print(f"   ✅ {complexity}: {result['status']} in {result['execution_metadata']['total_execution_time']:.2f}s")
                
            except Exception as e:
                print(f"   ❌ {complexity}: Failed - {e}")
                results[complexity] = {"status": "error", "error": str(e)}
        
        # Display comparison
        print(f"\n📊 EXECUTION COMPARISON:")
        print(f"{'Complexity':<12} {'Status':<10} {'Time (s)':<10} {'Tasks':<8} {'Success':<8}")
        print("-" * 60)
        
        for complexity, data in results.items():
            if data["status"] != "error":
                print(f"{complexity:<12} {data['status']:<10} {data['execution_time']:<10.2f} {data['tasks']:<8} {data['successful']:<8}")
            else:
                print(f"{complexity:<12} {'ERROR':<10} {'N/A':<10} {'N/A':<8} {'N/A':<8}")
        
    except Exception as e:
        print(f"❌ Workflow comparison failed: {e}")


def print_usage_examples():
    """Print usage examples for the WorkflowRunnerTool."""
    
    print("\n" + "=" * 80)
    print("WORKFLOW RUNNER USAGE EXAMPLES")
    print("=" * 80)
    
    examples = [
        {
            "title": "Basic Missing Data Analysis",
            "code": """
# Execute missing data troubleshooting workflow
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="missing_data_troubleshooting",
    problem_description="Dashboard shows no data",
    earliest_time="-24h",
    latest_time="now"
)
            """,
            "description": "Run the standard missing data troubleshooting workflow"
        },
        {
            "title": "Performance Analysis with Focus",
            "code": """
# Execute performance analysis for specific host
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="performance_analysis",
    problem_description="Slow searches on indexer-01",
    focus_host="indexer-01",
    complexity_level="advanced",
    enable_summarization=True
)
            """,
            "description": "Run performance analysis focused on a specific host"
        },
        {
            "title": "Quick Basic Analysis",
            "code": """
# Quick basic analysis without summarization
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="missing_data_troubleshooting",
    complexity_level="basic",
    enable_summarization=False
)
            """,
            "description": "Fast execution with basic complexity and no summarization"
        },
        {
            "title": "Targeted Index Analysis",
            "code": """
# Analyze specific index and sourcetype
result = await workflow_runner.execute(
    ctx=ctx,
    workflow_id="performance_analysis",
    focus_index="security",
    focus_sourcetype="firewall",
    earliest_time="-7d",
    complexity_level="moderate"
)
            """,
            "description": "Focus analysis on specific index and sourcetype"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}")
        print(f"   {example['description']}")
        print(f"   ```python{example['code']}   ```")


if __name__ == "__main__":
    """Main demonstration runner."""
    
    print("🚀 Starting Workflow Runner Tool Demonstration")
    
    # Run the main demonstration
    asyncio.run(demonstrate_workflow_runner())
    
    # Run workflow comparison
    asyncio.run(demonstrate_workflow_comparison())
    
    # Print usage examples
    print_usage_examples()
    
    print("\n✅ Demonstration completed!")
    print("\n💡 To use the WorkflowRunnerTool in your own code:")
    print("   1. Import: from src.tools.workflows.workflow_runner import WorkflowRunnerTool")
    print("   2. Initialize: tool = WorkflowRunnerTool('workflow_runner', 'workflows')")
    print("   3. Execute: result = await tool.execute(ctx=context, workflow_id='your_workflow')")
    print("   4. Use list_workflows tool to discover available workflow IDs") 