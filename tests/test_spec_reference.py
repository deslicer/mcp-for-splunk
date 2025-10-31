"""
Tests for Splunk configuration spec reference resource.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.resources.splunk_docs import (
    SplunkSpecReferenceResource,
    create_spec_reference_resource,
)


class TestSplunkSpecReferenceResource:
    """Test suite for SplunkSpecReferenceResource."""

    def test_metadata(self):
        """Test that METADATA is correctly defined."""
        metadata = SplunkSpecReferenceResource.METADATA
        assert metadata.uri == "splunk-spec://{config}"
        assert metadata.name == "splunk_spec_reference"
        assert metadata.category == "reference"
        assert "spec" in metadata.tags
        assert "configuration" in metadata.tags

    def test_initialization(self):
        """Test resource initialization."""
        resource = SplunkSpecReferenceResource("alert_actions.conf")
        assert resource.config == "alert_actions.conf"
        assert resource.uri == "splunk-spec://alert_actions.conf"
        assert "spec_alert_actions_conf" in resource.name

    def test_normalize_config_name(self):
        """Test configuration name normalization."""
        resource = SplunkSpecReferenceResource("alert_actions")

        # Test adding .conf
        assert resource._normalize_config_name("alert_actions") == "alert_actions.conf"

        # Test keeping .conf
        assert resource._normalize_config_name("alert_actions.conf") == "alert_actions.conf"

        # Test stripping .spec suffix
        assert resource._normalize_config_name("alert_actions.conf.spec") == "alert_actions.conf"

    def test_parse_version_components(self):
        """Test version parsing into minor and full components."""
        resource = SplunkSpecReferenceResource("alert_actions.conf")

        # Test full version (X.Y.Z)
        minor, full = resource._parse_version_components("10.0.0")
        assert minor == "10.0"
        assert full == "10.0.0"

        # Test minor version (X.Y)
        minor, full = resource._parse_version_components("10.0")
        assert minor == "10.0"
        assert full == "10.0.0"

        # Test latest version
        minor, full = resource._parse_version_components("latest")
        assert minor == "10.0"
        assert full == "10.0.0"

        # Test auto version
        minor, full = resource._parse_version_components("auto")
        assert minor == "10.0"
        assert full == "10.0.0"

        # Test 9.4.0
        minor, full = resource._parse_version_components("9.4.0")
        assert minor == "9.4"
        assert full == "9.4.0"

    def test_factory_function(self):
        """Test factory function creates correct resource."""
        resource = create_spec_reference_resource("limits.conf")
        assert isinstance(resource, SplunkSpecReferenceResource)
        assert resource.config == "limits.conf"

    @pytest.mark.asyncio
    async def test_get_content_success(self):
        """Test successful content retrieval with auto-detected version."""
        resource = SplunkSpecReferenceResource("alert_actions.conf")

        mock_content = """# Alert Actions Configuration

This is the documentation for alert_actions.conf.

## Settings

- `maxresults`: Maximum number of results
"""

        # Mock both get_splunk_version and fetch_doc_content
        with patch.object(resource, "get_splunk_version", new_callable=AsyncMock) as mock_version:
            mock_version.return_value = "10.0"

            with patch.object(resource, "fetch_doc_content", new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = mock_content

                # Mock context
                mock_ctx = AsyncMock()

                content = await resource.get_content(mock_ctx)

                # Verify version detection was called
                mock_version.assert_called_once_with(mock_ctx)

                # Verify the content includes metadata
                assert "# Splunk Configuration Spec: alert_actions.conf" in content
                assert "Version**: Splunk 10.0" in content
                assert "Configuration File Reference" in content
                assert "Source URL" in content
                assert mock_content in content

                # Verify URL construction
                mock_fetch.assert_called_once()
                called_url = mock_fetch.call_args[0][0]
                assert "/en/splunk-enterprise/administer/admin-manual/10.0/" in called_url
                assert "10.0.0-configuration-file-reference" in called_url
                assert "alert_actions.conf" in called_url

    @pytest.mark.asyncio
    async def test_get_content_fallback(self):
        """Test fallback URL when primary fails."""
        resource = SplunkSpecReferenceResource("limits.conf")

        primary_response = "# Documentation Not Found\n\nThe requested documentation was not found."
        fallback_response = "# Limits Configuration\n\nThis is the limits.conf documentation."

        with patch.object(resource, "get_splunk_version", new_callable=AsyncMock) as mock_version:
            mock_version.return_value = "10.0"

            with patch.object(resource, "fetch_doc_content", new_callable=AsyncMock) as mock_fetch:
                # First call returns 404, second call returns content
                mock_fetch.side_effect = [primary_response, fallback_response]

                mock_ctx = AsyncMock()
                content = await resource.get_content(mock_ctx)

                # Verify fallback was used
                assert "# Splunk Configuration Spec: limits.conf" in content
                assert "Limits Configuration" in content
                assert mock_fetch.call_count == 2

                # Verify both URLs were tried
                first_url = mock_fetch.call_args_list[0][0][0]
                second_url = mock_fetch.call_args_list[1][0][0]

                assert "/en/splunk-enterprise/administer/admin-manual/" in first_url
                assert "/en/data-management/splunk-enterprise-admin-manual/" in second_url

    @pytest.mark.asyncio
    async def test_get_content_both_fail(self):
        """Test error handling when both URLs fail."""
        resource = SplunkSpecReferenceResource("nonexistent.conf")

        not_found_response = (
            "# Documentation Not Found\n\nThe requested documentation was not found."
        )

        with patch.object(resource, "get_splunk_version", new_callable=AsyncMock) as mock_version:
            mock_version.return_value = "10.0"

            with patch.object(resource, "fetch_doc_content", new_callable=AsyncMock) as mock_fetch:
                # Both calls return 404
                mock_fetch.side_effect = [not_found_response, not_found_response]

                mock_ctx = AsyncMock()
                content = await resource.get_content(mock_ctx)

                # Verify error message
                assert "# Configuration Spec Not Found" in content
                assert "nonexistent.conf" in content
                assert "Attempted URLs" in content
                assert mock_fetch.call_count == 2

    def test_url_construction_versions(self):
        """Test URL construction for different version formats."""
        # Test 10.0.0
        resource = SplunkSpecReferenceResource("alert_actions.conf")
        minor, full = resource._parse_version_components("10.0.0")
        assert minor == "10.0"
        assert full == "10.0.0"

        # Test 9.4
        resource = SplunkSpecReferenceResource("limits.conf")
        minor, full = resource._parse_version_components("9.4")
        assert minor == "9.4"
        assert full == "9.4.0"

        # Test 9.3.0
        resource = SplunkSpecReferenceResource("inputs.conf")
        minor, full = resource._parse_version_components("9.3.0")
        assert minor == "9.3"
        assert full == "9.3.0"
