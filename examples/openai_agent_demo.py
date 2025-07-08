#!/usr/bin/env python3
"""
OpenAI Agent Tool Demonstration

This script demonstrates how to use the OpenAI Agent tool for troubleshooting
Splunk issues. The agent integrates with the existing MCP tools and prompts
to provide intelligent analysis and recommendations.

Prerequisites:
1. Set OPENAI_API_KEY environment variable
2. Configure Splunk connection (SPLUNK_HOST, SPLUNK_USERNAME, etc.)
3. Ensure the MCP server is running

Usage:
    python examples/openai_agent_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp import Context
from unittest.mock import Mock, AsyncMock

from src.tools.agents.openai_agent import OpenAIAgentTool


async def demo_openai_agent():
    """Demonstrate the OpenAI Agent tool functionality."""
    
    print("🤖 OpenAI Agent Tool Demonstration")
    print("=" * 50)
    
    # Check if OpenAI API key is available
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not found.")
        print("   Please set your OpenAI API key to run this demo:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return
    
    try:
        # Create the OpenAI agent tool
        print("🔧 Initializing OpenAI Agent Tool...")
        agent_tool = OpenAIAgentTool("execute_openai_agent", "agents")
        print(f"✅ Agent tool initialized with model: {agent_tool.config.model}")
        
        # Create a mock context for demonstration
        mock_ctx = Mock(spec=Context)
        mock_ctx.info = AsyncMock()
        mock_ctx.error = AsyncMock()
        
        # Demo 1: Performance troubleshooting
        print("\n📊 Demo 1: Performance Troubleshooting Agent")
        print("-" * 45)
        
        result = await agent_tool.execute(
            mock_ctx,
            agent_type="troubleshooting",
            component="performance",
            earliest_time="-24h",
            latest_time="now"
        )
        
        print(f"Status: {result['status']}")
        print(f"Agent Type: {result['agent_type']}")
        print(f"Component: {result['component']}")
        print(f"Tools Available: {result['tools_available']}")
        print(f"Analysis Preview: {result['analysis'][:200]}...")
        
        # Demo 2: Input troubleshooting
        print("\n📥 Demo 2: Input Troubleshooting Agent")
        print("-" * 42)
        
        result = await agent_tool.execute(
            mock_ctx,
            agent_type="troubleshooting",
            component="inputs",
            earliest_time="-7d",
            latest_time="now",
            focus_index="main"
        )
        
        print(f"Status: {result['status']}")
        print(f"Agent Type: {result['agent_type']}")
        print(f"Component: {result['component']}")
        print(f"Analysis Preview: {result['analysis'][:200]}...")
        
        # Demo 3: Indexing performance troubleshooting
        print("\n🔍 Demo 3: Indexing Performance Agent")
        print("-" * 42)
        
        result = await agent_tool.execute(
            mock_ctx,
            agent_type="troubleshooting",
            component="indexing",
            earliest_time="-4h",
            latest_time="now"
        )
        
        print(f"Status: {result['status']}")
        print(f"Agent Type: {result['agent_type']}")
        print(f"Component: {result['component']}")
        print(f"Analysis Preview: {result['analysis'][:200]}...")
        
        # Demo 4: Error handling
        print("\n❌ Demo 4: Error Handling")
        print("-" * 25)
        
        result = await agent_tool.execute(
            mock_ctx,
            agent_type="invalid_type",
            component="performance"
        )
        
        print(f"Status: {result['status']}")
        print(f"Error Type: {result['error_type']}")
        print(f"Error Message: {result['error']}")
        
        print("\n✅ Demo completed successfully!")
        print("\n📚 Available Agent Types and Components:")
        print("   - troubleshooting:")
        print("     * performance: System resource and throughput analysis")
        print("     * inputs: Data input and ingestion troubleshooting")
        print("     * indexing: Indexing performance and delay analysis")
        print("     * inputs_multi: Advanced multi-agent input analysis")
        
    except Exception as e:
        print(f"❌ Error during demo: {e}")
        print("   Make sure your OpenAI API key is valid and you have network connectivity.")


async def demo_prompt_integration():
    """Demonstrate how the agent integrates with existing prompts."""
    
    print("\n🔗 Prompt Integration Demonstration")
    print("=" * 40)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY required for this demo")
        return
    
    try:
        agent_tool = OpenAIAgentTool("execute_openai_agent", "agents")
        mock_ctx = Mock(spec=Context)
        
        # Show how the agent retrieves and uses prompts
        print("📝 Retrieving troubleshooting prompt...")
        
        prompt_content = await agent_tool._get_prompt_content(
            mock_ctx, 
            "troubleshooting", 
            "performance",
            earliest_time="-24h",
            latest_time="now"
        )
        
        print(f"✅ Prompt retrieved ({len(prompt_content)} characters)")
        print(f"Prompt preview: {prompt_content[:300]}...")
        
        # Show available tools
        print("\n🛠️  Discovering available MCP tools...")
        available_tools = agent_tool._get_available_tools()
        
        print(f"✅ Found {len(available_tools)} available tools:")
        for tool in available_tools[:5]:  # Show first 5 tools
            print(f"   - {tool['function']['name']}: {tool['function']['description'][:60]}...")
        
        if len(available_tools) > 5:
            print(f"   ... and {len(available_tools) - 5} more tools")
        
    except Exception as e:
        print(f"❌ Error during prompt demo: {e}")


def print_configuration_info():
    """Print configuration information for the demo."""
    
    print("\n⚙️  Configuration Information")
    print("=" * 30)
    
    # OpenAI configuration
    print("OpenAI Configuration:")
    print(f"   API Key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print(f"   Model: {os.getenv('OPENAI_MODEL', 'gpt-4o (default)')}")
    print(f"   Temperature: {os.getenv('OPENAI_TEMPERATURE', '0.7 (default)')}")
    print(f"   Max Tokens: {os.getenv('OPENAI_MAX_TOKENS', '4000 (default)')}")
    
    # Splunk configuration
    print("\nSplunk Configuration:")
    print(f"   Host: {os.getenv('SPLUNK_HOST', 'Not set')}")
    print(f"   Port: {os.getenv('SPLUNK_PORT', 'Not set')}")
    print(f"   Username: {os.getenv('SPLUNK_USERNAME', 'Not set')}")
    print(f"   Password: {'✅ Set' if os.getenv('SPLUNK_PASSWORD') else '❌ Not set'}")


async def main():
    """Main demonstration function."""
    
    print("🚀 MCP Server for Splunk - OpenAI Agent Demo")
    print("=" * 50)
    print("This demo shows how to use AI agents for Splunk troubleshooting")
    print("using the OpenAI integration with the MCP server.\n")
    
    # Print configuration
    print_configuration_info()
    
    # Run demos
    await demo_openai_agent()
    await demo_prompt_integration()
    
    print("\n🎯 Next Steps:")
    print("1. Set up your OpenAI API key if not already done")
    print("2. Configure Splunk connection parameters")
    print("3. Start the MCP server: python src/server.py")
    print("4. Use the agent tool through MCP client calls")
    print("5. Integrate with Claude Desktop or other MCP clients")
    
    print("\n📖 For more information:")
    print("   - Check the README.md for setup instructions")
    print("   - See docs/ for detailed documentation")
    print("   - Review tests/test_openai_agent.py for usage examples")


if __name__ == "__main__":
    asyncio.run(main()) 