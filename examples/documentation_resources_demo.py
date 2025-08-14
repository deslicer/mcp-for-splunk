#!/usr/bin/env python3
"""
Demo script for Splunk documentation resources.

Shows how to access and use the new documentation resources including:
- Static Splunk cheat sheet
- Dynamic troubleshooting documentation
- Version-aware resource creation
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Create a simple mock context for demo purposes
class MockContext:
    """Mock context for demo purposes."""

    def __init__(self):
        self.data = {}


from src.core.registry import resource_registry
from src.resources.splunk_docs import (
    DocumentationDiscoveryResource,
    SplunkCheatSheetResource,
    TroubleshootingResource,
    create_troubleshooting_resource,
    register_documentation_resources,
)


async def demo_cheat_sheet():
    """Demonstrate the static cheat sheet resource."""
    print("=" * 60)
    print("DEMO: Static Splunk Cheat Sheet Resource")
    print("=" * 60)

    # Create the cheat sheet resource
    cheat_sheet = SplunkCheatSheetResource()

    print(f"URI: {cheat_sheet.uri}")
    print(f"Name: {cheat_sheet.name}")
    print(f"Description: {cheat_sheet.description}")
    print()

    # Create a mock context (since we don't need Splunk connection for static content)
    ctx = MockContext()

    try:
        # Get the content (this will fetch from the actual URL)
        print("Fetching cheat sheet content...")
        content = await cheat_sheet.get_content(ctx)

        # Show first 500 characters
        print("Content preview:")
        print("-" * 40)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 40)
        print(f"Total content length: {len(content)} characters")

    except Exception as e:
        print(f"Error fetching cheat sheet: {e}")
        print("Note: This might happen if httpx is not installed or network issues exist")


async def demo_troubleshooting_resources():
    """Demonstrate the dynamic troubleshooting resources."""
    print("\n" + "=" * 60)
    print("DEMO: Dynamic Troubleshooting Resources")
    print("=" * 60)

    # Show available troubleshooting topics
    print("Available troubleshooting topics:")
    for topic, info in TroubleshootingResource.TROUBLESHOOTING_TOPICS.items():
        print(f"  - {topic}: {info['title']}")
    print()

    # Create troubleshooting resources for different versions
    versions = ["9.4.0", "latest"]
    topic = "metrics-log"

    for version in versions:
        print(f"--- Troubleshooting Resource: {topic} (version {version}) ---")

        try:
            # Create the resource
            troubleshooting_resource = create_troubleshooting_resource(version, topic)

            print(f"URI: {troubleshooting_resource.uri}")
            print(f"Name: {troubleshooting_resource.name}")
            print(f"Description: {troubleshooting_resource.description}")

            # Create a mock context
            ctx = MockContext()

            # Get the content
            print(f"Fetching troubleshooting content for {version}...")
            content = await troubleshooting_resource.get_content(ctx)

            # Show first 300 characters
            print("Content preview:")
            print("-" * 30)
            print(content[:300] + "..." if len(content) > 300 else content)
            print("-" * 30)
            print(f"Total content length: {len(content)} characters")

        except Exception as e:
            print(f"Error with troubleshooting resource: {e}")

        print()


async def demo_discovery_resource():
    """Demonstrate the enhanced discovery resource."""
    print("=" * 60)
    print("DEMO: Enhanced Documentation Discovery")
    print("=" * 60)

    # Create discovery resource
    discovery = DocumentationDiscoveryResource()

    print(f"URI: {discovery.uri}")
    print(f"Name: {discovery.name}")
    print(f"Description: {discovery.description}")
    print()

    # Create a mock context
    ctx = MockContext()

    try:
        print("Generating discovery content...")
        content = await discovery.get_content(ctx)

        # Show the discovery content (it includes our new resources)
        print("Discovery content:")
        print("-" * 40)
        print(content)
        print("-" * 40)

    except Exception as e:
        print(f"Error with discovery resource: {e}")


async def demo_resource_registry():
    """Demonstrate resource registration."""
    print("\n" + "=" * 60)
    print("DEMO: Resource Registry Integration")
    print("=" * 60)

    print("Registering documentation resources...")
    register_documentation_resources()

    # Show registered resources
    print("Registered documentation resources:")

    # Get all registered resources
    all_resources = resource_registry.list_resources()
    doc_resources = [r for r in all_resources if r.category == "documentation"]

    for resource in doc_resources:
        print(f"  - {resource.name}: {resource.description}")
        print(f"    URI: {resource.uri}")
        print(f"    Tags: {', '.join(resource.tags)}")
        print()


async def demo_uri_patterns():
    """Demonstrate URI patterns and usage examples."""
    print("=" * 60)
    print("DEMO: URI Patterns and Usage Examples")
    print("=" * 60)

    examples = [
        {
            "category": "Static Resources",
            "uris": [
                "splunk-docs://cheat-sheet",
            ],
        },
        {
            "category": "Troubleshooting (Version-aware)",
            "uris": [
                "splunk-docs://latest/troubleshooting/splunk-logs",
                "splunk-docs://9.4.0/troubleshooting/metrics-log",
                "splunk-docs://latest/troubleshooting/troubleshoot-inputs",
            ],
        },
        {
            "category": "SPL Reference (Existing)",
            "uris": [
                "splunk-docs://latest/spl-reference/stats",
                "splunk-docs://9.4.0/spl-reference/eval",
            ],
        },
        {
            "category": "Admin Guide (Existing)",
            "uris": [
                "splunk-docs://latest/admin/indexes",
                "splunk-docs://9.4.0/admin/authentication",
            ],
        },
        {
            "category": "Discovery",
            "uris": [
                "splunk-docs://discovery",
            ],
        },
    ]

    for example in examples:
        print(f"## {example['category']}")
        for uri in example["uris"]:
            print(f"  {uri}")
        print()


async def main():
    """Run all demonstrations."""
    print("Splunk Documentation Resources Demo")
    print("=" * 60)
    print("This demo shows the new documentation resources:")
    print("1. Static Splunk cheat sheet from official blog")
    print("2. Dynamic version-aware troubleshooting documentation")
    print("3. Enhanced discovery with new resource categories")
    print("4. Resource registry integration")
    print()

    # Set environment variable to avoid SSL verification issues in demo
    os.environ.setdefault("REQUESTS_CA_BUNDLE", "")

    try:
        # Run demonstrations
        await demo_uri_patterns()
        await demo_resource_registry()
        await demo_discovery_resource()
        await demo_cheat_sheet()
        await demo_troubleshooting_resources()

        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("✅ Static cheat sheet resource with caching")
        print("✅ Version-aware troubleshooting documentation")
        print("✅ Dynamic resource creation with helper functions")
        print("✅ Enhanced discovery resource")
        print("✅ Resource registry integration")
        print("✅ URI pattern examples")
        print("\nNext Steps:")
        print("- Try accessing these resources through the MCP server")
        print("- Use the URI patterns in your MCP client")
        print("- Explore the cached content and version management")

    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Check if httpx is available
    try:
        import httpx

        print("✅ httpx is available - full functionality enabled")
    except ImportError:
        print("⚠️  httpx not available - install with: pip install httpx")
        print("   Some features may show mock responses")

    print()

    # Run the demo
    asyncio.run(main())
