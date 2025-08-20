"""
Comprehensive tests for enhanced embedded resources.

Tests all aspects of the embedded resources system including:
- Content validation
- Caching mechanisms
- Registry operations
- Error handling
- Template functionality
- Splunk integration
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.base import ResourceMetadata
from src.resources.embedded import (
    ContentValidator,
    EmbeddedResource,
    EmbeddedResourceRegistry,
    FileEmbeddedResource,
    ResourceTemplate,
    SplunkEmbeddedResource,
    TemplateEmbeddedResource,
)


# Mock Context for testing
class Context:
    pass


class TestContentValidator:
    """Test content validation functionality."""

    def test_validate_json_valid(self):
        """Test JSON validation with valid JSON."""
        content = '{"key": "value", "number": 42}'
        result = ContentValidator.validate_json(content)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_json_invalid(self):
        """Test JSON validation with invalid JSON."""
        content = '{"key": "value", "number": 42'  # Missing closing brace
        result = ContentValidator.validate_json(content)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Invalid JSON" in result.errors[0]

    def test_validate_markdown_valid(self):
        """Test Markdown validation with valid content."""
        content = "# Title\n\nThis is valid markdown content."
        result = ContentValidator.validate_markdown(content)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_markdown_empty(self):
        """Test Markdown validation with empty content."""
        content = ""
        result = ContentValidator.validate_markdown(content)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Empty content" in result.errors[0]

    def test_validate_markdown_many_headers(self):
        """Test Markdown validation with too many headers."""
        content = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\n# H7\n## H8\n### H9\n#### H10\n##### H11"
        result = ContentValidator.validate_markdown(content)

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "Many headers detected" in result.warnings[0]

    def test_validate_text_valid(self):
        """Test text validation with valid content."""
        content = "This is valid text content."
        result = ContentValidator.validate_text(content)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_text_empty(self):
        """Test text validation with empty content."""
        content = ""
        result = ContentValidator.validate_text(content)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Empty content" in result.errors[0]

    def test_validate_text_large(self):
        """Test text validation with large content."""
        content = "x" * 1000001  # Over 1MB
        result = ContentValidator.validate_text(content)

        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert "Large content detected" in result.warnings[0]


class TestEmbeddedResource:
    """Test the base EmbeddedResource class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock(spec=Context)
        return ctx

    def test_embedded_resource_creation(self):
        """Test embedded resource creation with basic parameters."""
        resource = EmbeddedResource(
            uri="embedded://test/resource",
            name="Test Resource",
            description="A test resource",
            mime_type="text/plain",
            embedded_content="Test content"
        )

        assert resource.uri == "embedded://test/resource"
        assert resource.name == "Test Resource"
        assert resource.description == "A test resource"
        assert resource.mime_type == "text/plain"
        assert resource.embedded_content == "Test content"
        assert resource.validate_content is True
        assert resource.etag_enabled is True

    def test_embedded_resource_with_binary_content(self):
        """Test embedded resource with binary content."""
        binary_data = b"binary content"
        resource = EmbeddedResource(
            uri="embedded://test/binary",
            name="Binary Resource",
            description="A binary resource",
            mime_type="application/octet-stream",
            embedded_content=binary_data
        )

        assert resource.embedded_content == binary_data

    def test_embedded_resource_cache_settings(self):
        """Test embedded resource cache configuration."""
        resource = EmbeddedResource(
            uri="embedded://test/cached",
            name="Cached Resource",
            description="A cached resource",
            cache_ttl=600,
            validate_content=False,
            etag_enabled=False
        )

        assert resource.cache_ttl == 600
        assert resource.validate_content is False
        assert resource.etag_enabled is False

    @pytest.mark.asyncio
    async def test_get_content_with_embedded_text(self, mock_context):
        """Test getting content from embedded text resource."""
        resource = EmbeddedResource(
            uri="embedded://test/text",
            name="Text Resource",
            description="A text resource",
            embedded_content="Hello, World!"
        )

        content = await resource.get_content(mock_context)
        assert content == "Hello, World!"

    @pytest.mark.asyncio
    async def test_get_content_with_embedded_binary(self, mock_context):
        """Test getting content from embedded binary resource."""
        binary_data = b"binary content"
        resource = EmbeddedResource(
            uri="embedded://test/binary",
            name="Binary Resource",
            description="A binary resource",
            embedded_content=binary_data,
            mime_type="application/octet-stream"
        )

        content = await resource.get_content(mock_context)
        content_data = json.loads(content)

        assert content_data["type"] == "binary"
        assert content_data["mime_type"] == "application/octet-stream"
        assert content_data["size"] == len(binary_data)
        assert "data" in content_data

    @pytest.mark.asyncio
    async def test_get_content_with_dynamic_generation(self, mock_context):
        """Test getting content from resource that generates content dynamically."""
        class DynamicResource(EmbeddedResource):
            async def _generate_dynamic_content(self, ctx):
                return "Dynamic content generated"

        resource = DynamicResource(
            uri="embedded://test/dynamic",
            name="Dynamic Resource",
            description="A dynamic resource"
        )

        content = await resource.get_content(mock_context)
        assert content == "Dynamic content generated"

    @pytest.mark.asyncio
    async def test_get_content_with_validation_error(self, mock_context):
        """Test getting content with validation errors."""
        resource = EmbeddedResource(
            uri="embedded://test/invalid",
            name="Invalid Resource",
            description="An invalid resource",
            embedded_content='{"invalid": json',  # Invalid JSON
            mime_type="application/json",
            validate_content=True
        )

        content = await resource.get_content(mock_context)
        # Should still return content but log validation warning
        assert "invalid" in content

    def test_generate_etag(self):
        """Test ETag generation."""
        resource = EmbeddedResource(
            uri="embedded://test/etag",
            name="ETag Resource",
            description="A resource with ETag",
            embedded_content="Test content"
        )

        etag = resource._generate_etag()
        assert etag is not None
        assert etag.startswith('"')
        assert etag.endswith('"')

    def test_generate_etag_disabled(self):
        """Test ETag generation when disabled."""
        resource = EmbeddedResource(
            uri="embedded://test/no-etag",
            name="No ETag Resource",
            description="A resource without ETag",
            embedded_content="Test content",
            etag_enabled=False
        )

        etag = resource._generate_etag()
        assert etag is None

    def test_cache_validation(self):
        """Test cache validation logic."""
        resource = EmbeddedResource(
            uri="embedded://test/cache",
            name="Cache Resource",
            description="A cached resource",
            cache_ttl=300
        )

        # Initially no cache
        assert resource._is_cache_valid() is False

        # Cache some content
        resource._cache_content("cached content")
        assert resource._is_cache_valid() is True

        # Simulate cache expiration
        resource._cache_timestamp = 0
        assert resource._is_cache_valid() is False

    def test_create_error_response(self):
        """Test error response creation."""
        resource = EmbeddedResource(
            uri="embedded://test/error",
            name="Error Resource",
            description="A resource for testing errors"
        )

        error_response = resource._create_error_response("Test error")
        error_data = json.loads(error_response)

        assert error_data["error"] == "Test error"
        assert error_data["uri"] == "embedded://test/error"
        assert error_data["type"] == "error"
        assert "timestamp" in error_data

    def test_get_metadata(self):
        """Test metadata generation."""
        resource = EmbeddedResource(
            uri="embedded://test/metadata",
            name="Metadata Resource",
            description="A resource for testing metadata",
            cache_ttl=600
        )

        metadata = resource.get_metadata()

        assert isinstance(metadata, ResourceMetadata)
        assert metadata.uri == "embedded://test/metadata"
        assert metadata.name == "Metadata Resource"
        assert metadata.description == "A resource for testing metadata"
        assert metadata.category == "embedded"
        assert "embedded" in metadata.tags
        assert "cached" in metadata.tags


class TestFileEmbeddedResource:
    """Test the FileEmbeddedResource class."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test file content")
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)

    @pytest.fixture
    def temp_json_file(self):
        """Create a temporary JSON file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({"key": "value", "number": 42}, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        os.unlink(temp_path)

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock(spec=Context)
        return ctx

    def test_file_resource_creation(self, temp_file):
        """Test file resource creation."""
        resource = FileEmbeddedResource(
            uri="embedded://file/test",
            name="File Resource",
            description="A file resource",
            file_path=temp_file,
            mime_type="text/plain"
        )

        assert resource.file_path == Path(temp_file)
        assert resource.mime_type == "text/plain"
        assert resource.encoding == "utf-8"
        assert resource.watch_file is False

    def test_file_resource_auto_mime_detection(self, temp_file):
        """Test automatic MIME type detection."""
        resource = FileEmbeddedResource(
            uri="embedded://file/test",
            name="File Resource",
            description="A file resource",
            file_path=temp_file
        )

        # Should auto-detect text/plain for .txt file
        assert resource.mime_type == "text/plain"

    def test_file_resource_json_mime_detection(self, temp_json_file):
        """Test MIME type detection for JSON files."""
        resource = FileEmbeddedResource(
            uri="embedded://file/test",
            name="File Resource",
            description="A file resource",
            file_path=temp_json_file
        )

        # Should auto-detect application/json for .json file
        assert resource.mime_type == "application/json"

    @pytest.mark.asyncio
    async def test_get_content_from_text_file(self, temp_file, mock_context):
        """Test getting content from text file."""
        resource = FileEmbeddedResource(
            uri="embedded://file/test",
            name="File Resource",
            description="A file resource",
            file_path=temp_file
        )

        content = await resource.get_content(mock_context)
        assert content == "Test file content"

    @pytest.mark.asyncio
    async def test_get_content_from_json_file(self, temp_json_file, mock_context):
        """Test getting content from JSON file."""
        resource = FileEmbeddedResource(
            uri="embedded://file/test",
            name="File Resource",
            description="A file resource",
            file_path=temp_json_file
        )

        content = await resource.get_content(mock_context)
        # Should return JSON as text
        assert '"key": "value"' in content

    @pytest.mark.asyncio
    async def test_get_content_file_not_found(self, mock_context):
        """Test getting content from non-existent file."""
        resource = FileEmbeddedResource(
            uri="embedded://file/missing",
            name="Missing File Resource",
            description="A missing file resource",
            file_path="/nonexistent/file.txt"
        )

        content = await resource.get_content(mock_context)
        error_data = json.loads(content)

        assert error_data["error"].startswith("File not found")
        assert error_data["type"] == "error"

    @pytest.mark.asyncio
    async def test_get_content_with_file_watching(self, temp_file, mock_context):
        """Test file watching functionality."""
        resource = FileEmbeddedResource(
            uri="embedded://file/watched",
            name="Watched File Resource",
            description="A watched file resource",
            file_path=temp_file,
            watch_file=True
        )

        # First access
        content1 = await resource.get_content(mock_context)
        assert content1 == "Test file content"

        # Simulate file change by updating the file
        with open(temp_file, 'w') as f:
            f.write("Updated content")

        # Second access should detect change
        content2 = await resource.get_content(mock_context)
        assert content2 == "Updated content"

    @pytest.mark.asyncio
    async def test_get_content_with_different_encoding(self, temp_file, mock_context):
        """Test file reading with different encoding."""
        # Create file with specific encoding
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write("Content with special chars: éñü")

        resource = FileEmbeddedResource(
            uri="embedded://file/encoded",
            name="Encoded File Resource",
            description="A file resource with encoding",
            file_path=temp_file,
            encoding="utf-8"
        )

        content = await resource.get_content(mock_context)
        assert "éñü" in content


class TestTemplateEmbeddedResource:
    """Test the TemplateEmbeddedResource class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock(spec=Context)
        return ctx

    def test_template_resource_creation(self):
        """Test template resource creation."""
        class TestTemplateResource(TemplateEmbeddedResource):
            async def _generate_content_from_params(self, ctx, params):
                return "Generated content"

        resource = TestTemplateResource(
            uri_template="embedded://template/{param}",
            name="Template Resource",
            description="A template resource",
            mime_type="text/plain"
        )

        assert resource.uri_template == "embedded://template/{param}"
        assert resource.parameter_validators == {}

    def test_template_resource_with_validators(self):
        """Test template resource with parameter validators."""
        def validate_param(value):
            if not value.isalpha():
                raise ValueError("Parameter must be alphabetic")

        class TestTemplateResource(TemplateEmbeddedResource):
            async def _generate_content_from_params(self, ctx, params):
                return "Generated content"

        resource = TestTemplateResource(
            uri_template="embedded://template/{param}",
            name="Template Resource",
            description="A template resource",
            parameter_validators={"param": validate_param}
        )

        assert "param" in resource.parameter_validators

    def test_extract_uri_parameters(self):
        """Test URI parameter extraction."""
        class TestTemplateResource(TemplateEmbeddedResource):
            async def _generate_content_from_params(self, ctx, params):
                return "Generated content"

        resource = TestTemplateResource(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        uri = "embedded://docs/api/README.md"
        params = resource._extract_uri_parameters(uri)

        assert params["category"] == "api"
        assert params["filename"] == "README.md"

    def test_extract_uri_parameters_no_match(self):
        """Test URI parameter extraction with no match."""
        class TestTemplateResource(TemplateEmbeddedResource):
            async def _generate_content_from_params(self, ctx, params):
                return "Generated content"

        resource = TestTemplateResource(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        uri = "embedded://other/path"
        params = resource._extract_uri_parameters(uri)

        assert params == {}

    def test_validate_parameters(self):
        """Test parameter validation."""
        def validate_param(value):
            if not value.isalpha():
                raise ValueError("Parameter must be alphabetic")

        class TestTemplateResource(TemplateEmbeddedResource):
            async def _generate_content_from_params(self, ctx, params):
                return "Generated content"

        resource = TestTemplateResource(
            uri_template="embedded://template/{param}",
            name="Template Resource",
            description="A template resource",
            parameter_validators={"param": validate_param}
        )

        # Valid parameter
        params = {"param": "valid"}
        errors = resource._validate_parameters(params)
        assert len(errors) == 0

        # Invalid parameter
        params = {"param": "123"}
        errors = resource._validate_parameters(params)
        assert len(errors) == 1
        assert "Parameter 'param' validation failed" in errors[0]

    @pytest.mark.asyncio
    async def test_get_content_with_parameters(self, mock_context):
        """Test getting content with URI parameters."""
        class TestTemplateResource(TemplateEmbeddedResource):
            async def _generate_content_from_params(self, ctx, params):
                return f"Generated content for {params.get('category', 'unknown')}"

        resource = TestTemplateResource(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        content = await resource.get_content(mock_context, uri="embedded://docs/api/README.md")
        assert content == "Generated content for api"

    @pytest.mark.asyncio
    async def test_get_content_with_validation_error(self, mock_context):
        """Test getting content with parameter validation error."""
        def validate_param(value):
            if not value.isalpha():
                raise ValueError("Parameter must be alphabetic")

        class TestTemplateResource(TemplateEmbeddedResource):
            async def _generate_content_from_params(self, ctx, params):
                return "Generated content"

        resource = TestTemplateResource(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template",
            parameter_validators={"category": validate_param}
        )

        content = await resource.get_content(mock_context, uri="embedded://docs/123/README.md")
        error_data = json.loads(content)

        assert "Parameter validation failed" in error_data["error"]


class TestResourceTemplate:
    """Test the ResourceTemplate class."""

    def test_template_creation(self):
        """Test template creation."""
        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template",
            mime_type="text/markdown"
        )

        assert template.uri_template == "embedded://docs/{category}/{filename}"
        assert template.name == "Documentation Template"
        assert template.mime_type == "text/markdown"

    def test_template_with_parameter_types(self):
        """Test template with parameter types."""
        template = ResourceTemplate(
            uri_template="embedded://data/{id}/{format}",
            name="Data Template",
            description="A data template",
            parameter_types={"id": int, "format": str},
            parameter_defaults={"format": "json"}
        )

        assert template.parameter_types["id"] == int
        assert template.parameter_types["format"] == str
        assert template.parameter_defaults["format"] == "json"

    def test_template_expand(self):
        """Test template expansion."""
        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        expanded = template.expand(category="api", filename="README.md")
        assert expanded == "embedded://docs/api/README.md"

    def test_template_expand_with_type_conversion(self):
        """Test template expansion with type conversion."""
        template = ResourceTemplate(
            uri_template="embedded://data/{id}/{format}",
            name="Data Template",
            description="A data template",
            parameter_types={"id": int, "format": str}
        )

        expanded = template.expand(id="123", format="json")
        assert expanded == "embedded://data/123/json"

    def test_template_expand_with_defaults(self):
        """Test template expansion with default parameters."""
        template = ResourceTemplate(
            uri_template="embedded://data/{id}/{format}",
            name="Data Template",
            description="A data template",
            parameter_defaults={"format": "json"}
        )

        expanded = template.expand(id="123")
        assert expanded == "embedded://data/123/json"

    def test_template_expand_missing_parameter(self):
        """Test template expansion with missing parameter."""
        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        with pytest.raises(ValueError, match="Missing required parameter"):
            template.expand(category="api")

    def test_template_expand_type_conversion_error(self):
        """Test template expansion with type conversion error."""
        template = ResourceTemplate(
            uri_template="embedded://data/{id}/{format}",
            name="Data Template",
            description="A data template",
            parameter_types={"id": int}
        )

        with pytest.raises(ValueError, match="type conversion failed"):
            template.expand(id="invalid", format="json")

    def test_template_validate_parameters(self):
        """Test parameter validation."""
        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template",
            parameter_types={"category": str, "filename": str},
            parameter_defaults={"category": "general"}
        )

        # Valid parameters
        errors = template.validate_parameters(category="api", filename="README.md")
        assert len(errors) == 0

        # Missing required parameter
        errors = template.validate_parameters(category="api")
        assert len(errors) == 0  # filename has default

        # Invalid type
        errors = template.validate_parameters(category=123, filename="README.md")
        assert len(errors) == 1
        assert "type validation failed" in errors[0]

    def test_template_get_metadata(self):
        """Test template metadata generation."""
        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template",
            mime_type="text/markdown"
        )

        metadata = template.get_metadata()

        assert isinstance(metadata, ResourceMetadata)
        assert metadata.uri == "embedded://docs/{category}/{filename}"
        assert metadata.name == "Documentation Template"
        assert metadata.description == "A documentation template"
        assert metadata.mime_type == "text/markdown"
        assert metadata.category == "template"
        assert "template" in metadata.tags
        assert "dynamic" in metadata.tags
        assert "parameterized" in metadata.tags


class TestEmbeddedResourceRegistry:
    """Test the EmbeddedResourceRegistry class."""

    def test_registry_creation(self):
        """Test registry creation."""
        registry = EmbeddedResourceRegistry()

        assert len(registry._resources) == 0
        assert len(registry._templates) == 0
        assert len(registry._metadata) == 0
        assert len(registry._access_stats) == 0

    def test_register_embedded_resource(self):
        """Test registering an embedded resource."""
        registry = EmbeddedResourceRegistry()

        resource = EmbeddedResource(
            uri="embedded://test/resource",
            name="Test Resource",
            description="A test resource",
            embedded_content="Test content"
        )

        registry.register_embedded_resource(resource)

        assert "embedded://test/resource" in registry._resources
        assert "embedded://test/resource" in registry._metadata
        assert "embedded://test/resource" in registry._access_stats

    def test_register_template(self):
        """Test registering a template."""
        registry = EmbeddedResourceRegistry()

        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        registry.register_template(template)

        assert "embedded://docs/{category}/{filename}" in registry._templates
        assert "embedded://docs/{category}/{filename}" in registry._metadata

    def test_get_resource(self):
        """Test getting a resource."""
        registry = EmbeddedResourceRegistry()

        resource = EmbeddedResource(
            uri="embedded://test/resource",
            name="Test Resource",
            description="A test resource",
            embedded_content="Test content"
        )

        registry.register_embedded_resource(resource)

        retrieved = registry.get_resource("embedded://test/resource")
        assert retrieved == resource

        # Check access statistics
        stats = registry._access_stats["embedded://test/resource"]
        assert stats["access_count"] == 1
        assert stats["last_accessed"] is not None

    def test_get_resource_not_found(self):
        """Test getting a non-existent resource."""
        registry = EmbeddedResourceRegistry()

        resource = registry.get_resource("embedded://test/missing")
        assert resource is None

    def test_get_template(self):
        """Test getting a template."""
        registry = EmbeddedResourceRegistry()

        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        registry.register_template(template)

        retrieved = registry.get_template("embedded://docs/{category}/{filename}")
        assert retrieved == template

    def test_get_template_not_found(self):
        """Test getting a non-existent template."""
        registry = EmbeddedResourceRegistry()

        template = registry.get_template("embedded://test/missing")
        assert template is None

    def test_list_resources(self):
        """Test listing resources."""
        registry = EmbeddedResourceRegistry()

        resource1 = EmbeddedResource(
            uri="embedded://test/resource1",
            name="Test Resource 1",
            description="A test resource",
            embedded_content="Test content 1"
        )

        resource2 = EmbeddedResource(
            uri="embedded://test/resource2",
            name="Test Resource 2",
            description="Another test resource",
            embedded_content="Test content 2"
        )

        registry.register_embedded_resource(resource1)
        registry.register_embedded_resource(resource2)

        resources = registry.list_resources()
        assert len(resources) == 2

        uris = [r.uri for r in resources]
        assert "embedded://test/resource1" in uris
        assert "embedded://test/resource2" in uris

    def test_list_templates(self):
        """Test listing templates."""
        registry = EmbeddedResourceRegistry()

        template1 = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        template2 = ResourceTemplate(
            uri_template="embedded://data/{id}/{format}",
            name="Data Template",
            description="A data template"
        )

        registry.register_template(template1)
        registry.register_template(template2)

        templates = registry.list_templates()
        assert len(templates) == 2

    def test_get_statistics(self):
        """Test getting registry statistics."""
        registry = EmbeddedResourceRegistry()

        resource = EmbeddedResource(
            uri="embedded://test/resource",
            name="Test Resource",
            description="A test resource",
            embedded_content="Test content"
        )

        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template"
        )

        registry.register_embedded_resource(resource)
        registry.register_template(template)

        # Access the resource to generate statistics
        registry.get_resource("embedded://test/resource")

        stats = registry.get_statistics()

        assert stats["total_resources"] == 1
        assert stats["total_templates"] == 1
        assert stats["total_accesses"] == 1
        assert "embedded://test/resource" in stats["resource_stats"]

    def test_create_from_template(self):
        """Test creating resource from template."""
        registry = EmbeddedResourceRegistry()

        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template",
            parameter_types={"category": str, "filename": str}
        )

        registry.register_template(template)

        resource = registry.create_from_template(
            "embedded://docs/{category}/{filename}",
            category="api",
            filename="README.md"
        )

        assert resource is not None
        assert resource.uri == "embedded://docs/api/README.md"
        assert "api/README.md" in resource.name

    def test_create_from_template_validation_error(self):
        """Test creating resource from template with validation error."""
        registry = EmbeddedResourceRegistry()

        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template",
            parameter_types={"category": int}  # Expects int but gets string
        )

        registry.register_template(template)

        resource = registry.create_from_template(
            "embedded://docs/{category}/{filename}",
            category="api",  # String instead of int
            filename="README.md"
        )

        assert resource is None

    def test_create_from_template_not_found(self):
        """Test creating resource from non-existent template."""
        registry = EmbeddedResourceRegistry()

        resource = registry.create_from_template(
            "embedded://docs/{category}/{filename}",
            category="api",
            filename="README.md"
        )

        assert resource is None

    def test_cleanup_expired_cache(self):
        """Test cache cleanup functionality."""
        registry = EmbeddedResourceRegistry()

        resource = EmbeddedResource(
            uri="embedded://test/cached",
            name="Cached Resource",
            description="A cached resource",
            cache_ttl=1  # Very short TTL for testing
        )

        registry.register_embedded_resource(resource)

        # Cache some content
        resource._cache_content("cached content")
        assert resource._cached_content is not None

        # Wait for cache to expire
        import time
        time.sleep(1.1)

        # Clean up expired cache
        cleaned_count = registry.cleanup_expired_cache()
        assert cleaned_count == 1
        assert resource._cached_content is None


class TestSplunkEmbeddedResource:
    """Test the SplunkEmbeddedResource class."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock(spec=Context)
        return ctx

    def test_splunk_resource_creation(self):
        """Test Splunk resource creation."""
        class TestSplunkResource(SplunkEmbeddedResource):
            async def _generate_splunk_content(self, ctx, identity, service):
                return "splunk content"

        resource = TestSplunkResource(
            uri="embedded://splunk/data",
            name="Splunk Data Resource",
            description="A Splunk data resource",
            connection_timeout=30,
            retry_attempts=3
        )

        assert resource.connection_timeout == 30
        assert resource.retry_attempts == 3

    @pytest.mark.asyncio
    async def test_get_content_with_splunk_integration(self, mock_context):
        """Test getting content with Splunk integration."""
        class TestSplunkResource(SplunkEmbeddedResource):
            async def _generate_splunk_content(self, ctx, identity, service):
                return json.dumps({"data": "splunk content", "client_id": identity.client_id})

        # Mock the client manager and config extractor
        with patch('src.resources.embedded.get_client_manager') as mock_get_manager, \
             patch('src.resources.embedded.EnhancedConfigExtractor') as mock_extractor:

            # Mock client manager
            mock_manager = Mock()
            mock_manager.get_client_connection = AsyncMock()
            mock_get_manager.return_value = mock_manager

            # Mock config extractor
            mock_extractor_instance = Mock()
            mock_extractor_instance.extract_client_config = AsyncMock(return_value={
                "splunk_host": "localhost",
                "splunk_username": "admin"
            })
            mock_extractor.return_value = mock_extractor_instance

            # Mock identity and service
            mock_identity = Mock()
            mock_identity.client_id = "test_client"
            mock_service = Mock()
            mock_manager.get_client_connection.return_value = (mock_identity, mock_service)

            resource = TestSplunkResource(
                uri="embedded://splunk/test",
                name="Test Splunk Resource",
                description="A test Splunk resource"
            )

            content = await resource.get_content(mock_context)
            content_data = json.loads(content)

            assert content_data["data"] == "splunk content"
            assert content_data["client_id"] == "test_client"

    @pytest.mark.asyncio
    async def test_get_content_no_splunk_config(self, mock_context):
        """Test getting content without Splunk configuration."""
        class TestSplunkResource(SplunkEmbeddedResource):
            async def _generate_splunk_content(self, ctx, identity, service):
                return "splunk content"

        with patch('src.resources.embedded.EnhancedConfigExtractor') as mock_extractor:
            mock_extractor_instance = Mock()
            mock_extractor_instance.extract_client_config = AsyncMock(return_value=None)
            mock_extractor.return_value = mock_extractor_instance

            resource = TestSplunkResource(
                uri="embedded://splunk/test",
                name="Test Splunk Resource",
                description="A test Splunk resource"
            )

            content = await resource.get_content(mock_context)
            error_data = json.loads(content)

            assert "No Splunk configuration available" in error_data["error"]

    @pytest.mark.asyncio
    async def test_get_content_with_retry_logic(self, mock_context):
        """Test getting content with retry logic."""
        class TestSplunkResource(SplunkEmbeddedResource):
            async def _generate_splunk_content(self, ctx, identity, service):
                return "splunk content"

        with patch('src.resources.embedded.get_client_manager') as mock_get_manager, \
             patch('src.resources.embedded.EnhancedConfigExtractor') as mock_extractor:

            # Mock client manager that fails on first attempt
            mock_manager = Mock()
            mock_manager.get_client_connection = AsyncMock()
            mock_get_manager.return_value = mock_manager

            # Mock config extractor
            mock_extractor_instance = Mock()
            mock_extractor_instance.extract_client_config = AsyncMock(return_value={
                "splunk_host": "localhost"
            })
            mock_extractor.return_value = mock_extractor_instance

            # Mock identity and service
            mock_identity = Mock()
            mock_service = Mock()

            # First call fails, second succeeds
            mock_manager.get_client_connection.side_effect = [
                Exception("Connection failed"),
                (mock_identity, mock_service)
            ]

            resource = TestSplunkResource(
                uri="embedded://splunk/test",
                name="Test Splunk Resource",
                description="A test Splunk resource",
                retry_attempts=2
            )

            content = await resource.get_content(mock_context)
            assert content == "splunk content"

            # Should have been called twice
            assert mock_manager.get_client_connection.call_count == 2


# Integration tests
class TestEmbeddedResourcesIntegration:
    """Integration tests for embedded resources."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = Mock(spec=Context)
        return ctx

    @pytest.mark.asyncio
    async def test_full_resource_lifecycle(self, mock_context):
        """Test complete resource lifecycle."""
        # Create registry
        registry = EmbeddedResourceRegistry()

        # Create and register resource
        resource = EmbeddedResource(
            uri="embedded://test/lifecycle",
            name="Lifecycle Resource",
            description="A resource for testing lifecycle",
            embedded_content="Lifecycle content"
        )

        registry.register_embedded_resource(resource)

        # Get resource
        retrieved = registry.get_resource("embedded://test/lifecycle")
        assert retrieved == resource

        # Get content
        content = await retrieved.get_content(mock_context)
        assert content == "Lifecycle content"

        # Check statistics
        stats = registry.get_statistics()
        assert stats["total_resources"] == 1
        assert stats["total_accesses"] == 1

    @pytest.mark.asyncio
    async def test_template_resource_creation_and_usage(self, mock_context):
        """Test template resource creation and usage."""
        registry = EmbeddedResourceRegistry()

        # Create template
        template = ResourceTemplate(
            uri_template="embedded://docs/{category}/{filename}",
            name="Documentation Template",
            description="A documentation template",
            parameter_types={"category": str, "filename": str}
        )

        registry.register_template(template)

        # Create resource from template
        resource = registry.create_from_template(
            "embedded://docs/{category}/{filename}",
            category="api",
            filename="README.md"
        )

        assert resource is not None
        assert resource.uri == "embedded://docs/api/README.md"

        # Register the created resource
        registry.register_embedded_resource(resource)

        # Get the resource
        retrieved = registry.get_resource("embedded://docs/api/README.md")
        assert retrieved == resource

        # Test getting content from the resource
        if retrieved:
            content = await retrieved.get_content(mock_context)
            assert content is not None

    @pytest.mark.asyncio
    async def test_file_resource_with_watching(self, mock_context):
        """Test file resource with file watching."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Initial content")
            temp_path = f.name

        try:
            registry = EmbeddedResourceRegistry()

            # Create file resource
            resource = FileEmbeddedResource(
                uri="embedded://file/watched",
                name="Watched File Resource",
                description="A watched file resource",
                file_path=temp_path,
                watch_file=True
            )

            registry.register_embedded_resource(resource)

            # Get initial content
            content1 = await resource.get_content(mock_context)
            assert content1 == "Initial content"

            # Update file
            with open(temp_path, 'w') as f:
                f.write("Updated content")

            # Get updated content
            content2 = await resource.get_content(mock_context)
            assert content2 == "Updated content"

        finally:
            # Cleanup
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_error_handling_across_resources(self, mock_context):
        """Test error handling across different resource types."""
        registry = EmbeddedResourceRegistry()

        # Test embedded resource with invalid content
        resource1 = EmbeddedResource(
            uri="embedded://test/invalid-json",
            name="Invalid JSON Resource",
            description="A resource with invalid JSON",
            embedded_content='{"invalid": json',  # Invalid JSON
            mime_type="application/json",
            validate_content=True
        )

        registry.register_embedded_resource(resource1)

        # Test file resource with non-existent file
        resource2 = FileEmbeddedResource(
            uri="embedded://file/missing",
            name="Missing File Resource",
            description="A resource for a missing file",
            file_path="/nonexistent/file.txt"
        )

        registry.register_embedded_resource(resource2)

        # Get content from both resources
        content1 = await resource1.get_content(mock_context)
        content2 = await resource2.get_content(mock_context)

        # Both should return error responses
        error1 = json.loads(content1)
        error2 = json.loads(content2)

        assert error1["type"] == "error"
        assert error2["type"] == "error"
        assert "error" in error1
        assert "error" in error2

        # Check statistics
        stats = registry.get_statistics()
        assert stats["total_resources"] == 2
        assert stats["total_accesses"] == 2
