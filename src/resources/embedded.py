"""
Enhanced Embedded Resources for MCP Server.

Provides enhanced resource functionality including embedded content,
resource templates, and improved discovery mechanisms following MCP patterns.
"""

import json
import logging
import base64
import hashlib
import time
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastmcp import Context

from ..core.base import BaseResource, ResourceMetadata
from ..core.client_identity import get_client_manager

logger = logging.getLogger(__name__)


@dataclass
class ContentValidationResult:
    """Result of content validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ContentValidator:
    """Validator for embedded resource content."""
    
    @staticmethod
    def validate_json(content: str) -> ContentValidationResult:
        """Validate JSON content."""
        errors = []
        warnings = []
        
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
        
        return ContentValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_markdown(content: str) -> ContentValidationResult:
        """Validate Markdown content."""
        errors = []
        warnings = []
        
        # Basic markdown validation
        if not content.strip():
            errors.append("Empty content")
        
        # Check for common markdown issues
        if content.count('#') > 10:
            warnings.append("Many headers detected - consider structure")
        
        return ContentValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @staticmethod
    def validate_text(content: str) -> ContentValidationResult:
        """Validate text content."""
        errors = []
        warnings = []
        
        if not content.strip():
            errors.append("Empty content")
        
        if len(content) > 1000000:  # 1MB
            warnings.append("Large content detected")
        
        return ContentValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class EmbeddedResource(BaseResource):
    """
    Enhanced base class for embedded resources that can contain both text and binary content.
    
    Embedded resources provide enhanced functionality including:
    - Embedded content within resource metadata
    - Binary data support with base64 encoding
    - MIME type detection and validation
    - Content caching and optimization
    - Content validation
    - ETag support for caching
    """

    def __init__(
        self, 
        uri: str, 
        name: str, 
        description: str, 
        mime_type: str = "text/plain",
        embedded_content: Optional[Union[str, bytes]] = None,
        cache_ttl: int = 300,
        validate_content: bool = True,
        etag_enabled: bool = True
    ):
        super().__init__(uri, name, description, mime_type)
        self.embedded_content = embedded_content
        self.cache_ttl = cache_ttl
        self.validate_content = validate_content
        self.etag_enabled = etag_enabled
        self._cached_content = None
        self._cache_timestamp = 0
        self._etag = None
        self._content_hash = None

    async def get_content(self, ctx: Context) -> str:
        """
        Get resource content with embedded content support.
        
        Args:
            ctx: MCP context
            
        Returns:
            Resource content as string (JSON for binary data)
        """
        try:
            # Check cache first
            if self._is_cache_valid():
                return self._cached_content

            # Get content from embedded data or generate dynamically
            if self.embedded_content is not None:
                content = await self._process_embedded_content()
            else:
                content = await self._generate_dynamic_content(ctx)

            # Validate content if enabled
            if self.validate_content:
                validation_result = self._validate_content(content)
                if not validation_result.is_valid:
                    logger.warning(f"Content validation failed for {self.uri}: {validation_result.errors}")
                if validation_result.warnings:
                    logger.info(f"Content validation warnings for {self.uri}: {validation_result.warnings}")

            # Cache the result
            self._cache_content(content)
            
            return content

        except Exception as e:
            logger.error(f"Error getting content for {self.uri}: {e}")
            return self._create_error_response(str(e))

    async def _process_embedded_content(self) -> str:
        """Process embedded content and return appropriate format."""
        if isinstance(self.embedded_content, str):
            # Text content
            return self.embedded_content
        elif isinstance(self.embedded_content, bytes):
            # Binary content - encode as base64 and return as JSON
            encoded = base64.b64encode(self.embedded_content).decode('utf-8')
            return json.dumps({
                "type": "binary",
                "mime_type": self.mime_type,
                "data": encoded,
                "size": len(self.embedded_content),
                "etag": self._generate_etag() if self.etag_enabled else None
            })
        else:
            raise ValueError(f"Unsupported embedded content type: {type(self.embedded_content)}")

    async def _generate_dynamic_content(self, ctx: Context) -> str:
        """Generate dynamic content - override in subclasses."""
        raise NotImplementedError("Subclasses must implement _generate_dynamic_content")

    def _is_cache_valid(self) -> bool:
        """Check if cached content is still valid."""
        if self._cached_content is None:
            return False
        
        return (time.time() - self._cache_timestamp) < self.cache_ttl

    def _cache_content(self, content: str) -> None:
        """Cache content with timestamp."""
        self._cached_content = content
        self._cache_timestamp = time.time()
        self._content_hash = self._generate_content_hash(content)

    def _generate_content_hash(self, content: str) -> str:
        """Generate content hash for ETag."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _generate_etag(self) -> Optional[str]:
        """Generate ETag for the resource."""
        if self._content_hash:
            return f'"{self._content_hash}"'
        return None

    def _validate_content(self, content: str) -> ContentValidationResult:
        """Validate content based on MIME type."""
        if self.mime_type == "application/json":
            return ContentValidator.validate_json(content)
        elif self.mime_type in ["text/markdown", "text/x-markdown"]:
            return ContentValidator.validate_markdown(content)
        else:
            return ContentValidator.validate_text(content)

    def _create_error_response(self, error_message: str) -> str:
        """Create error response in consistent format."""
        return json.dumps({
            "error": error_message,
            "uri": self.uri,
            "type": "error",
            "timestamp": datetime.now().isoformat()
        })

    def get_metadata(self) -> ResourceMetadata:
        """Get enhanced metadata for this resource."""
        return ResourceMetadata(
            uri=self.uri,
            name=self.name,
            description=self.description,
            mime_type=self.mime_type,
            category="embedded",
            tags=["embedded", "content", "cached" if self.cache_ttl > 0 else "dynamic"]
        )


class FileEmbeddedResource(EmbeddedResource):
    """
    Enhanced embedded resource that loads content from files.
    
    Supports both text and binary files with automatic MIME type detection,
    file watching, and content validation.
    """

    def __init__(
        self, 
        uri: str, 
        name: str, 
        description: str, 
        file_path: str,
        mime_type: Optional[str] = None,
        encoding: str = "utf-8",
        watch_file: bool = False
    ):
        # Auto-detect MIME type if not provided
        if mime_type is None:
            detected_mime_type, _ = mimetypes.guess_type(file_path)
            mime_type = detected_mime_type or "application/octet-stream"

        super().__init__(uri, name, description, mime_type)
        self.file_path = Path(file_path)
        self.encoding = encoding
        self.watch_file = watch_file
        self._file_mtime = None

    async def get_content(self, ctx: Context) -> str:
        """Get content from file with enhanced error handling."""
        try:
            if not self.file_path.exists():
                return self._create_error_response(f"File not found: {self.file_path}")

            # Check if file has changed (for file watching)
            if self.watch_file and self._file_mtime:
                current_mtime = self.file_path.stat().st_mtime
                if current_mtime > self._file_mtime:
                    # File changed, invalidate cache
                    self._cached_content = None
                    self._cache_timestamp = 0

            # Read file content
            if self.mime_type.startswith('text/'):
                # Text file
                content = self.file_path.read_text(encoding=self.encoding)
                self._file_mtime = self.file_path.stat().st_mtime
                return content
            else:
                # Binary file
                binary_content = self.file_path.read_bytes()
                encoded = base64.b64encode(binary_content).decode('utf-8')
                self._file_mtime = self.file_path.stat().st_mtime
                return json.dumps({
                    "type": "binary",
                    "mime_type": self.mime_type,
                    "data": encoded,
                    "size": len(binary_content),
                    "filename": self.file_path.name,
                    "etag": self._generate_etag() if self.etag_enabled else None
                })

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading file {self.file_path}: {e}")
            return self._create_error_response(f"Encoding error: {str(e)}")
        except PermissionError as e:
            logger.error(f"Permission error reading file {self.file_path}: {e}")
            return self._create_error_response(f"Permission denied: {str(e)}")
        except Exception as e:
            logger.error(f"Error reading file {self.file_path}: {e}")
            return self._create_error_response(f"Error reading file: {str(e)}")


class TemplateEmbeddedResource(EmbeddedResource):
    """
    Enhanced template-based embedded resource that supports URI parameters.
    
    Allows dynamic resource generation based on URI parameters with
    validation and type conversion.
    """

    def __init__(
        self, 
        uri_template: str, 
        name: str, 
        description: str, 
        mime_type: str = "text/plain",
        parameter_validators: Optional[Dict[str, Callable]] = None
    ):
        super().__init__(uri_template, name, description, mime_type)
        self.uri_template = uri_template
        self.parameter_validators = parameter_validators or {}

    async def get_content(self, ctx: Context, uri: str = None) -> str:
        """
        Get content with URI parameter extraction and validation.
        
        Args:
            ctx: MCP context
            uri: Specific URI (optional)
            
        Returns:
            Generated content based on URI parameters
        """
        try:
            # Extract parameters from URI
            params = self._extract_uri_parameters(uri or self.uri)
            
            # Validate parameters
            validation_errors = self._validate_parameters(params)
            if validation_errors:
                return self._create_error_response(f"Parameter validation failed: {validation_errors}")
            
            # Generate content based on parameters
            content = await self._generate_content_from_params(ctx, params)
            
            return content

        except Exception as e:
            logger.error(f"Error generating template content: {e}")
            return self._create_error_response(f"Template error: {str(e)}")

    def _extract_uri_parameters(self, uri: str) -> Dict[str, str]:
        """Extract parameters from URI based on template with enhanced parsing."""
        params = {}
        
        # Enhanced parameter extraction
        if '{' in self.uri_template and '}' in self.uri_template:
            # Extract parameter names from template
            param_names = re.findall(r'\{([^}]+)\}', self.uri_template)
            
            # Create regex pattern for matching
            pattern = self.uri_template
            for param_name in param_names:
                pattern = pattern.replace(f'{{{param_name}}}', f'(?P<{param_name}>[^/]+)')
            
            # Match URI against pattern
            match = re.match(pattern, uri)
            if match:
                params = match.groupdict()
        
        return params

    def _validate_parameters(self, params: Dict[str, str]) -> List[str]:
        """Validate extracted parameters."""
        errors = []
        
        for param_name, validator in self.parameter_validators.items():
            if param_name in params:
                try:
                    validator(params[param_name])
                except Exception as e:
                    errors.append(f"Parameter '{param_name}' validation failed: {e}")
        
        return errors

    @abstractmethod
    async def _generate_content_from_params(self, ctx: Context, params: Dict[str, str]) -> str:
        """Generate content based on URI parameters."""
        pass


class SplunkEmbeddedResource(EmbeddedResource):
    """
    Enhanced embedded resource with Splunk integration.
    
    Provides enhanced Splunk-specific resource functionality with client isolation,
    connection pooling, and error recovery.
    """

    def __init__(
        self, 
        uri: str, 
        name: str, 
        description: str, 
        mime_type: str = "application/json",
        connection_timeout: int = 30,
        retry_attempts: int = 3
    ):
        super().__init__(uri, name, description, mime_type)
        self.client_manager = get_client_manager()
        self.connection_timeout = connection_timeout
        self.retry_attempts = retry_attempts

    async def get_content(self, ctx: Context) -> str:
        """Get content with enhanced Splunk client isolation and retry logic."""
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                # Extract client configuration
                from ..core.enhanced_config_extractor import EnhancedConfigExtractor
                config_extractor = EnhancedConfigExtractor()
                client_config = await config_extractor.extract_client_config(ctx)
                
                if not client_config:
                    return self._create_error_response("No Splunk configuration available")

                # Get client connection
                identity, service = await self.client_manager.get_client_connection(ctx, client_config)
                
                # Generate Splunk-specific content
                content = await self._generate_splunk_content(ctx, identity, service)
                
                return content

            except Exception as e:
                last_error = e
                logger.warning(f"Splunk connection attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"All Splunk connection attempts failed for {self.uri}")
        return self._create_error_response(f"Splunk error after {self.retry_attempts} attempts: {str(last_error)}")

    @abstractmethod
    async def _generate_splunk_content(self, ctx: Context, identity, service) -> str:
        """Generate content using Splunk service."""
        pass


class ResourceTemplate:
    """
    Enhanced template for creating dynamic resources.
    
    Provides URI template functionality following RFC 6570 with
    parameter validation and type conversion.
    """

    def __init__(
        self, 
        uri_template: str, 
        name: str, 
        description: str, 
        mime_type: str = "text/plain",
        parameter_types: Optional[Dict[str, type]] = None,
        parameter_defaults: Optional[Dict[str, Any]] = None
    ):
        self.uri_template = uri_template
        self.name = name
        self.description = description
        self.mime_type = mime_type
        self.parameter_types = parameter_types or {}
        self.parameter_defaults = parameter_defaults or {}

    def expand(self, **params) -> str:
        """Expand template with parameters and type conversion."""
        try:
            # Apply type conversions
            converted_params = {}
            for key, value in params.items():
                if key in self.parameter_types:
                    try:
                        converted_params[key] = self.parameter_types[key](value)
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"Parameter '{key}' type conversion failed: {e}")
                else:
                    converted_params[key] = value
            
            # Apply defaults for missing parameters
            for key, default_value in self.parameter_defaults.items():
                if key not in converted_params:
                    converted_params[key] = default_value
            
            return self.uri_template.format(**converted_params)
        except KeyError as e:
            raise ValueError(f"Missing required parameter: {e}")
        except Exception as e:
            raise ValueError(f"Template expansion error: {e}")

    def get_metadata(self) -> ResourceMetadata:
        """Get enhanced metadata for this template."""
        return ResourceMetadata(
            uri=self.uri_template,
            name=self.name,
            description=self.description,
            mime_type=self.mime_type,
            category="template",
            tags=["template", "dynamic", "parameterized"]
        )

    def validate_parameters(self, **params) -> List[str]:
        """Validate parameters against template requirements."""
        errors = []
        
        # Extract required parameters from template
        required_params = re.findall(r'\{([^}]+)\}', self.uri_template)
        
        # Check for missing required parameters
        for param in required_params:
            if param not in params and param not in self.parameter_defaults:
                errors.append(f"Missing required parameter: {param}")
        
        # Validate parameter types
        for param, value in params.items():
            if param in self.parameter_types:
                try:
                    self.parameter_types[param](value)
                except (ValueError, TypeError) as e:
                    errors.append(f"Parameter '{param}' type validation failed: {e}")
        
        return errors


class EmbeddedResourceRegistry:
    """
    Enhanced registry for embedded resources with improved discovery.
    
    Provides centralized management of embedded resources with
    template support, automatic discovery, and performance monitoring.
    """

    def __init__(self):
        self._resources: Dict[str, EmbeddedResource] = {}
        self._templates: Dict[str, ResourceTemplate] = {}
        self._metadata: Dict[str, ResourceMetadata] = {}
        self._access_stats: Dict[str, Dict[str, Any]] = {}

    def register_embedded_resource(self, resource: EmbeddedResource) -> None:
        """Register an embedded resource with statistics tracking."""
        self._resources[resource.uri] = resource
        self._metadata[resource.uri] = resource.get_metadata()
        self._access_stats[resource.uri] = {
            "access_count": 0,
            "last_accessed": None,
            "average_response_time": 0.0,
            "error_count": 0
        }
        logger.info(f"Registered embedded resource: {resource.uri}")

    def register_template(self, template: ResourceTemplate) -> None:
        """Register a resource template with validation."""
        # Validate template parameters
        validation_errors = template.validate_parameters()
        if validation_errors:
            logger.warning(f"Template validation warnings: {validation_errors}")
        
        self._templates[template.uri_template] = template
        self._metadata[template.uri_template] = template.get_metadata()
        logger.info(f"Registered resource template: {template.uri_template}")

    def get_resource(self, uri: str) -> Optional[EmbeddedResource]:
        """Get embedded resource by URI with access tracking."""
        resource = self._resources.get(uri)
        if resource:
            # Update access statistics
            stats = self._access_stats[uri]
            stats["access_count"] += 1
            stats["last_accessed"] = datetime.now()
        
        return resource

    def get_template(self, uri_template: str) -> Optional[ResourceTemplate]:
        """Get resource template by URI template."""
        return self._templates.get(uri_template)

    def list_resources(self) -> List[ResourceMetadata]:
        """List all registered embedded resources with statistics."""
        return list(self._metadata.values())

    def list_templates(self) -> List[ResourceTemplate]:
        """List all registered templates."""
        return list(self._templates.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        total_resources = len(self._resources)
        total_templates = len(self._templates)
        total_accesses = sum(stats["access_count"] for stats in self._access_stats.values())
        total_errors = sum(stats["error_count"] for stats in self._access_stats.values())
        
        return {
            "total_resources": total_resources,
            "total_templates": total_templates,
            "total_accesses": total_accesses,
            "total_errors": total_errors,
            "resource_stats": self._access_stats
        }

    def create_from_template(self, template_uri: str, **params) -> Optional[EmbeddedResource]:
        """Create resource instance from template with validation."""
        template = self.get_template(template_uri)
        if not template:
            return None
        
        try:
            # Validate parameters
            validation_errors = template.validate_parameters(**params)
            if validation_errors:
                logger.error(f"Template parameter validation failed: {validation_errors}")
                return None
            
            expanded_uri = template.expand(**params)
            
            # Create a new resource instance with the expanded URI
            return EmbeddedResource(
                uri=expanded_uri,
                name=f"{template.name} ({expanded_uri})",
                description=template.description,
                mime_type=template.mime_type
            )
        except Exception as e:
            logger.error(f"Error creating resource from template: {e}")
            return None

    def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries and return count of cleaned items."""
        cleaned_count = 0
        current_time = time.time()
        
        for resource in self._resources.values():
            if hasattr(resource, '_cache_timestamp') and resource._cache_timestamp > 0:
                if current_time - resource._cache_timestamp > resource.cache_ttl:
                    resource._cached_content = None
                    resource._cache_timestamp = 0
                    cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired cache entries")
        
        return cleaned_count


# Global registry instance
embedded_resource_registry = EmbeddedResourceRegistry()


def register_embedded_resources():
    """Register all embedded resources with the registry."""
    try:
        # Register file-based embedded resources
        _register_file_resources()
        
        # Register template-based resources
        _register_template_resources()
        
        # Register Splunk embedded resources
        _register_splunk_embedded_resources()
        
        # Register with the main resource registry
        _register_with_main_registry()
        
        logger.info("Successfully registered embedded resources")
        
    except Exception as e:
        logger.error(f"Error registering embedded resources: {e}")


def _register_file_resources():
    """Register file-based embedded resources."""
    # Enhanced file resources with better error handling
    file_resources = [
        {
            "uri": "embedded://docs/README.md",
            "name": "README Documentation",
            "description": "Project README file with enhanced formatting",
            "file_path": "README.md",
            "mime_type": "text/markdown",
            "encoding": "utf-8",
            "watch_file": True
        },
        {
            "uri": "embedded://docs/CHANGELOG.md",
            "name": "Changelog",
            "description": "Project changelog and version history",
            "file_path": "CHANGELOG.md",
            "mime_type": "text/markdown",
            "encoding": "utf-8",
            "watch_file": True
        },
        {
            "uri": "embedded://config/settings.json",
            "name": "Application Settings",
            "description": "Application configuration settings",
            "file_path": "config/settings.json",
            "mime_type": "application/json",
            "encoding": "utf-8",
            "watch_file": False
        }
    ]
    
    for resource_config in file_resources:
        try:
            resource = FileEmbeddedResource(
                uri=resource_config["uri"],
                name=resource_config["name"],
                description=resource_config["description"],
                file_path=resource_config["file_path"],
                mime_type=resource_config.get("mime_type"),
                encoding=resource_config.get("encoding", "utf-8"),
                watch_file=resource_config.get("watch_file", False)
            )
            embedded_resource_registry.register_embedded_resource(resource)
        except Exception as e:
            logger.warning(f"Could not register file resource {resource_config['uri']}: {e}")


def _register_template_resources():
    """Register enhanced template-based resources."""
    templates = [
        ResourceTemplate(
            uri_template="embedded://docs/{doc_type}/{filename}",
            name="Documentation Template",
            description="Template for accessing documentation files with type validation",
            mime_type="text/markdown",
            parameter_types={"doc_type": str, "filename": str},
            parameter_defaults={"doc_type": "general"}
        ),
        ResourceTemplate(
            uri_template="embedded://config/{config_type}",
            name="Configuration Template",
            description="Template for accessing configuration files",
            mime_type="text/plain",
            parameter_types={"config_type": str}
        ),
        ResourceTemplate(
            uri_template="embedded://data/{dataset}/{format}",
            name="Dataset Template",
            description="Template for accessing datasets in different formats",
            mime_type="application/json",
            parameter_types={"dataset": str, "format": str},
            parameter_defaults={"format": "json"}
        )
    ]
    
    for template in templates:
        embedded_resource_registry.register_template(template)


def _register_splunk_embedded_resources():
    """Register Splunk-specific embedded resources."""
    # This would register Splunk-specific embedded resources
    # Implementation depends on your specific Splunk integration needs
    logger.info("Splunk embedded resources registration placeholder")


def _register_with_main_registry():
    """Register embedded resources with the main resource registry."""
    try:
        from ..core.registry import resource_registry
        
        # Register all embedded resources with the main registry
        for uri, resource in embedded_resource_registry._resources.items():
            metadata = resource.get_metadata()
            resource_registry.register(type(resource), metadata)
        
        logger.info("Registered embedded resources with main registry")
        
    except Exception as e:
        logger.error(f"Error registering with main registry: {e}")


# Import asyncio for the retry logic
import asyncio