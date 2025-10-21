# MCP Server for Splunk Documentation

Welcome to the comprehensive documentation for the MCP Server for Splunk! This documentation is organized to help you find exactly what you need, whether you're just getting started or diving deep into advanced topics.

## 🎯 Quick Navigation

### New to MCP Server for Splunk?

**Start here** → [Getting Started Guide](getting-started/)

### Want to validate your setup fast?

**Run tests now** → [Tests Quick Start](tests.md)

### Want to integrate with AI clients?

**Go to** → [Integration Guide](guides/integration/)

### Need to deploy to production?

**Check out** → [Deployment Guide](guides/deployment/)

### Want to contribute or extend?

**Visit** → [Contributing Guide](contrib/contributing.md)

## 📚 Documentation Structure

### 🚀 Getting Started

Perfect for first-time users and quick setup.

| Guide | Description | Time | Audience |
|-------|-------------|------|----------|
| **[Overview](getting-started/)** | What is MCP Server for Splunk? | 5 min | Everyone |
| **[Installation](getting-started/installation.md)** | Step-by-step setup guide | 15 min | New users |
| **[Troubleshooting](getting-started/troubleshooting.md)** | Common issues and solutions | Reference | Everyone |
| **[Tests Quick Start](tests.md)** | First success experience | 2 min | New users |

### 📖 User Guides

Practical guides for common tasks and scenarios.

| Guide | Description | Time | Audience |
|-------|-------------|------|----------|
| **[Integration](guides/integration/)** | Connect AI clients to MCP server | 30 min | Developers |
| **[Configuration](guides/configuration/)** | Configuration options and patterns | 20 min | Operators |
| **[Deployment](guides/deployment/)** | Production deployment strategies | 45 min | DevOps |
| **[Security](guides/security.md)** | Security best practices | 30 min | Security teams |
| **[Testing](guides/TESTING.md)** | Testing and validation | 15 min | Developers |
| **[Tests Quick Start](tests.md)** | Fast path to a green run | 2 min | Developers |
| **[Lookups & Dashboards](guides/lookups_and_dashboards.md)** | Working with lookups and dashboards | 15 min | All users |
| **[Migration](guides/migration_guide.md)** | Upgrading and migration | 20 min | Existing users |

### 🏗️ Architecture

Technical deep-dives for developers and architects.

| Document | Description | Time | Audience |
|----------|-------------|------|----------|
| **[Overview](architecture/)** | High-level architecture guide | 15 min | Architects |
| **[System Design](architecture/overview.md)** | Detailed system architecture | 30 min | Developers |
| Components | Component breakdown (coming soon) | 45 min | Contributors |
| Extension Guide | How to extend the system (coming soon) | 60 min | Contributors |

### 📝 API Reference

Complete reference documentation for tools, resources, and APIs.

| Reference | Description | Audience |
|-----------|-------------|----------|
| **[Tools Reference](reference/tools.md)** | Tool documentation | Developers |
| **[Resources Reference](reference/resources.md)** | Resource documentation | Developers |

### 🤝 Community

Guides for contributing and community participation.

| Guide | Description | Time | Audience |
|-------|-------------|------|----------|
| **[Contributing](contrib/contributing.md)** | How to contribute | 30 min | Contributors |
| **[Tool Development](contrib/tool_development.md)** | Creating new tools | 60 min | Developers |

## 🎭 Documentation by Role

### 👩‍💻 For Developers

**Building AI applications with Splunk data**

1. **Quick Start**: [Getting Started](getting-started/) → [Integration Guide](guides/integration/)
2. **Deep Dive**: [Tools Reference](reference/tools.md) → [Architecture](architecture/)
3. **Extend**: [Contributing](contrib/contributing.md) → [Tool Development](contrib/tool_development.md)

**Key Resources:**

- [Claude Desktop Integration](guides/integration/#claude-desktop)
- [Google ADK Examples](guides/integration/#google-agent-development-kit-adk)
- [HTTP Client Integration](guides/integration/#http-transport-integration)

### 🛠️ For DevOps/Platform Engineers

**Deploying and operating MCP servers**

1. **Planning**: [Deployment Guide](guides/deployment/) → Security Guide (coming soon)
2. **Implementation**: [Production Deployment](guides/deployment/production.md) → [Configuration](guides/configuration/)
3. **Operations**: [Monitoring](guides/monitoring.md)

**Key Resources:**

- [Docker Deployment](guides/deployment/DOCKER.md)
- Kubernetes Setup (coming soon)
- **[Security Best Practices](guides/security.md)**

### 🏢 For Splunk Administrators

**Integrating AI with existing Splunk infrastructure**

1. **Understanding**: [Getting Started](getting-started/) → [Architecture Overview](architecture/)
2. **Planning**: [Security Guide](guides/security.md) → [Configuration Guide](guides/configuration/)
3. **Implementation**: [Installation](getting-started/installation.md) → [Testing](guides/TESTING.md)

**Key Resources:**

- [Splunk Permissions](guides/security.md#splunk-permissions)
- [Multi-tenant Configuration](guides/configuration/#multi-tenant-setup)
- **[Health Monitoring](guides/monitoring.md)**

### 🔍 For Security Teams

**Threat hunting and security analysis with AI**

1. **Capabilities**: [Tools Reference](reference/tools.md) → [Integration Examples](guides/integration/)
2. **Implementation**: [Security Guide](guides/security.md) → [Deployment](guides/deployment/)
3. **Extension**: [Tool Development](contrib/tool_development.md)

**Key Resources:**

- Threat Hunting Tools (see [Tools Reference](reference/tools.md))
- Security Integration Patterns (see [Integration Guide](guides/integration/))

### 🎓 For Contributors

**Adding tools and improving the project**

1. **Start**: [Contributing Guide](contrib/contributing.md) → [Development Setup](contrib/contributing.md#development-environment)
2. **Create**: [Tool Development](contrib/tool_development.md) → [Testing](guides/TESTING.md)
3. **Share**: [Pull Request Process](community/contributing.md#submission-process) → [Community](community/)

**Key Resources:**

- [Interactive Tool Generator](community/tool-development.md#tool-generator)
- [Tool Templates](community/tool-development.md#tool-templates)
- [Validation Scripts](community/tool-development.md#validation)

## 🔍 Quick Reference

### Common Tasks

| Task | Documentation | Time |
|------|---------------|------|
| **Set up for development** | [Getting Started](getting-started/) | 15 min |
| **Connect Claude Desktop** | [Claude Integration](guides/integration/#claude-desktop) | 10 min |
| **Deploy to production** | [Production Guide](guides/deployment/production.md) | 45 min |
| **Create a custom tool** | [Tool Development](community/tool-development.md) | 60 min |
| **Run tests** | [Tests Quick Start](tests.md) | 2 min |
| **Configure security** | [Security Guide](guides/security.md) | 30 min |
| **Troubleshoot issues** | [Troubleshooting](getting-started/troubleshooting.md) | Variable |

### Quick Links

- **🔗 [Project Repository](https://github.com/your-org/mcp-server-for-splunk)**
- **🐛 [Report Issues](https://github.com/your-org/mcp-server-for-splunk/issues)**
- **💬 [Community Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions)**
- **📋 [Roadmap](https://github.com/your-org/mcp-server-for-splunk/projects)**

### External Resources

- **[Model Context Protocol](https://modelcontextprotocol.io/)** - Official MCP specification
- **[FastMCP Framework](https://gofastmcp.com/)** - MCP server framework we use
- **[Splunk REST API](https://docs.splunk.com/Documentation/Splunk/latest/RESTREF)** - Splunk API reference
- **[Claude Desktop](https://claude.ai/desktop)** - Popular MCP client

## 📋 Documentation Standards

Our documentation follows these principles:

### 🎯 User-Centered Design

- **Hook** (10 seconds): Why should I care?
- **Quick Start** (2 minutes): Can I get this working?
- **Navigation** (30 seconds): Where do I go next?

### 📝 Writing Standards

- **Clear and concise**: Maximum 3-4 sentences per paragraph
- **Action-oriented**: Use active voice and direct instructions
- **Example-rich**: Every concept has a working example
- **Tested**: All code examples are tested and current

### 🔧 Technical Standards

- **Complete**: Include all prerequisites and context
- **Current**: Code examples work with latest versions
- **Accessible**: Alt text for images, clear formatting
- **Linked**: Comprehensive cross-references

## 🔄 Contributing to Documentation

Found a gap or error? We welcome documentation contributions!

### Quick Fixes

- **Typos and small errors**: Edit directly via GitHub
- **Broken links**: Report via [Issues](https://github.com/your-org/mcp-server-for-splunk/issues)
- **Missing examples**: Submit via [Pull Request](https://github.com/your-org/mcp-server-for-splunk/pulls)

### Major Contributions

- **New guides**: Follow our [Documentation Style Guide](docs/readme-guide.md)
- **Structural changes**: Discuss in [GitHub Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions)
- **Translation**: Contact maintainers for coordination

---

**Ready to get started?** 🚀

- **New users**: Begin with [Getting Started](getting-started/)
- **Developers**: Jump to [Integration Guide](guides/integration/)
- **Contributors**: Check out [Contributing Guide](community/contributing.md)

**Need help?** Join our [community discussions](https://github.com/your-org/mcp-server-for-splunk/discussions) - we're here to help!
