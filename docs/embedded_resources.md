# Enhanced Embedded Resources for MCP

## Overview

Embedded Resources are a powerful enhancement to the Model Context Protocol (MCP) that allows servers to provide read-only data with embedded content, dynamic generation, and advanced caching capabilities. This implementation follows MCP patterns and provides enhanced functionality for resource management.

## What Are Embedded Resources?

Embedded Resources extend the standard MCP resource concept by providing:

- **Embedded Content**: Resources can contain their content directly within the resource metadata
- **Dynamic Generation**: Content can be generated on-demand based on parameters or context
- **Advanced Caching**: Intelligent caching with ETag support and cache invalidation
- **Content Validation**: Automatic validation of content based on MIME type
- **Template Support**: Parameterized resources with type validation
- **Performance Monitoring**: Access statistics and performance tracking

## Key Features

### 1. Content Embedding

Resources can embed their content directly, eliminating the need for external file access:

```python
# Text content embedding
resource = EmbeddedResource(
    uri="embedded://docs/guide",
    name="User Guide",
    description="Complete user guide",
    embedded_content="# User Guide\n\nThis is the complete guide...",
    mime_type="text/markdown"
)

# Binary content embedding
resource = EmbeddedResource(
    uri="embedded://images/logo",
    name="Company Logo",
    description="Company logo image",
    embedded_content=binary_image_data,
    mime_type="image/png"
)
```

### 2. File-Based Resources

Enhanced file resources with automatic MIME detection and file watching:

```python
resource = FileEmbeddedResource(
    uri="embedded://docs/README.md",
    name="README Documentation",
    description="Project README file",
    file_path="README.md",
    mime_type="text/markdown",
    encoding="utf-8",
    watch_file=True  # Automatically detect file changes
)
```

### 3. Template-Based Resources

Dynamic resources with parameter validation and type conversion:

```python
template = ResourceTemplate(
    uri_template="embedded://docs/{doc_type}/{filename}",
    name="Documentation Template",
    description="Template for accessing documentation files",
    mime_type="text/markdown",
    parameter_types={"doc_type": str, "filename": str},
    parameter_defaults={"doc_type": "general"}
)

# Usage
expanded_uri = template.expand(doc_type="api", filename="resources.md")
# Result: "embedded://docs/api/resources.md"
```

### 4. Splunk Integration

Enhanced Splunk resources with retry logic and connection pooling:

```python
class SplunkDataResource(SplunkEmbeddedResource):
    async def _generate_splunk_content(self, ctx: Context, identity, service) -> str:
        # Fetch data from Splunk
        search_results = await service.search("index=main | head 100")
        return json.dumps(search_results)
```

## Implementation Classes

### EmbeddedResource (Base Class)

The base class for all embedded resources with enhanced functionality:

```python
class EmbeddedResource(BaseResource):
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
```

**Features:**
- Content validation based on MIME type
- ETag generation for HTTP caching
- Intelligent caching with TTL
- Error handling and logging
- Performance monitoring

### FileEmbeddedResource

Enhanced file-based resources with file watching and encoding support:

```python
class FileEmbeddedResource(EmbeddedResource):
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
```

**Features:**
- Automatic MIME type detection
- File change detection
- Multiple encoding support
- Binary file handling
- Permission error handling

### TemplateEmbeddedResource

Dynamic resources with parameter validation:

```python
class TemplateEmbeddedResource(EmbeddedResource):
    def __init__(
        self, 
        uri_template: str, 
        name: str, 
        description: str, 
        mime_type: str = "text/plain",
        parameter_validators: Optional[Dict[str, Callable]] = None
    ):
```

**Features:**
- URI parameter extraction
- Parameter validation
- Type conversion
- Default parameter values

### SplunkEmbeddedResource

Splunk-specific resources with enhanced connection handling:

```python
class SplunkEmbeddedResource(EmbeddedResource):
    def __init__(
        self, 
        uri: str, 
        name: str, 
        description: str, 
        mime_type: str = "application/json",
        connection_timeout: int = 30,
        retry_attempts: int = 3
    ):
```

**Features:**
- Client isolation
- Retry logic with exponential backoff
- Connection pooling
- Error recovery

## Registry System

### EmbeddedResourceRegistry

Centralized registry for managing embedded resources:

```python
registry = EmbeddedResourceRegistry()

# Register resources
registry.register_embedded_resource(resource)
registry.register_template(template)

# Access resources
resource = registry.get_resource("embedded://docs/README.md")

# Get statistics
stats = registry.get_statistics()
```

**Features:**
- Resource registration and discovery
- Template management
- Access statistics
- Cache cleanup
- Performance monitoring

## Content Validation

### ContentValidator

Automatic content validation based on MIME type:

```python
# JSON validation
result = ContentValidator.validate_json(json_content)

# Markdown validation
result = ContentValidator.validate_markdown(markdown_content)

# Text validation
result = ContentValidator.validate_text(text_content)
```

**Validation Features:**
- JSON syntax validation
- Markdown structure checking
- Content size limits
- Encoding validation

## Usage Patterns

### 1. Static Content Resources

```python
# Create a static documentation resource
docs_resource = EmbeddedResource(
    uri="embedded://docs/user-guide",
    name="User Guide",
    description="Complete user guide for the application",
    embedded_content="# User Guide\n\n## Getting Started\n\n...",
    mime_type="text/markdown",
    cache_ttl=3600  # Cache for 1 hour
)
```

### 2. File-Based Resources

```python
# Create a file-based resource with watching
config_resource = FileEmbeddedResource(
    uri="embedded://config/settings.json",
    name="Application Settings",
    description="Current application configuration",
    file_path="config/settings.json",
    mime_type="application/json",
    watch_file=True  # Automatically detect changes
)
```

### 3. Template Resources

```python
# Create a template for dynamic documentation
doc_template = ResourceTemplate(
    uri_template="embedded://docs/{category}/{filename}",
    name="Documentation Template",
    description="Template for accessing documentation by category",
    mime_type="text/markdown",
    parameter_types={"category": str, "filename": str},
    parameter_defaults={"category": "general"}
)

# Use the template
resource = registry.create_from_template(
    "embedded://docs/{category}/{filename}",
    category="api",
    filename="authentication.md"
)
```

### 4. Splunk Data Resources

```python
class SplunkMetricsResource(SplunkEmbeddedResource):
    async def _generate_splunk_content(self, ctx: Context, identity, service) -> str:
        # Generate system metrics from Splunk
        search_query = "index=system_metrics | stats avg(cpu) as avg_cpu, avg(memory) as avg_memory"
        results = await service.search(search_query)
        
        return json.dumps({
            "timestamp": datetime.now().isoformat(),
            "metrics": results,
            "source": "splunk"
        })
```

## Content Types

### Text Content

```python
# Plain text
resource = EmbeddedResource(
    uri="embedded://text/status",
    embedded_content="System is operational",
    mime_type="text/plain"
)

# Markdown
resource = EmbeddedResource(
    uri="embedded://docs/guide",
    embedded_content="# Guide\n\nThis is a **markdown** guide.",
    mime_type="text/markdown"
)

# JSON
resource = EmbeddedResource(
    uri="embedded://data/config",
    embedded_content='{"version": "1.0", "features": ["a", "b"]}',
    mime_type="application/json"
)
```

### Binary Content

```python
# Image
with open("logo.png", "rb") as f:
    image_data = f.read()

resource = EmbeddedResource(
    uri="embedded://images/logo",
    embedded_content=image_data,
    mime_type="image/png"
)
```

## Caching and Performance

### Cache Management

```python
# Configure caching
resource = EmbeddedResource(
    uri="embedded://data/expensive",
    cache_ttl=600,  # Cache for 10 minutes
    etag_enabled=True
)

# Manual cache cleanup
registry.cleanup_expired_cache()
```

### Performance Monitoring

```python
# Get access statistics
stats = registry.get_statistics()
print(f"Total accesses: {stats['total_accesses']}")
print(f"Average response time: {stats['resource_stats']['uri']['average_response_time']}")
```

## Error Handling

### Graceful Error Handling

```python
# Resources automatically handle errors
try:
    content = await resource.get_content(ctx)
except Exception as e:
    # Error is logged and returned as JSON error response
    error_response = resource._create_error_response(str(e))
```

### Validation Errors

```python
# Content validation errors
if not validation_result.is_valid:
    logger.warning(f"Content validation failed: {validation_result.errors}")
```

## Integration with MCP

### Registration with Main Registry

```python
# Automatic registration with main MCP registry
def register_embedded_resources():
    # Register with embedded registry
    embedded_resource_registry.register_embedded_resource(resource)
    
    # Register with main MCP registry
    from ..core.registry import resource_registry
    resource_registry.register(type(resource), resource.get_metadata())
```

### Discovery Integration

```python
# Resources are automatically discovered
from ..core.discovery import discover_resources
discover_resources()  # Discovers embedded resources
```

## Best Practices

### 1. Resource Naming

```python
# Use consistent URI schemes
"embedded://docs/{category}/{filename}"
"embedded://config/{config_type}"
"embedded://data/{dataset}/{format}"
```

### 2. Content Validation

```python
# Always enable content validation for user-provided content
resource = EmbeddedResource(
    validate_content=True,
    mime_type="application/json"
)
```

### 3. Caching Strategy

```python
# Use appropriate cache TTL based on content volatility
static_content = EmbeddedResource(cache_ttl=3600)  # 1 hour
dynamic_content = EmbeddedResource(cache_ttl=60)   # 1 minute
real_time_data = EmbeddedResource(cache_ttl=0)     # No cache
```

### 4. Error Handling

```python
# Provide meaningful error messages
def _create_error_response(self, error_message: str) -> str:
    return json.dumps({
        "error": error_message,
        "uri": self.uri,
        "type": "error",
        "timestamp": datetime.now().isoformat()
    })
```

### 5. Performance Monitoring

```python
# Monitor resource usage
stats = registry.get_statistics()
if stats['total_errors'] > 0:
    logger.warning(f"High error rate: {stats['total_errors']} errors")
```

## Examples

### Complete Example: Documentation System

```python
# Create documentation resources
docs_registry = EmbeddedResourceRegistry()

# Static documentation
readme_resource = EmbeddedResource(
    uri="embedded://docs/README",
    name="README",
    description="Project README",
    embedded_content="# Project README\n\nWelcome to our project...",
    mime_type="text/markdown"
)

# File-based documentation
api_docs = FileEmbeddedResource(
    uri="embedded://docs/api",
    name="API Documentation",
    description="API documentation from files",
    file_path="docs/api.md",
    mime_type="text/markdown",
    watch_file=True
)

# Template for dynamic docs
doc_template = ResourceTemplate(
    uri_template="embedded://docs/{category}/{filename}",
    name="Documentation Template",
    description="Dynamic documentation access",
    mime_type="text/markdown"
)

# Register everything
docs_registry.register_embedded_resource(readme_resource)
docs_registry.register_embedded_resource(api_docs)
docs_registry.register_template(doc_template)

# Use the system
content = await docs_registry.get_resource("embedded://docs/README").get_content(ctx)
```

### Splunk Integration Example

```python
class SplunkLogsResource(SplunkEmbeddedResource):
    async def _generate_splunk_content(self, ctx: Context, identity, service) -> str:
        # Get recent logs
        search_query = "index=main | head 100 | table _time, source, message"
        results = await service.search(search_query)
        
        return json.dumps({
            "logs": results,
            "timestamp": datetime.now().isoformat(),
            "client_id": identity.client_id
        })

# Register Splunk resource
splunk_logs = SplunkLogsResource(
    uri="embedded://splunk/logs/recent",
    name="Recent Logs",
    description="Recent Splunk logs"
)
```

## Conclusion

Enhanced Embedded Resources provide a powerful way to extend MCP servers with rich, dynamic content capabilities. By following the patterns and best practices outlined in this documentation, you can create robust, performant, and maintainable embedded resource systems that enhance your AI applications' capabilities.

The implementation provides:
- **Flexibility**: Support for various content types and sources
- **Performance**: Intelligent caching and optimization
- **Reliability**: Comprehensive error handling and validation
- **Monitoring**: Built-in statistics and performance tracking
- **Integration**: Seamless integration with existing MCP systems

For more information, refer to the MCP specification and the FastMCP documentation.