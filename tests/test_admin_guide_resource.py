"""
Tests for Splunk administration guide documentation resources.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.resources.splunk_docs import AdminGuideResource, _doc_cache


class TestAdminGuideResource:
    """Test suite for AdminGuideResource."""

    @pytest.mark.asyncio
    async def test_indexes_topic_uses_current_indexes_documentation_url(self):
        """Test indexes admin docs use the current Splunk Help data-management path."""
        resource = AdminGuideResource("10.0", "indexes")
        mock_content = "# About managing indexes\n\nIndexes store Splunk Enterprise data."

        with patch.object(resource, "fetch_doc_content", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_content

            content = await resource.get_content(AsyncMock())

            assert "# Splunk Administration: indexes" in content
            assert "About managing indexes" in content

            called_url = mock_fetch.call_args[0][0]
            assert called_url == (
                "https://help.splunk.com/en/data-management/"
                "manage-splunk-enterprise-indexers/10.0/"
                "manage-indexes/about-managing-indexes"
            )

    @pytest.mark.asyncio
    async def test_failed_admin_fetch_is_not_wrapped_as_success(self):
        """Error bodies stay unwrapped so the docs cache will not store them."""
        resource = AdminGuideResource("10.2", "users")
        _doc_cache.cache.clear()
        with patch.object(resource, "fetch_doc_content", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "# Documentation Error\n\nsoft 404"

            content = await resource.get_content(AsyncMock())

            assert content.startswith("# Documentation Error")
            assert "# Splunk Administration:" not in content
