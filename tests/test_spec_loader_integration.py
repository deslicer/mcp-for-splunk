"""Test that SplunkSpecReferenceResource is properly loaded through the MCP loader."""

from unittest.mock import patch

import pytest
from fastmcp import FastMCP


def test_spec_reference_handler_registration():
    """Test that the spec reference handler is registered with FastMCP."""
    # Create a mock FastMCP server
    mcp = FastMCP("test-server")

    # Import the loader
    from src.core.loader import ResourceLoader

    # Create loader instance
    loader = ResourceLoader(mcp)

    # Track registered resources
    registered_resources = []
    original_resource = mcp.resource

    def track_resource(*args, **kwargs):
        """Track resource registrations."""
        if args:
            uri_pattern = args[0]
            registered_resources.append({"uri": uri_pattern, "name": kwargs.get("name", "unknown")})
        return original_resource(*args, **kwargs)

    # Patch the resource decorator
    with patch.object(mcp, "resource", side_effect=track_resource):
        # Call the registration method
        try:
            loader._register_dynamic_documentation_handlers()
        except Exception as e:
            # Expected - we're just tracking registrations, not actually running
            print(f"Expected error during mock registration: {e}")

    # Verify spec resource was registered
    spec_resources = [r for r in registered_resources if "spec" in r["uri"].lower()]

    print(f"\nAll registered resources: {registered_resources}")
    print(f"\nSpec resources found: {spec_resources}")

    assert len(spec_resources) > 0, "No spec resource handlers registered"

    # Check for the correct URI pattern (simplified to just config, no version)
    spec_uris = [r["uri"] for r in spec_resources]
    assert any("splunk-spec://{config}" in uri for uri in spec_uris), (
        f"Expected 'splunk-spec://{{config}}' pattern, got: {spec_uris}"
    )

    # Check for correct name
    spec_names = [r["name"] for r in spec_resources]
    assert "get_spec_reference_docs" in spec_names, (
        f"Expected 'get_spec_reference_docs' name, got: {spec_names}"
    )


def test_spec_reference_in_skip_list():
    """Test that spec reference URI is in the skip list."""
    # This is a code inspection test - verify the skip list exists
    import inspect

    from src.core.loader import ResourceLoader

    source = inspect.getsource(ResourceLoader._load_single_resource)

    # Check that the spec pattern is in the skip list (simplified pattern)
    assert "splunk-spec://{config}" in source, "Spec resource URI pattern not found in skip list"


def test_spec_reference_factory_exists():
    """Test that the factory function exists and is importable."""
    try:
        from src.resources.splunk_docs import create_spec_reference_resource

        # Verify it's callable
        assert callable(create_spec_reference_resource), (
            "create_spec_reference_resource is not callable"
        )

        print("✓ Factory function exists and is importable")

    except ImportError as e:
        pytest.fail(f"Cannot import create_spec_reference_resource: {e}")


if __name__ == "__main__":
    print("Testing Spec Resource Loader Integration\n")
    print("=" * 60)

    # Test 1: Handler registration
    print("\n1. Testing handler registration...")
    try:
        test_spec_reference_handler_registration()
        print("   ✓ Handler registration test passed")
    except AssertionError as e:
        print(f"   ✗ Handler registration test failed: {e}")

    # Test 2: Skip list
    print("\n2. Testing skip list inclusion...")
    try:
        test_spec_reference_in_skip_list()
        print("   ✓ Skip list test passed")
    except AssertionError as e:
        print(f"   ✗ Skip list test failed: {e}")

    # Test 3: Factory function
    print("\n3. Testing factory function...")
    try:
        test_spec_reference_factory_exists()
        print("   ✓ Factory function test passed")
    except Exception as e:
        print(f"   ✗ Factory function test failed: {e}")

    print("\n" + "=" * 60)
    print("✅ All loader integration tests completed!")
