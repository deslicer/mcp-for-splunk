#!/usr/bin/env python3
"""
Test script for the Enhanced Handoff-Based Dynamic Troubleshooting Agent.

This script demonstrates the new handoff-based orchestration approach with:
- Specialized micro-agents for different diagnostic tasks
- OpenAI Agents SDK handoff pattern for intelligent routing
- Comprehensive tracing and context inspection
- End-to-end visibility of agent interactions

Usage:
    python examples/test_handoff_troubleshooting.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from fastmcp import Context
from src.tools.agents.dynamic_troubleshoot_agent import DynamicTroubleshootAgentTool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockContext(Context):
    """Mock context for testing the handoff-based troubleshooting agent."""
    
    def __init__(self):
        self.progress_reports = []
        self.info_messages = []
        self.warning_messages = []
        self.error_messages = []
    
    async def report_progress(self, progress: int, total: int):
        """Mock progress reporting."""
        self.progress_reports.append((progress, total))
        print(f"📊 Progress: {progress}/{total} ({progress/total*100:.1f}%)")
    
    async def info(self, message: str):
        """Mock info logging."""
        self.info_messages.append(message)
        print(f"ℹ️  {message}")
    
    async def warning(self, message: str):
        """Mock warning logging."""
        self.warning_messages.append(message)
        print(f"⚠️  {message}")
    
    async def error(self, message: str):
        """Mock error logging."""
        self.error_messages.append(message)
        print(f"❌ {message}")

async def test_missing_data_scenario():
    """Test the handoff-based agent with a missing data scenario."""
    
    print("\n" + "="*80)
    print("🔍 TESTING MISSING DATA SCENARIO WITH HANDOFF-BASED ORCHESTRATION")
    print("="*80)
    
    # Create the handoff-based troubleshooting agent
    try:
        agent = DynamicTroubleshootAgentTool("dynamic_troubleshoot", "troubleshooting")
        print("✅ Handoff-based troubleshooting agent created successfully")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return
    
    # Create mock context
    ctx = MockContext()
    
    # Test problem description for missing data
    problem_description = """
    My security dashboard shows no data for the last 2 hours, but I know events should be coming in from our forwarders.
    Usually we see around 1000 events per minute from index=security, but now it shows zero results.
    The forwarders appear to be running normally, and I can see network traffic.
    This started happening around 2 PM today, and users are reporting they can't see recent security alerts.
    """
    
    # Execute the handoff-based troubleshooting
    try:
        print(f"\n🚀 Starting handoff-based troubleshooting for missing data scenario...")
        print(f"📝 Problem: {problem_description[:100]}...")
        
        result = await agent.execute(
            ctx=ctx,
            problem_description=problem_description,
            earliest_time="-4h",
            latest_time="now",
            focus_index="security",
            complexity_level="moderate",
            workflow_type="auto"  # Let it auto-detect
        )
        
        print(f"\n✅ Handoff-based troubleshooting completed!")
        print(f"📊 Result status: {result.get('status', 'unknown')}")
        print(f"🎯 Coordinator type: {result.get('coordinator_type', 'unknown')}")
        
        # Display context inspection results
        if 'context_inspection' in result:
            context_info = result['context_inspection']
            print(f"\n📋 CONTEXT INSPECTION RESULTS:")
            print(f"   • Input length: {context_info['orchestration_input']['total_length']} characters")
            print(f"   • Available specialists: {context_info['agent_context']['available_specialists']}")
            print(f"   • Context efficiency: {context_info['context_optimization']['context_efficiency_score']:.2f}")
            print(f"   • Tracing enabled: {context_info['tracing_context']['tracing_available']}")
            
            print(f"\n🤖 ENGAGED SPECIALISTS:")
            for specialist in context_info['agent_context']['specialist_names']:
                print(f"   • {specialist}")
            
            print(f"\n💡 CONTEXT OPTIMIZATION RECOMMENDATIONS:")
            for rec in context_info['context_optimization']['recommendations']:
                print(f"   • {rec}")
        
        # Display handoff metadata
        if 'handoff_metadata' in result:
            handoff_info = result['handoff_metadata']
            print(f"\n🔄 HANDOFF ORCHESTRATION DETAILS:")
            print(f"   • Orchestrator: {handoff_info.get('orchestrating_agent', 'Unknown')}")
            print(f"   • Handoff approach: {handoff_info.get('handoff_approach', 'Unknown')}")
            print(f"   • Tracing spans: {handoff_info.get('tracing_spans', False)}")
        
        # Display workflow execution details
        if 'workflow_execution' in result:
            workflow_info = result['workflow_execution']
            print(f"\n⚡ WORKFLOW EXECUTION DETAILS:")
            print(f"   • Workflow ID: {workflow_info.get('workflow_id', 'Unknown')}")
            print(f"   • Execution method: {workflow_info.get('execution_method', 'Unknown')}")
            print(f"   • Turns executed: {workflow_info.get('turns_executed', 0)}")
            print(f"   • Agents engaged: {workflow_info.get('agents_engaged', 0)}")
        
        # Display orchestration analysis (truncated for readability)
        if 'orchestration_analysis' in result:
            analysis = result['orchestration_analysis']
            print(f"\n🧠 ORCHESTRATION ANALYSIS (first 500 chars):")
            print(f"   {analysis[:500]}{'...' if len(analysis) > 500 else ''}")
        
        print(f"\n📈 PROGRESS REPORTS: {len(ctx.progress_reports)}")
        print(f"💬 INFO MESSAGES: {len(ctx.info_messages)}")
        print(f"⚠️  WARNING MESSAGES: {len(ctx.warning_messages)}")
        print(f"❌ ERROR MESSAGES: {len(ctx.error_messages)}")
        
    except Exception as e:
        print(f"❌ Handoff-based troubleshooting failed: {e}")
        import traceback
        traceback.print_exc()

async def test_performance_scenario():
    """Test the handoff-based agent with a performance scenario."""
    
    print("\n" + "="*80)
    print("🚀 TESTING PERFORMANCE SCENARIO WITH HANDOFF-BASED ORCHESTRATION")
    print("="*80)
    
    # Create the handoff-based troubleshooting agent
    try:
        agent = DynamicTroubleshootAgentTool("dynamic_troubleshoot", "troubleshooting")
        print("✅ Handoff-based troubleshooting agent created successfully")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return
    
    # Create mock context
    ctx = MockContext()
    
    # Test problem description for performance issues
    problem_description = """
    Our Splunk searches have been running extremely slowly since yesterday morning.
    Searches that used to complete in 30 seconds are now taking 5-10 minutes.
    Users are complaining about dashboard load times, and scheduled searches are backing up.
    I noticed high CPU usage on our search heads, and the search concurrency seems to be hitting limits.
    This is affecting our entire operations team's ability to investigate incidents.
    """
    
    # Execute the handoff-based troubleshooting
    try:
        print(f"\n🚀 Starting handoff-based troubleshooting for performance scenario...")
        print(f"📝 Problem: {problem_description[:100]}...")
        
        result = await agent.execute(
            ctx=ctx,
            problem_description=problem_description,
            earliest_time="-24h",
            latest_time="now",
            complexity_level="advanced",
            workflow_type="performance"  # Force performance workflow
        )
        
        print(f"\n✅ Handoff-based troubleshooting completed!")
        print(f"📊 Result status: {result.get('status', 'unknown')}")
        print(f"🎯 Detected workflow: {result.get('detected_workflow_type', 'unknown')}")
        
        # Display context inspection results
        if 'context_inspection' in result:
            context_info = result['context_inspection']
            print(f"\n📋 CONTEXT INSPECTION RESULTS:")
            print(f"   • Input length: {context_info['orchestration_input']['total_length']} characters")
            print(f"   • Context efficiency: {context_info['context_optimization']['context_efficiency_score']:.2f}")
            print(f"   • Performance specialists: {len([s for s in context_info['agent_context']['specialist_names'] if 'Performance' in s or 'Resource' in s or 'Concurrency' in s])}")
        
        print(f"\n📈 PROGRESS REPORTS: {len(ctx.progress_reports)}")
        print(f"💬 INFO MESSAGES: {len(ctx.info_messages)}")
        
    except Exception as e:
        print(f"❌ Handoff-based troubleshooting failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    
    print("🧪 HANDOFF-BASED DYNAMIC TROUBLESHOOTING AGENT TEST")
    print("=" * 80)
    print("This test demonstrates the new handoff-based orchestration approach with:")
    print("• Specialized micro-agents for different diagnostic tasks")
    print("• OpenAI Agents SDK handoff pattern for intelligent routing")
    print("• Comprehensive tracing and context inspection")
    print("• End-to-end visibility of agent interactions")
    print("=" * 80)
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("   Please set your OpenAI API key to test the handoff-based agent")
        return
    
    try:
        # Test missing data scenario
        await test_missing_data_scenario()
        
        # Test performance scenario  
        await test_performance_scenario()
        
        print("\n" + "="*80)
        print("🎉 HANDOFF-BASED TROUBLESHOOTING TESTS COMPLETED")
        print("="*80)
        print("Key benefits demonstrated:")
        print("• Intelligent specialist selection based on problem symptoms")
        print("• Context preservation across agent handoffs")
        print("• Comprehensive tracing of agent interactions")
        print("• Context inspection for optimization insights")
        print("• End-to-end visibility of diagnostic process")
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 