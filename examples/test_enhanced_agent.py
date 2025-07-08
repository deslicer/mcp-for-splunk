#!/usr/bin/env python3
"""
Test script for the enhanced OpenAI agent with structured workflow execution.

This script demonstrates the 6-step workflow and provides detailed logging
to help debug and understand the agent's execution process.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from fastmcp import Context
    from src.tools.agents.openai_agent import OpenAIAgentTool
except ImportError:
    # Alternative import path
    from tools.agents.openai_agent import OpenAIAgentTool
    from fastmcp import Context


# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent_test.log')
    ]
)

logger = logging.getLogger(__name__)


class MockContext(Context):
    """Mock context for testing without full MCP server."""
    
    def __init__(self):
        self.messages = []
    
    async def info(self, message: str):
        """Log info message."""
        print(f"ℹ️  INFO: {message}")
        logger.info(f"Context INFO: {message}")
        self.messages.append(("info", message))
    
    async def error(self, message: str):
        """Log error message."""
        print(f"❌ ERROR: {message}")
        logger.error(f"Context ERROR: {message}")
        self.messages.append(("error", message))
    
    async def debug(self, message: str):
        """Log debug message."""
        print(f"🐛 DEBUG: {message}")
        logger.debug(f"Context DEBUG: {message}")
        self.messages.append(("debug", message))


async def test_enhanced_agent():
    """Test the enhanced OpenAI agent with detailed logging."""
    
    print("🚀 Testing Enhanced OpenAI Agent")
    print("=" * 50)
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key in the environment or .env file")
        return
    
    try:
        # Create mock context
        ctx = MockContext()
        
        # Initialize the agent
        print("\n🔧 Initializing OpenAI Agent...")
        agent = OpenAIAgentTool("execute_openai_agent", "agents")
        
        # Test parameters
        test_params = {
            "agent_type": "troubleshooting",
            "component": "performance",
            "earliest_time": "-1h",
            "latest_time": "now",
            "complexity_level": "simple",  # Use simple for faster testing
            "include_performance_analysis": False,  # Disable for faster testing
            "analysis_depth": "quick"
        }
        
        print(f"\n📝 Test Parameters:")
        for key, value in test_params.items():
            print(f"  {key}: {value}")
        
        print(f"\n🎬 Starting agent execution...")
        print("-" * 40)
        
        # Execute the agent
        result = await agent.execute(ctx, **test_params)
        
        print("\n" + "=" * 50)
        print("📊 EXECUTION RESULTS")
        print("=" * 50)
        
        # Display results
        print(f"Status: {result.get('status', 'unknown')}")
        
        if result.get("status") == "success":
            print("✅ Agent executed successfully!")
            
            # Workflow execution details
            workflow_exec = result.get("workflow_execution", {})
            print(f"\n📋 Workflow Execution:")
            print(f"  Total Steps: {workflow_exec.get('total_steps', 0)}")
            print(f"  Completed Steps: {workflow_exec.get('completed_steps', 0)}")
            print(f"  Failed Steps: {workflow_exec.get('failed_steps', 0)}")
            print(f"  Success Rate: {workflow_exec.get('success_rate', 0):.2%}")
            
            # Context details
            context = result.get("context", {})
            print(f"\n🔧 Context Information:")
            print(f"  Tools Available: {context.get('tools_available', 0)}")
            print(f"  Resources Available: {context.get('resources_available', 0)}")
            print(f"  Resources Fetched: {context.get('resources_fetched', 0)}")
            print(f"  Workflow Steps Defined: {context.get('workflow_steps_defined', 0)}")
            print(f"  Tool Calls Extracted: {context.get('tool_calls_extracted', 0)}")
            print(f"  Resource Calls Extracted: {context.get('resource_calls_extracted', 0)}")
            
            # Agent response preview
            agent_response = result.get("agent_response", "")
            if agent_response:
                print(f"\n🤖 Agent Response Preview:")
                print(f"  Length: {len(agent_response)} characters")
                print(f"  Preview: {agent_response[:200]}...")
            
            # Step results details
            step_results = workflow_exec.get("step_results", {})
            if step_results:
                print(f"\n📋 Step Execution Details:")
                for step_id, step_result in step_results.items():
                    print(f"  {step_id}:")
                    print(f"    Tool Calls Executed: {step_result.get('tool_calls_executed', 0)}")
                    print(f"    Tool Calls Failed: {step_result.get('tool_calls_failed', 0)}")
                    
                    tool_results = step_result.get("tool_results", {})
                    if tool_results:
                        print(f"    Tool Results:")
                        for tool_name, tool_result in tool_results.items():
                            if isinstance(tool_result, dict) and "error" in tool_result:
                                print(f"      ❌ {tool_name}: {tool_result['error']}")
                            else:
                                print(f"      ✅ {tool_name}: Success")
        
        else:
            print("❌ Agent execution failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Error Type: {result.get('error_type', 'Unknown')}")
        
        print(f"\n📝 Context Messages ({len(ctx.messages)} total):")
        for level, message in ctx.messages[-10:]:  # Show last 10 messages
            emoji = {"info": "ℹ️", "error": "❌", "debug": "🐛"}.get(level, "📝")
            print(f"  {emoji} {message}")
        
        if len(ctx.messages) > 10:
            print(f"  ... and {len(ctx.messages) - 10} more messages")
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        logger.exception("Test failed")
        import traceback
        traceback.print_exc()


async def test_workflow_parsing():
    """Test the workflow parsing functionality separately."""
    
    print("\n🧪 Testing Workflow Parsing")
    print("=" * 30)
    
    try:
        ctx = MockContext()
        agent = OpenAIAgentTool("execute_openai_agent", "agents")
        
        # Test prompt fetching
        print("📝 Testing prompt fetching...")
        prompt_content = await agent._fetch_prompt(
            ctx, 
            "troubleshooting", 
            "performance",
            earliest_time="-1h",
            latest_time="now",
            analysis_type="comprehensive"
        )
        
        print(f"✅ Fetched prompt: {len(prompt_content)} characters")
        
        # Test workflow step definition
        print("🗺️ Testing workflow step definition...")
        workflow_steps = await agent._define_workflow_steps(ctx, prompt_content)
        
        print(f"✅ Defined {len(workflow_steps)} workflow steps")
        
        for i, step in enumerate(workflow_steps[:5], 1):  # Show first 5 steps
            print(f"  Step {i}: {step.title}")
            print(f"    Tool Calls: {len(step.tool_calls)}")
            print(f"    Resource Calls: {len(step.resource_calls)}")
            print(f"    Parallel: {step.parallel_execution}")
        
        if len(workflow_steps) > 5:
            print(f"  ... and {len(workflow_steps) - 5} more steps")
        
    except Exception as e:
        print(f"❌ Workflow parsing test failed: {e}")
        logger.exception("Workflow parsing test failed")


async def main():
    """Main test function."""
    print("🧪 Enhanced OpenAI Agent Test Suite")
    print("=" * 40)
    
    # Test workflow parsing first
    await test_workflow_parsing()
    
    # Test full agent execution
    await test_enhanced_agent()
    
    print("\n🎉 Test suite completed!")
    print("Check 'agent_test.log' for detailed logs")


if __name__ == "__main__":
    asyncio.run(main()) 