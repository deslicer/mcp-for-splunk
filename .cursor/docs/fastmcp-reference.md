# FastMCP Documentation Reference

This reference file provides organized access to FastMCP documentation via Context7 integration.

## Quick Context7 Integration

To get the latest documentation for any topic, use:
```python
# Use Context7 MCP tool to get latest docs
await mcp_Context7_get_library_docs(
    context7CompatibleLibraryID="/fastmcp/fastmcp",
    topic="<topic_from_below>",
    tokens=10000
)
```

## Core Development Topics

### Server Development
- **Topic**: "server setup and configuration"
- **Key Areas**: Basic server creation, configuration, middleware setup
- **Links**: [Server Basics](https://gofastmcp.com/servers/server.md)

- **Topic**: "tool development and decorators"
- **Key Areas**: Creating tools, parameter validation, decorators
- **Links**: [Tools](https://gofastmcp.com/servers/tools.md), [Decorating Methods](https://gofastmcp.com/patterns/decorating-methods.md)

- **Topic**: "middleware and error handling"
- **Key Areas**: Request/response middleware, error handling, rate limiting
- **Links**: [Middleware](https://gofastmcp.com/servers/middleware.md), [Error Handling](https://gofastmcp.com/python-sdk/fastmcp-server-middleware-error_handling.md)

### Client Development
- **Topic**: "client setup and authentication"
- **Key Areas**: Client initialization, bearer tokens, OAuth
- **Links**: [Client](https://gofastmcp.com/clients/client.md), [Bearer Auth](https://gofastmcp.com/clients/auth/bearer.md)

- **Topic**: "tool operations and execution"
- **Key Areas**: Discovering tools, executing tools, handling responses
- **Links**: [Tool Operations](https://gofastmcp.com/clients/tools.md)

### Testing and Development
- **Topic**: "testing mcp servers"
- **Key Areas**: Testing patterns, in-memory testing, integration tests
- **Links**: [Testing](https://gofastmcp.com/patterns/testing.md), [Utilities Tests](https://gofastmcp.com/python-sdk/fastmcp-utilities-tests.md)

- **Topic**: "http requests and patterns"
- **Key Areas**: HTTP handling, request processing, ASGI integration
- **Links**: [HTTP Requests](https://gofastmcp.com/patterns/http-requests.md), [ASGI Integration](https://gofastmcp.com/deployment/asgi.md)

## Advanced Features

### Resources and Templates
- **Topic**: "resources and templates"
- **Key Areas**: Static resources, templated resources, resource management
- **Links**: [Resources](https://gofastmcp.com/servers/resources.md), [Templates](https://gofastmcp.com/python-sdk/fastmcp-resources-template.md)

### Context and Communication
- **Topic**: "mcp context and capabilities"
- **Key Areas**: Context access, logging, progress reporting, user elicitation
- **Links**: [Context](https://gofastmcp.com/servers/context.md), [Logging](https://gofastmcp.com/servers/logging.md), [Progress](https://gofastmcp.com/servers/progress.md)

- **Topic**: "prompts and sampling"
- **Key Areas**: Prompt templates, LLM sampling, message handling
- **Links**: [Prompts](https://gofastmcp.com/servers/prompts.md), [Sampling](https://gofastmcp.com/servers/sampling.md)

### Integration and Deployment
- **Topic**: "deployment and transports"
- **Key Areas**: STDIO, HTTP, SSE transports, server deployment
- **Links**: [Running Server](https://gofastmcp.com/deployment/running-server.md), [Transports](https://gofastmcp.com/clients/transports.md)

- **Topic**: "openapi integration"
- **Key Areas**: OpenAPI spec generation, FastAPI integration
- **Links**: [OpenAPI](https://gofastmcp.com/servers/openapi.md)

## Architecture Patterns

### Server Composition
- **Topic**: "server composition and proxy"
- **Key Areas**: Combining servers, mounting, proxy patterns
- **Links**: [Composition](https://gofastmcp.com/servers/composition.md), [Proxy](https://gofastmcp.com/servers/proxy.md)

### Tool Transformation
- **Topic**: "tool transformation and enhancement"
- **Key Areas**: Tool variants, schema modification, argument mapping
- **Links**: [Tool Transformation](https://gofastmcp.com/patterns/tool-transformation.md)

## LLM Integration

### Client Integrations
- **Topic**: "anthropic integration"
- **Links**: [Anthropic API](https://gofastmcp.com/integrations/anthropic.md)

- **Topic**: "openai integration"
- **Links**: [OpenAI API](https://gofastmcp.com/integrations/openai.md)

- **Topic**: "claude desktop integration"
- **Links**: [Claude Desktop](https://gofastmcp.com/integrations/claude-desktop.md)

## Security and Authentication

### Authentication Patterns
- **Topic**: "bearer token authentication"
- **Key Areas**: JWT validation, token providers, security
- **Links**: [Bearer Auth](https://gofastmcp.com/servers/auth/bearer.md), [Bearer Providers](https://gofastmcp.com/python-sdk/fastmcp-server-auth-providers-bearer.md)

- **Topic**: "oauth authentication"
- **Links**: [OAuth](https://gofastmcp.com/clients/auth/oauth.md)

## Utilities and Helpers

### Development Tools
- **Topic**: "fastmcp cli and utilities"
- **Key Areas**: CLI usage, development tools, caching
- **Links**: [CLI](https://gofastmcp.com/patterns/cli.md), [Cache](https://gofastmcp.com/python-sdk/fastmcp-utilities-cache.md)

- **Topic**: "json schema and validation"
- **Links**: [JSON Schema](https://gofastmcp.com/python-sdk/fastmcp-utilities-json_schema.md)

## Quick Reference Commands

### Get Specific Documentation
```python
# For testing patterns (matches your minimal mocking preference)
docs = await mcp_Context7_get_library_docs(
    context7CompatibleLibraryID="/fastmcp/fastmcp",
    topic="testing mcp servers",
    tokens=5000
)

# For tool development
docs = await mcp_Context7_get_library_docs(
    context7CompatibleLibraryID="/fastmcp/fastmcp", 
    topic="tool development and decorators",
    tokens=8000
)

# For server setup
docs = await mcp_Context7_get_library_docs(
    context7CompatibleLibraryID="/fastmcp/fastmcp",
    topic="server setup and configuration", 
    tokens=6000
)
```

### Common Workflows
```python
# Complete server development workflow
topics = [
    "server setup and configuration",
    "tool development and decorators", 
    "testing mcp servers",
    "middleware and error handling"
]

for topic in topics:
    docs = await mcp_Context7_get_library_docs(
        context7CompatibleLibraryID="/fastmcp/fastmcp",
        topic=topic,
        tokens=5000
    )
```

## Project-Specific Patterns

### For Splunk MCP Server Development
- Focus on: "tool development", "testing patterns", "http requests"
- Authentication: "bearer token authentication" for API security
- Integration: "openapi integration" for API documentation

### Key FastMCP Concepts for This Project
1. **In-memory testing** - Aligns with your testing preferences
2. **Tool decorators** - For Splunk API wrapping
3. **Context management** - For Splunk connection handling
4. **Error handling** - For robust Splunk API interactions

## Usage Tips

1. **Start Broad**: Use general topics first, then narrow down
2. **Combine Topics**: Mix related concepts for comprehensive understanding
3. **Token Management**: Adjust token count based on complexity needed
4. **Regular Updates**: Context7 provides latest docs, no local staleness

## Emergency References

If Context7 is unavailable, fallback to direct links from the [FastMCP sitemap](https://gofastmcp.com/llms.txt). 