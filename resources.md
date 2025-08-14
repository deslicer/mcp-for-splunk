# MCP Server Resources Documentation

## Overview

Resources in the Model Context Protocol (MCP) provide read-only access to data sources that LLM clients can request and use as context. Resources are essentially "GET-like" endpoints that expose information to AI assistants, allowing them to retrieve and understand relevant data from your server.

This document provides a comprehensive guide to implementing and using resources in your MCP server, with specific focus on patterns and best practices for building robust, scalable resource systems.

## What Are Resources?

Resources represent data or files that an MCP client can read. They are:

- **Read-only**: Resources provide data but don't perform actions
- **URI-based**: Each resource has a unique identifier (URI)
- **Contextual**: They provide information that helps LLMs understand and respond to user queries
- **Lazy-loaded**: Content is only generated when specifically requested

Resources can be:
- Static files (documents, configurations)
- Dynamic data (database queries, API responses)
- Computed information (reports, analytics)
- Real-time data (system status, metrics)

## Resource Types

### 1. Static Resources
Fixed content that doesn't change between requests:
```python
@mcp.resource("config://app-settings")
def get_app_settings() -> dict:
    """Application configuration settings."""
    return {
        "version": "1.0.0",
        "environment": "production",
        "features": ["search", "analytics"]
    }
```

### 2. Dynamic Resources
Content that changes based on current state or time:
```python
@mcp.resource("status://system")
async def get_system_status() -> dict:
    """Current system status and metrics."""
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_usage": get_cpu_usage(),
        "memory_usage": get_memory_usage(),
        "active_connections": get_connection_count()
    }
```

### 3. Resource Templates
Parameterized resources that generate content based on URI parameters:
```python
@mcp.resource("users://{user_id}/profile")
async def get_user_profile(user_id: str) -> dict:
    """User profile information for a specific user."""
    user = await fetch_user_from_db(user_id)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "last_login": user.last_login.isoformat()
    }
```

## Implementation Patterns

### Basic Resource Definition

```python
from fastmcp import FastMCP

mcp = FastMCP(name="DataServer")

@mcp.resource("data://config")
def get_config() -> dict:
    """Provides application configuration as JSON."""
    return {
        "theme": "dark",
        "version": "1.2.0",
        "features": ["tools", "resources"]
    }
```

### Resource with Metadata

```python
@mcp.resource(
    uri="data://app-status",
    name="ApplicationStatus",
    description="Provides the current status of the application",
    mime_type="application/json",
    tags={"monitoring", "status"}
)
async def get_application_status() -> dict:
    """Get current application status."""
    return {
        "status": "operational",
        "uptime": get_uptime(),
        "version": "1.0.0"
    }
```

### File-based Resources

```python
import aiofiles
from pathlib import Path

@mcp.resource("file://logs/latest.txt", mime_type="text/plain")
async def read_latest_log() -> str:
    """Read the latest log file."""
    log_path = Path("/app/logs/latest.log")
    if not log_path.exists():
        return "Log file not found"

    async with aiofiles.open(log_path, mode="r") as f:
        content = await f.read()
    return content
```

## Resource Templates (Parameterized Resources)

Resource templates allow you to create dynamic URIs with parameters:

### Simple Template

```python
@mcp.resource("weather://{city}/current")
async def get_weather(city: str) -> dict:
    """Weather information for a specific city."""
    weather_data = await fetch_weather_api(city)
    return {
        "city": city.capitalize(),
        "temperature": weather_data["temp"],
        "condition": weather_data["condition"],
        "humidity": weather_data["humidity"]
    }
```

### Multi-Parameter Templates

```python
@mcp.resource("repos://{owner}/{repo}/info")
async def get_repo_info(owner: str, repo: str) -> dict:
    """GitHub repository information."""
    repo_data = await github_api.get_repo(owner, repo)
    return {
        "owner": owner,
        "name": repo,
        "stars": repo_data["stargazers_count"],
        "forks": repo_data["forks_count"],
        "description": repo_data["description"]
    }
```

### Wildcard Parameters

```python
@mcp.resource("files://{filepath*}")
async def get_file_content(filepath: str) -> str:
    """Get content of a file at any path depth."""
    # filepath can match multiple segments like "docs/api/resources.md"
    safe_path = sanitize_path(filepath)
    return await read_file_safely(safe_path)
```

### Optional Parameters with Defaults

```python
@mcp.resource("search://{query}")
async def search_content(
    query: str,
    max_results: int = 10,
    include_archived: bool = False
) -> dict:
    """Search content with optional parameters."""
    results = await search_engine.search(
        query=query,
        limit=max_results,
        include_archived=include_archived
    )
    return {
        "query": query,
        "total_results": len(results),
        "results": results
    }
```

## Advanced Patterns

### Context-Aware Resources

```python
from fastmcp import FastMCP, Context

@mcp.resource("data://user-context")
async def get_user_context(ctx: Context) -> dict:
    """Get context information about the current request."""
    return {
        "request_id": ctx.request_id,
        "timestamp": datetime.now().isoformat(),
        "session_info": "Active session"
    }
```

### Cached Resources

```python
from functools import lru_cache
import asyncio

class ResourceCache:
    def __init__(self):
        self._cache = {}
        self._ttl = {}

    async def get_or_fetch(self, key: str, fetch_func, ttl: int = 300):
        now = time.time()
        if key in self._cache and now < self._ttl.get(key, 0):
            return self._cache[key]

        data = await fetch_func()
        self._cache[key] = data
        self._ttl[key] = now + ttl
        return data

cache = ResourceCache()

@mcp.resource("data://expensive-computation")
async def get_expensive_data() -> dict:
    """Cached expensive computation."""
    return await cache.get_or_fetch(
        "expensive_data",
        lambda: perform_expensive_computation(),
        ttl=600  # 10 minutes
    )
```

### Database Resources

```python
import asyncpg

@mcp.resource("db://users/{user_id}")
async def get_user_from_db(user_id: str) -> dict:
    """Get user data from database."""
    async with asyncpg.create_pool(DATABASE_URL) as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                int(user_id)
            )
            if not row:
                raise ValueError(f"User {user_id} not found")

            return dict(row)
```

### API Integration Resources

```python
import httpx

@mcp.resource("api://external-service/{endpoint}")
async def get_external_data(endpoint: str) -> dict:
    """Fetch data from external API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.example.com/{endpoint}",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        response.raise_for_status()
        return response.json()
```

## Error Handling

### Standard Error Handling

```python
from fastmcp.exceptions import ResourceError

@mcp.resource("data://safe-resource")
async def safe_resource() -> dict:
    """Resource with proper error handling."""
    try:
        data = await fetch_sensitive_data()
        return data
    except FileNotFoundError:
        raise ResourceError("Data file not found")
    except PermissionError:
        raise ResourceError("Access denied to data source")
    except Exception as e:
        # Log internal error but don't expose details
        logger.error(f"Internal error: {e}")
        raise ResourceError("Internal server error occurred")
```

### Validation and Sanitization

```python
import re
from pathlib import Path

@mcp.resource("files://{filename}")
async def get_safe_file(filename: str) -> str:
    """Safely read files with validation."""
    # Validate filename
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        raise ResourceError("Invalid filename format")

    # Prevent directory traversal
    safe_path = Path("/safe/directory") / filename
    if not str(safe_path).startswith("/safe/directory"):
        raise ResourceError("Path traversal not allowed")

    if not safe_path.exists():
        raise ResourceError(f"File '{filename}' not found")

    return safe_path.read_text()
```

## Return Types and Content Types

### Text Content

```python
@mcp.resource("logs://latest", mime_type="text/plain")
async def get_latest_logs() -> str:
    """Return plain text logs."""
    return "2024-01-01 10:00:00 INFO Application started\n"
```

### JSON Content

```python
@mcp.resource("data://metrics", mime_type="application/json")
async def get_metrics() -> dict:
    """Return JSON metrics data."""
    return {
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "disk_usage": 23.1
    }
```

### Binary Content

```python
@mcp.resource("images://logo.png", mime_type="image/png")
async def get_logo() -> bytes:
    """Return binary image data."""
    with open("/assets/logo.png", "rb") as f:
        return f.read()
```

### Custom Content Types

```python
@mcp.resource("reports://summary.csv", mime_type="text/csv")
async def get_csv_report() -> str:
    """Return CSV formatted data."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Value", "Timestamp"])
    writer.writerow(["CPU", "45.2", "2024-01-01T10:00:00Z"])

    return output.getvalue()
```

## Resource Management

### Enabling/Disabling Resources

```python
@mcp.resource("data://debug-info", enabled=False)
def get_debug_info() -> dict:
    """Debug information (disabled by default)."""
    return {"debug": "sensitive information"}

# Dynamically enable/disable
def toggle_debug_mode(enabled: bool):
    get_debug_info.enable() if enabled else get_debug_info.disable()
```

### Resource Discovery

```python
@mcp.resource("meta://resources")
async def list_available_resources() -> dict:
    """List all available resources."""
    resources = []
    for uri, resource in mcp.resources.items():
        resources.append({
            "uri": uri,
            "name": getattr(resource, 'name', 'Unknown'),
            "description": getattr(resource, 'description', 'No description'),
            "enabled": getattr(resource, 'enabled', True)
        })

    return {"resources": resources}
```

## Performance Optimization

### Async Operations

```python
import asyncio

@mcp.resource("data://aggregated")
async def get_aggregated_data() -> dict:
    """Fetch data from multiple sources concurrently."""
    # Fetch multiple data sources concurrently
    tasks = [
        fetch_user_stats(),
        fetch_system_metrics(),
        fetch_recent_activity()
    ]

    user_stats, metrics, activity = await asyncio.gather(*tasks)

    return {
        "user_stats": user_stats,
        "system_metrics": metrics,
        "recent_activity": activity
    }
```

### Streaming Large Resources

```python
@mcp.resource("data://large-dataset")
async def get_large_dataset() -> dict:
    """Handle large datasets efficiently."""
    # For very large data, consider pagination or streaming
    return {
        "message": "Large dataset available",
        "pagination": {
            "page_size": 1000,
            "total_pages": 50,
            "next_page_uri": "data://large-dataset/page/1"
        }
    }

@mcp.resource("data://large-dataset/page/{page}")
async def get_dataset_page(page: str) -> dict:
    """Get a specific page of the large dataset."""
    page_num = int(page)
    offset = (page_num - 1) * 1000

    data = await fetch_paginated_data(offset=offset, limit=1000)

    return {
        "page": page_num,
        "data": data,
        "has_next": len(data) == 1000
    }
```

## Security Considerations

### Access Control

```python
from functools import wraps

def require_admin_access(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # In a real implementation, check user permissions
        # This is a simplified example
        if not check_admin_permissions():
            raise ResourceError("Admin access required")
        return await func(*args, **kwargs)
    return wrapper

@mcp.resource("admin://system-config")
@require_admin_access
async def get_admin_config() -> dict:
    """Admin-only system configuration."""
    return {"admin_setting": "sensitive_value"}
```

### Data Sanitization

```python
import html
import json

@mcp.resource("user://profile/{user_id}")
async def get_sanitized_profile(user_id: str) -> dict:
    """Get user profile with sanitized data."""
    user = await fetch_user(user_id)

    # Sanitize data before returning
    return {
        "id": user.id,
        "name": html.escape(user.name),
        "bio": html.escape(user.bio),
        "public_email": sanitize_email(user.email) if user.email_public else None
    }
```

## Testing Resources

### Unit Testing

```python
import pytest
from fastmcp import FastMCP
from fastmcp.testing import create_test_client

@pytest.fixture
def mcp_client():
    mcp = FastMCP("TestServer")

    @mcp.resource("test://data")
    def test_resource():
        return {"test": "data"}

    return create_test_client(mcp)

@pytest.mark.asyncio
async def test_resource_access(mcp_client):
    """Test basic resource access."""
    response = await mcp_client.read_resource("test://data")
    assert response.content[0].text == '{"test": "data"}'
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_database_resource():
    """Test database resource integration."""
    # Setup test database
    await setup_test_db()

    try:
        response = await mcp_client.read_resource("db://users/123")
        data = json.loads(response.content[0].text)
        assert "id" in data
        assert data["id"] == 123
    finally:
        await cleanup_test_db()
```

## Best Practices

### 1. Resource Naming
- Use consistent URI schemes (e.g., `data://`, `file://`, `api://`)
- Make resource names descriptive and hierarchical
- Use kebab-case for multi-word names

### 2. Error Handling
- Always handle exceptions gracefully
- Use `ResourceError` for client-facing errors
- Log internal errors but don't expose sensitive details

### 3. Performance
- Use async functions for I/O operations
- Implement caching for expensive computations
- Consider pagination for large datasets

### 4. Security
- Validate all input parameters
- Sanitize output data
- Implement proper access controls
- Never expose sensitive internal information

### 5. Documentation
- Provide clear docstrings for all resources
- Use descriptive parameter names and types
- Include usage examples in comments

## Common Use Cases

### Configuration Management
```python
@mcp.resource("config://app/{env}")
async def get_environment_config(env: str) -> dict:
    """Get configuration for specific environment."""
    valid_envs = ["dev", "staging", "prod"]
    if env not in valid_envs:
        raise ResourceError(f"Invalid environment: {env}")

    return await load_config(env)
```

### System Monitoring
```python
@mcp.resource("metrics://system")
async def get_system_metrics() -> dict:
    """Current system performance metrics."""
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }
```

### Data Aggregation
```python
@mcp.resource("reports://sales/{period}")
async def get_sales_report(period: str) -> dict:
    """Sales report for specified period."""
    start_date, end_date = parse_period(period)

    sales_data = await fetch_sales_data(start_date, end_date)

    return {
        "period": period,
        "total_sales": sum(s.amount for s in sales_data),
        "transaction_count": len(sales_data),
        "average_sale": sum(s.amount for s in sales_data) / len(sales_data)
    }
```

## Conclusion

Resources are a powerful way to expose data to LLM clients through the MCP protocol. By following the patterns and best practices outlined in this guide, you can create robust, secure, and efficient resource systems that enhance your AI applications' capabilities.

Remember to:
- Design clear, consistent URI schemes
- Handle errors gracefully
- Implement proper security measures
- Test thoroughly
- Document your resources well

For more advanced patterns and specific implementation details, refer to the FastMCP documentation and the official MCP specification.
