"""
Tests for Dashboard Studio documentation resources.
"""

import pytest

from src.core.registry import resource_registry
from src.resources.dashboard_studio_docs import (
    DASHBOARD_STUDIO_TOPICS,
    DashboardStudioDiscoveryResource,
    DashboardStudioDocsResource,
)


# Mock Context for testing
class MockContext:
    pass


class TestDashboardStudioResources:
    """Test Dashboard Studio documentation resources."""

    def test_cheatsheet_resource_metadata(self):
        """Test cheatsheet resource has correct metadata."""
        resource = DashboardStudioDocsResource("cheatsheet")

        assert resource.uri == "dashboard-studio://cheatsheet"
        assert "Dashboard Studio Cheatsheet" in resource.name
        assert (
            "cheatsheet" in resource.description.lower()
            or "comprehensive" in resource.description.lower()
        )
        assert resource.mime_type == "text/markdown"

    def test_discovery_resource_metadata(self):
        """Test discovery resource has correct metadata."""
        resource = DashboardStudioDiscoveryResource()

        assert resource.uri == "dashboard-studio://discovery"
        assert resource.name == "dashboard_studio_discovery"
        assert (
            "discovery" in resource.description.lower() or "index" in resource.description.lower()
        )
        assert resource.mime_type == "text/markdown"

    @pytest.mark.asyncio
    async def test_cheatsheet_content_loads(self):
        """Test cheatsheet content loads successfully."""
        resource = DashboardStudioDocsResource("cheatsheet")
        ctx = MockContext()

        content = await resource.get_content(ctx)

        assert content is not None
        assert len(content) > 0
        # Check for key sections
        assert "Dashboard Studio" in content or "cheatsheet" in content.lower()
        assert "version" in content.lower()
        assert "datasources" in content.lower() or "data" in content.lower()
        assert "visualizations" in content.lower()

    @pytest.mark.asyncio
    async def test_cheatsheet_has_examples(self):
        """Test cheatsheet contains JSON examples."""
        resource = DashboardStudioDocsResource("cheatsheet")
        ctx = MockContext()

        content = await resource.get_content(ctx)

        # Check for JSON code blocks with key structure
        assert "```json" in content or "```" in content
        # Content should have dashboard-related structure
        assert "version" in content.lower() or "title" in content.lower()

    @pytest.mark.asyncio
    async def test_discovery_content_structure(self):
        """Test discovery resource has expected structure."""
        resource = DashboardStudioDiscoveryResource()
        ctx = MockContext()

        content = await resource.get_content(ctx)

        assert content is not None
        assert len(content) > 0

        # Check for expected content
        expected_content = [
            "Dashboard Studio",
            "discovery",
            "cheatsheet",
            "dashboard-studio://",
        ]

        for expected in expected_content:
            assert expected.lower() in content.lower()

    @pytest.mark.asyncio
    async def test_discovery_has_topics_list(self):
        """Test discovery resource references available topics."""
        resource = DashboardStudioDiscoveryResource()
        ctx = MockContext()

        content = await resource.get_content(ctx)

        # Check for key documentation topics from DASHBOARD_STUDIO_TOPICS
        assert "cheatsheet" in content.lower()
        assert "visualization" in content.lower()
        assert "definition" in content.lower() or "schema" in content.lower()

    def test_resources_registered_in_registry(self):
        """Test resources are registered in the resource registry."""
        # Get all registered resources
        registered_uris = [metadata.uri for metadata in resource_registry.list_resources()]

        # Check resources are registered with template pattern
        # Note: The dynamic resource uses a template URI pattern
        assert any("dashboard-studio" in uri for uri in registered_uris)
        assert "dashboard-studio://discovery" in registered_uris

    def test_metadata_tags(self):
        """Test resources have appropriate tags."""
        # Test cheatsheet resource tags
        assert "dashboard-studio" in DashboardStudioDocsResource.METADATA.tags

        # Test discovery resource tags
        discovery_metadata = DashboardStudioDiscoveryResource.METADATA
        assert "dashboard-studio" in discovery_metadata.tags
        assert "discovery" in discovery_metadata.tags or "index" in discovery_metadata.tags

    def test_available_topics(self):
        """Test that DASHBOARD_STUDIO_TOPICS contains expected topics."""
        assert "cheatsheet" in DASHBOARD_STUDIO_TOPICS
        assert "definition" in DASHBOARD_STUDIO_TOPICS
        assert "visualizations" in DASHBOARD_STUDIO_TOPICS

        # Verify cheatsheet has a file reference
        assert "file" in DASHBOARD_STUDIO_TOPICS["cheatsheet"]

    def test_dynamic_resource_creation(self):
        """Test creating resources for different topics."""
        # Create resources for different topics
        cheatsheet = DashboardStudioDocsResource("cheatsheet")
        definition = DashboardStudioDocsResource("definition")
        visualizations = DashboardStudioDocsResource("visualizations")

        # Verify URIs are correct
        assert cheatsheet.uri == "dashboard-studio://cheatsheet"
        assert definition.uri == "dashboard-studio://definition"
        assert visualizations.uri == "dashboard-studio://visualizations"

        # Verify mime types
        assert cheatsheet.mime_type == "text/markdown"
        assert definition.mime_type == "text/markdown"
        assert visualizations.mime_type == "text/markdown"
