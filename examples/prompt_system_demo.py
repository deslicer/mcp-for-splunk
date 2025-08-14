#!/usr/bin/env python3
"""
Demo script showing the new prompt system functionality.

This demonstrates:
1. How prompts are auto-discovered and loaded
2. How to interact with the prompt registry
3. How the troubleshoot_inputs prompt works
4. Integration with the Splunk tools and resources
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastmcp import FastMCP

from src.core.loader import ComponentLoader
from src.core.registry import prompt_registry


async def demo_prompt_system():
    """Demonstrate the prompt system functionality."""
    print("=" * 70)
    print("🚀 Splunk MCP Prompt System Demo")
    print("=" * 70)

    # Initialize MCP server and loader
    print("\n1. Initializing MCP server and loading components...")
    mcp = FastMCP("Splunk MCP Demo")
    loader = ComponentLoader(mcp)

    # Load all components
    results = loader.load_all_components()
    print(f"✅ Loaded components: {results}")

    # Show available prompts
    print("\n2. Available prompts:")
    prompts = prompt_registry.list_prompts()

    for prompt in prompts:
        print(f"   📝 {prompt.name}")
        print(f"      Category: {prompt.category}")
        print(f"      Description: {prompt.description}")
        print(f"      Arguments: {len(prompt.arguments)}")

        for arg in prompt.arguments:
            required = "required" if arg.get("required", False) else "optional"
            print(f"        - {arg['name']} ({required}): {arg['description']}")
        print()

    # Get the troubleshoot_inputs prompt
    print("3. Demonstrating troubleshoot_inputs prompt:")
    if prompts:
        prompt_name = "troubleshoot_inputs"
        prompt_instance = prompt_registry.get_prompt(prompt_name)

        print(f"   📋 Prompt: {prompt_name}")
        print(f"   🔧 Class: {prompt_instance.__class__.__name__}")
        print(f"   📖 Metadata: {prompt_instance.METADATA}")

        # Show what the prompt would do (without executing)
        print("\n   🎯 This prompt provides:")
        print("   - Step-by-step troubleshooting workflow")
        print("   - Integration with metrics.log analysis")
        print("   - Uses run_splunk_search tool for queries")
        print("   - References official Splunk documentation")
        print("   - Configurable time ranges and focus filters")

        print("\n   📋 Example usage in MCP client:")
        print(
            f"""
   {{
     "method": "prompts/get",
     "params": {{
       "name": "{prompt_name}",
       "arguments": {{
         "earliest_time": "-24h",
         "latest_time": "now",
         "focus_index": "main",
         "focus_host": "server01"
       }}
     }}
   }}
        """
        )

        print("\n   🔍 This would generate a comprehensive workflow that:")
        print("   1. Reviews troubleshooting documentation")
        print("   2. Analyzes overall throughput patterns")
        print("   3. Breaks down by index, host, sourcetype, and source")
        print("   4. Provides timeline analysis for problem identification")
        print("   5. Checks input processor performance")
        print("   6. Includes interpretation guidelines and next steps")

    print("\n4. Integration with existing system:")
    print("   🔗 Prompts work seamlessly with:")
    print("   - 🛠️  22 Splunk tools (search, admin, metadata, etc.)")
    print("   - 📚 9 documentation and system resources")
    print("   - 🎯 Auto-discovery and registration system")
    print("   - 🚀 FastMCP server with proper parameter handling")

    print("\n5. Next steps for expansion:")
    print("   📝 Create additional prompts by:")
    print("   - Adding new classes to src/prompts/troubleshooting.py")
    print("   - Creating new modules in src/prompts/")
    print("   - Following the BasePrompt pattern")
    print("   - Auto-discovery will handle registration")

    print("\n" + "=" * 70)
    print("✅ Demo complete! The prompt system is ready for use.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_prompt_system())
