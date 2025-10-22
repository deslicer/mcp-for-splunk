"""
Tests for Dashboard Studio documentation resources.
"""

import pytest

from src.core.registry import resource_registry
from src.resources.dashboard_studio_docs import (
    DashboardStudioCheatsheetResource,
    DashboardStudioLinksResource,
)


# Mock Context for testing
class MockContext:
    pass


class TestDashboardStudioResources:
    """Test Dashboard Studio documentation resources."""

    def test_cheatsheet_resource_metadata(self):
        """Test cheatsheet resource has correct metadata."""
        resource = DashboardStudioCheatsheetResource()

        assert resource.uri == "dashboard-studio://cheatsheet"
        assert resource.name == "dashboard_studio_cheatsheet"
        assert "Dashboard Studio" in resource.description
        assert resource.mime_type == "text/markdown"

    def test_links_resource_metadata(self):
        """Test links resource has correct metadata."""
        resource = DashboardStudioLinksResource()

        assert resource.uri == "dashboard-studio://links"
        assert resource.name == "dashboard_studio_links"
        assert "documentation links" in resource.description
        assert resource.mime_type == "text/markdown"

    @pytest.mark.asyncio
    async def test_cheatsheet_content_loads(self):
        """Test cheatsheet content loads successfully."""
        resource = DashboardStudioCheatsheetResource()
        ctx = MockContext()

        content = await resource.get_content(ctx)

        assert content is not None
        assert len(content) > 0
        # Check for key sections
        assert "Dashboard Studio Cheatsheet" in content or "cheatsheet" in content.lower()
        assert "version" in content
        assert "dataSources" in content or "data" in content.lower()
        assert "visualizations" in content

    @pytest.mark.asyncio
    async def test_cheatsheet_has_examples(self):
        """Test cheatsheet contains JSON examples."""
        resource = DashboardStudioCheatsheetResource()
        ctx = MockContext()

        content = await resource.get_content(ctx)

        # Check for JSON code blocks with key structure
        assert "```json" in content or "```" in content
        assert '"version"' in content or "version" in content
        assert '"title"' in content or "title" in content

    @pytest.mark.asyncio
    async def test_links_content_structure(self):
        """Test links resource has expected URLs and structure."""
        resource = DashboardStudioLinksResource()
        ctx = MockContext()

        content = await resource.get_content(ctx)

        assert content is not None
        assert len(content) > 0

        # Check for expected URLs
        expected_urls = [
            "splunkui.splunk.com/Packages/dashboard-docs",
            "help.splunk.com",
            "9.4",  # Version reference
        ]

        for url_part in expected_urls:
            assert url_part in content

    @pytest.mark.asyncio
    async def test_links_has_canonical_docs(self):
        """Test links resource references canonical documentation."""
        resource = DashboardStudioLinksResource()
        ctx = MockContext()

        content = await resource.get_content(ctx)

        # Check for key documentation topics
        assert "Dashboard Framework" in content or "Framework" in content
        assert "visualization" in content.lower()
        assert "definition" in content.lower()

    def test_resources_registered_in_registry(self):
        """Test resources are registered in the resource registry."""
        # Get all registered resources
        registered_uris = [metadata.uri for metadata in resource_registry.list_resources()]

        # Check both resources are registered
        assert "dashboard-studio://cheatsheet" in registered_uris
        assert "dashboard-studio://links" in registered_uris

    def test_cheatsheet_metadata_tags(self):
        """Test cheatsheet has appropriate tags."""
        metadata = DashboardStudioCheatsheetResource.METADATA

        assert "dashboard-studio" in metadata.tags
        assert "reference" in metadata.tags or "cheatsheet" in metadata.tags

    def test_links_metadata_tags(self):
        """Test links resource has appropriate tags."""
        metadata = DashboardStudioLinksResource.METADATA

        assert "dashboard-studio" in metadata.tags
        assert "documentation" in metadata.tags or "links" in metadata.tags
