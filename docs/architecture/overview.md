# MCP Server for Splunk - Architecture Guide

## Project Structure

This document outlines the modular architecture designed to support community contributions and extensibility.

### Directory Structure

```
mcp-server-for-splunk/
├── src/
│   ├── __init__.py
│   ├── server.py                    # Main server entry point
│   ├── core/                        # Core framework components
│   │   ├── __init__.py
│   │   ├── base.py                  # Base classes for tools/resources/prompts
│   │   ├── context.py               # Shared context management
│   │   ├── discovery.py             # Tool/resource/prompt discovery
│   │   ├── loader.py                # Dynamic loading system
│   │   ├── registry.py              # Tool registry management
│   │   └── utils.py                 # Common utilities
│   ├── client/                      # Splunk connection management
│   │   ├── __init__.py
│   │   ├── splunk_client.py         # Splunk SDK wrapper
│   │   └── connection_pool.py       # Connection pooling (future)
│   ├── tools/                       # Core tools (maintained by project)
│   │   ├── __init__.py
│   │   ├── search/                  # Search-related tools
│   │   │   ├── __init__.py
│   │   │   ├── oneshot_search.py
│   │   │   ├── job_search.py
│   │   │   └── realtime_search.py   # Future
│   │   ├── metadata/                # Metadata tools
│   │   │   ├── __init__.py
│   │   │   ├── indexes.py
│   │   │   ├── sourcetypes.py
│   │   │   └── sources.py
│   │   ├── kvstore/                 # KV Store tools
│   │   │   ├── __init__.py
│   │   │   ├── collections.py
│   │   │   └── data.py
│   │   ├── admin/                   # Administrative tools
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── users.py
│   │   │   └── config.py
│   │   └── health/                  # Health and monitoring
│   │       ├── __init__.py
│   │       └── status.py
│   ├── resources/                   # Core resources
│   │   ├── __init__.py
│   │   ├── health.py                # Health check resources
│   │   └── documentation.py         # API documentation resources
│   └── prompts/                     # Core prompts
│       ├── __init__.py
│       ├── search_assistant.py      # Search query building
│       └── troubleshooting.py       # Diagnostic prompts
├── contrib/                         # Community contributions
│   ├── README.md                    # Contribution guidelines
│   ├── tools/                       # Community tools
│   │   ├── examples/                # Example tools for contributors
│   │   │   ├── __init__.py
│   │   │   └── hello_world.py       # Simple example tool
│   │   ├── security/                # Security-focused tools
│   │   │   ├── __init__.py
│   │   │   ├── threat_hunting.py
│   │   │   └── incident_response.py
│   │   ├── devops/                  # DevOps/SRE tools
│   │   │   ├── __init__.py
│   │   │   ├── monitoring.py
│   │   │   └── alerting.py
│   │   └── analytics/               # Business analytics tools
│   │       ├── __init__.py
│   │       ├── reporting.py
│   │       └── dashboards.py
│   ├── resources/                   # Community resources
│   │   ├── examples/
│   │   │   ├── __init__.py
│   │   │   └── sample_data.py
│   │   └── security/
│   │       ├── __init__.py
│   │       └── threat_feeds.py
│   └── prompts/                     # Community prompts
│       ├── examples/
│       │   ├── __init__.py
│       │   └── basic_prompts.py
│       └── security/
│           ├── __init__.py
│           └── threat_analysis.py
├── plugins/                         # External plugins (future)
│   ├── README.md
│   └── .gitkeep
├── config/                          # Configuration management
│   ├── __init__.py
│   ├── settings.py                  # Configuration schema
│   ├── tool_registry.yaml          # Tool registration config
│   └── defaults/                    # Default configurations
│       ├── tools.yaml
│       ├── resources.yaml
│       └── prompts.yaml
├── docs/                           # Documentation
│   ├── api/                        # API documentation
│   ├── contrib/                    # Contribution guides
│   │   ├── tool_development.md
│   │   ├── resource_development.md
│   │   ├── prompt_development.md
│   │   └── testing_guide.md
│   ├── examples/                   # Usage examples
│   └── deployment/                 # Deployment guides
├── tests/                          # Test suite
│   ├── core/                       # Core framework tests
│   ├── tools/                      # Core tool tests
│   ├── contrib/                    # Community contribution tests
│   └── integration/                # Integration tests
└── scripts/                        # Utility scripts
    ├── dev_setup.sh               # Development environment setup
    ├── register_tools.py          # Tool registration utility
    └── validate_contrib.py        # Contribution validation
```

## Architecture Principles

### 1. Modular Design
- **Core Framework**: Stable, well-tested foundation in `src/core/`
- **Core Tools**: Essential Splunk tools maintained by the project team
- **Community Contributions**: Extensions and specialized tools in `contrib/`
- **Plugin System**: Future support for external packages in `plugins/`

### 2. Discovery and Loading
- **Automatic Discovery**: Tools, resources, and prompts are discovered automatically
- **Configuration-Driven**: Tool registration via YAML configuration
- **Dynamic Loading**: Hot-reload capability for development
- **Namespace Isolation**: Clear separation between core and contrib components

### 3. Base Classes and Interfaces
All tools, resources, and prompts inherit from base classes that provide:
- Consistent error handling
- Logging integration
- Context management
- Validation framework
- Testing utilities

### 4. Community Contribution Framework
- **Clear Guidelines**: Standardized development patterns
- **Testing Requirements**: Automated testing for all contributions
- **Code Quality**: Linting and formatting standards
- **Documentation**: Required documentation for all contributions
- **Review Process**: Clear contribution and review workflow

## Implementation Benefits

### For Core Maintainers
- **Separation of Concerns**: Core framework separate from tools
- **Easier Maintenance**: Modular components easier to update
- **Quality Control**: Standardized patterns and testing
- **Scalability**: Framework can grow without complexity explosion

### For Contributors
- **Clear Structure**: Obvious where to place new tools
- **Development Tools**: Utilities for creating and testing tools
- **Examples**: Rich set of examples to learn from
- **Guided Process**: Clear contribution guidelines and workflows

### For Users
- **Discoverability**: Easy to find available tools and capabilities
- **Customization**: Can enable/disable specific tool categories
- **Documentation**: Comprehensive API and usage documentation
- **Reliability**: Consistent quality across all tools

## Next Steps

1. **Refactor Current Code**: Extract tools from `server.py` into modular components
2. **Create Base Classes**: Establish foundation classes and interfaces
3. **Implement Discovery**: Build automatic tool/resource/prompt discovery
4. **Setup Contribution Framework**: Create guidelines and development tools
5. **Add Examples**: Provide clear examples for contributors
6. **Documentation**: Comprehensive contributor and user documentation
