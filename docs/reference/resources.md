# MCP Resources Reference

## Overview

Resources in the Model Context Protocol (MCP) are read-only, URI-addressable data endpoints that LLM clients can retrieve on demand. They provide context (documents, configuration, health, search results) without performing side effects.

## Resources vs Tools (FastMCP)

- **Resources**: model-readable, GET-like, discovered and fetched via `list_resources()` and `read_resource()`; ideal for config, docs, status, or search results.
- **Tools**: model-invoked actions with inputs/outputs and potential side effects; used for executing searches, creating objects, etc.

## Using resources with the FastMCP client

```python
# List resources
resources = await client.list_resources()  # -> list[mcp.types.Resource]

# Read a static or dynamic resource
content = await client.read_resource("file:///path/to/README.md")
print(content[0].text)  # Assuming text

# Read a template-based resource
weather = await client.read_resource("data://weather/london")
print(weather[0].text)  # Assuming text
```

You can also enumerate templates:

```python
templates = await client.list_resource_templates()  # -> list[mcp.types.ResourceTemplate]
```

## Defining resources (FastMCP)

Annotate Python callables with `@mcp.resource()` to expose resources. You can include metadata such as `uri`, `name`, `description`, `mime_type`, and `tags`.

```python
from fastmcp import FastMCP

mcp = FastMCP(name="DataServer")

@mcp.resource(
    uri="data://app-status",
    name="ApplicationStatus",
    description="Provides the current status of the application.",
    mime_type="application/json",
    tags={"monitoring", "status"}
)
def get_application_status() -> dict:
    return {"status": "ok", "uptime": 12345}
```

### Resource templates

URIs can include parameters (mapped to function arguments) to generate dynamic content.

```python
@mcp.resource("weather://{city}/current")
def get_weather(city: str) -> dict:
    return {"city": city.capitalize(), "temperature": 22, "unit": "celsius"}

@mcp.resource("repos://{owner}/{repo}/info")
def get_repo_info(owner: str, repo: str) -> dict:
    return {"owner": owner, "name": repo}
```

### Static/predefined resources

You can register static content directly (files, text, directory listings):

```python
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.resources import FileResource, TextResource, DirectoryResource

mcp = FastMCP(name="DataServer")

# File
readme_path = Path("./README.md").resolve()
if readme_path.exists():
    mcp.add_resource(FileResource(
        uri=f"file://{readme_path.as_posix()}",
        path=readme_path,
        name="README File",
        description="The project's README.",
        mime_type="text/markdown",
        tags={"documentation"}
    ))

# Text
mcp.add_resource(TextResource(
    uri="resource://notice",
    name="Important Notice",
    text="System maintenance scheduled for Sunday.",
))

# Directory listing
data_dir = Path("./app_data").resolve()
if data_dir.is_dir():
    mcp.add_resource(DirectoryResource(
        uri="resource://data-files",
        path=data_dir,
        name="Data Directory Listing",
        description="Lists directory files",
        recursive=False
    ))
```

### Duplicate handling

Configure how duplicate URIs are handled during registration:

```python
from fastmcp import FastMCP

mcp = FastMCP(name="ResourceServer", on_duplicate_resources="error")  # error|warn(default)|ignore

@mcp.resource("data://config")
def get_config_v1():
    return {"version": 1}
```

## Server-specific resources (MCP Server for Splunk)

This server auto-registers several Splunk-focused resources from `src/resources/`. Common URIs include:

- `splunk-docs://cheat-sheet` — SPL cheat sheet (markdown)
- `splunk-docs://discovery` — discover available documentation resources
- `splunk-docs://{version}/spl-reference/{command}` — SPL command docs
- `splunk-docs://{version}/admin/{topic}` — Admin guides
- `splunk-docs://{version}/troubleshooting/{topic}` — Troubleshooting docs
- `splunk://config/{config_file}` — Splunk config (e.g., `indexes.conf`, `props.conf`)
- `splunk://health/status` — Health summary (JSON)
- `splunk://apps/installed` — Installed apps with capability analysis (JSON)
- `splunk://indexes/list` — Index metadata (JSON; excludes internal indexes)
- `splunk://savedsearches/list` — Saved searches (JSON)
- `splunk://search/results/recent` — Recent completed searches (JSON)

Example (Python client):

```python
from fastmcp import Client

async with Client(server) as client:
    # Discover
    res = await client.list_resources()
    for r in res:
        print(r.uri, r.name)

    # Read health
    health = await client.read_resource("splunk://health/status")
    print(health[0].text)

    # Read a specific config
    cfg = await client.read_resource("splunk://config/indexes.conf")
    print(cfg[0].text)
```

### Client-scoped isolation and credentials

Splunk resources are client-scoped. Provide Splunk connection details via HTTP headers (or server environment variables) so the server can securely construct a per-client connection and validate access.

Required headers:

```text
X-Splunk-Host: your-splunk-host
X-Splunk-Username: your-username
X-Splunk-Password: your-password
X-Splunk-Port: 8089            # optional
X-Splunk-Scheme: https          # optional
X-Splunk-Verify-SSL: false      # optional
```

If headers are not provided, the server attempts a safe default/fallback and returns helpful error payloads when unavailable.

## Return types and content

Resources can return text, JSON, or binary content. Set `mime_type` appropriately (for example: `text/markdown`, `application/json`, `image/png`). Clients handle serialization transparently.

## Best practices

- **Stable URIs**: Keep URIs descriptive and version-tolerant when applicable.
- **Template parameters**: Validate and sanitize path parameters.
- **Security**: Enforce client isolation and never expose secrets in outputs.
- **Performance**: Cache heavy resources and paginate large payloads.
- **Discoverability**: Provide clear names/descriptions and tags for better client UX.

## References

- FastMCP resources overview and code examples: `https://gofastmcp.com/servers/resources`
- FastMCP client usage for resources: `https://gofastmcp.com/clients/client`


