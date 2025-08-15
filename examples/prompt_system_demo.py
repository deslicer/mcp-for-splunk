#!/usr/bin/env python3
"""
Demo script showing the new prompt system functionality.

This demonstrates:
1. How prompts are auto-discovered and loaded
2. How to interact with the prompt registry
3. How the new mcp_usage prompts work
4. Integration with the Splunk tools and resources
"""

import asyncio
import sys
from pathlib import Path

from fastmcp import FastMCP

from src.core.loader import ComponentLoader
from src.core.registry import prompt_registry

# Add project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


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

    # Demonstrate new prompts
    print("3. Demonstrating mcp_usage prompts:")
    for name, args in [
        ("mcp_overview", {"detail_level": "basic"}),
        ("workflow_creation_guide", {"workflow_type": "performance", "complexity": "simple"}),
        ("tool_usage_guide", {"tool_name": "workflow_runner"}),
    ]:
        print(f"\n   📋 Prompt: {name}")
        prompt_instance = prompt_registry.get_prompt(name)
        result = await prompt_instance.get_prompt(None, **args)  # Context not needed for static text
        content = result["content"][0]["text"] if isinstance(result, dict) else str(result)
        print(f"   ✅ Content preview: {content[:200]}{'...' if len(content) > 200 else ''}")

    print("\n4. Integration with existing system:")
    print("   🔗 Prompts work seamlessly with:")
    print("   - 🛠️  Splunk tools (search, admin, metadata, etc.)")
    print("   - 📚 Documentation and system resources")
    print("   - 🎯 Auto-discovery and registration system")
    print("   - 🚀 FastMCP server with proper parameter handling")

    print("\n" + "=" * 70)
    print("✅ Demo complete! The prompt system is ready for use.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_prompt_system())
