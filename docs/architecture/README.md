# Architecture Documentation

This section provides comprehensive technical documentation about the MCP Server for Splunk architecture, design patterns, and extensibility.

## 📋 Architecture Overview

| Document | Description | Audience |
|----------|-------------|----------|
| **[System Overview](overview.md)** | High-level architecture and design principles | Architects, Tech Leads |
| Component Design (coming soon) | Detailed component breakdown and interactions | Developers |
| Extension Guide (coming soon) | How to extend and customize the system | Contributors |
| Data Flow (coming soon) | Request flow and data processing patterns | Developers, Debuggers |

## 🏗️ Quick Architecture Summary

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Client     │    │   MCP Server    │    │   Splunk API    │
│                 │    │                 │    │                 │
│ • Claude        │◄──►│ • FastMCP       │◄──►│ • REST API      │
│ • Cursor        │    │ • Tool Registry │    │ • Search API    │
│ • Custom Apps   │    │ • Discovery     │    │ • Admin API     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Design Principles

- **🔍 Auto-Discovery**: Tools and resources are automatically discovered and loaded
- **🔌 Modular**: Each tool is independent and self-contained
- **🛡️ Secure**: Client-scoped access with no credential exposure
- **🚀 Extensible**: Easy to add new tools and capabilities
- **🌐 Transport Agnostic**: Works with stdio and HTTP transports

### Directory Structure

```
src/
├── core/                 # Core framework
│   ├── base.py          # Base classes and interfaces
│   ├── discovery.py     # Automatic component discovery
│   ├── registry.py      # Component registration
│   └── loader.py        # Dynamic loading into FastMCP
│
├── tools/               # Core tools (project-maintained)
│   ├── search/          # Search and analytics tools
│   ├── metadata/        # Data discovery tools
│   ├── admin/           # Administration tools
│   ├── kvstore/         # KV Store operations
│   └── health/          # System monitoring tools
│
├── resources/           # Information resources
│   ├── splunk_config.py # Configuration access
│   ├── splunk_docs.py   # Documentation resources
│   └── processors/      # Content processing
│
├── prompts/            # Reusable prompt templates
└── client/             # Splunk client abstraction

contrib/                # Community contributions
├── tools/              # Community-contributed tools
├── scripts/            # Development and testing scripts
└── examples/           # Usage examples and templates
```

## 🔧 Technical Concepts

### Tool Discovery and Loading

1. **Scan Phase**: Discover all Python modules in `src/mcp_server_for_splunk/tools/` and `contrib/tools/`
2. **Registration Phase**: Register tools with metadata validation
3. **Loading Phase**: Dynamically load into FastMCP server
4. **Runtime Phase**: Tools available for MCP client invocation

### Configuration Management

The system supports multiple configuration sources with precedence:

1. **HTTP Headers** (highest priority) - Multi-tenant scenarios
2. **Client Environment Variables** - MCP client configuration
3. **Server Environment Variables** - Traditional server config
4. **Configuration Files** - `.env` files and config objects

### Security Model

- **No Credential Storage**: Credentials provided by clients
- **Client Scoping**: Each client can connect to different Splunk instances
- **Minimal Permissions**: Tools request only necessary Splunk permissions
- **Transport Security**: HTTPS for network transport, secure stdio for local

## 🎯 Use Cases

### Development Patterns

**Tool Development:**
- Inherit from `BaseTool` for standard functionality
- Use `ToolMetadata` for discovery and documentation
- Implement async `execute()` method for tool logic

**Resource Development:**
- Inherit from `BaseResource` for information resources
- Implement content processors for different data types
- Use URI patterns for resource identification

**Integration Patterns:**
- stdio transport for local AI clients (Claude, Cursor)
- HTTP transport for web applications and remote access
- Multi-tenant deployment for serving multiple clients

## 📊 Performance Characteristics

### Startup Performance
- **Local Mode**: ~10 seconds (single Python process)
- **Docker Mode**: ~2 minutes (full stack with containers)
- **Tool Loading**: ~1-2 seconds for 20+ tools

### Runtime Performance
- **Simple Tools**: <100ms response time
- **Search Operations**: 1-30 seconds (depends on Splunk query complexity)
- **Memory Usage**: ~50-100MB for server process

### Scalability
- **Concurrent Clients**: 10-100+ depending on transport mode
- **Tool Capacity**: Unlimited (dynamic loading)
- **Splunk Connections**: Pooled and reused per client configuration

## 🔍 Debugging and Observability

### Logging Levels
- **ERROR**: Critical issues and failures
- **WARNING**: Important issues that don't stop operation
- **INFO**: General operational information
- **DEBUG**: Detailed execution tracing

### Monitoring Points
- Tool execution times and success rates
- Splunk connection health and response times
- Client connection patterns and usage
- Resource utilization and performance metrics

### Debug Features
- **Interactive Testing**: MCP Inspector for tool validation
- **Detailed Logging**: Configurable log levels and output
- **Health Endpoints**: Service health and status monitoring
- **Error Handling**: Graceful degradation and error reporting

## 🚀 Getting Started

### For Architects
1. Review [System Overview](overview.md) for high-level design
2. Component Design (coming soon) for implementation details
3. Extension Patterns (coming soon) for customization needs

### For Developers
1. Component Design (coming soon) for development patterns
2. Extension Guide (coming soon) to add new functionality
3. Data Flow (coming soon) for debugging and optimization

### For Operators
1. Understand deployment patterns in [System Overview](overview.md)
2. Review monitoring and observability features
3. Plan capacity and scaling based on performance characteristics

---

**Next Steps**: Choose the specific architecture topic that matches your role and needs!
