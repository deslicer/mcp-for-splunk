# Contributing to MCP Server for Splunk

Welcome to the community! We're excited to have you contribute to making AI and Splunk integration accessible to everyone.

## 🌟 Why Contribute?

- **Impact**: Help thousands of developers integrate AI with Splunk
- **Learning**: Gain experience with MCP, FastMCP, and Splunk technologies
- **Community**: Join a growing community of AI and Splunk enthusiasts
- **Recognition**: Get credit for your contributions in our documentation

## 🚀 Quick Start for Contributors

### 1. Set Up Development Environment

```bash
# Fork and clone the repository
git clone https://github.com/your-username/mcp-server-for-splunk.git
cd mcp-server-for-splunk

# Set up development environment
./scripts/build_and_run.sh --dev
```

### 2. Explore the Codebase

```bash
# Browse existing tools for inspiration
./contrib/scripts/list_tools.py --interactive

# Understand the structure
tree src/tools/ contrib/tools/
```

### 3. Create Your First Tool

```bash
# Interactive tool generator
./contrib/scripts/generate_tool.py

# Follow the prompts to create a new tool
# Test your tool
./contrib/scripts/validate_tools.py
```

## 🛠️ Contribution Types

### 🔧 New Tools

**What we're looking for:**

- Security and threat hunting tools
- DevOps and monitoring capabilities
- Analytics and reporting features
- Integration helpers and utilities

**Popular contribution ideas:**

- User behavior analysis tools
- Performance monitoring dashboards
- Automated incident response workflows
- Custom search and alerting capabilities

### 📚 Documentation

**Always needed:**

- Usage examples and tutorials
- Integration guides for new AI clients
- Best practices and patterns
- Translation to other languages

### 🐛 Bug Fixes

**High-impact areas:**

- Splunk API compatibility issues
- Tool error handling improvements
- Performance optimizations
- Test coverage enhancements

### 💡 Feature Enhancements

**Welcome improvements:**

- Better error messages and debugging
- New MCP protocol features
- Enhanced configuration options
- Performance optimizations

## 📝 Tool Development Guide

### Tool Structure

Every tool follows this pattern:

```python
# contrib/tools/category/my_tool.py
from src.core.base import BaseTool, ToolMetadata
from fastmcp import Context

class MyTool(BaseTool):
    """Brief description of what this tool does."""
    
    METADATA = ToolMetadata(
        name="my_tool",
        description="Detailed description for AI agents",
        category="security",  # security, devops, analytics, examples
        tags=["security", "analysis"],
        requires_connection=True,
        version="1.0.0"
    )
    
    async def execute(self, ctx: Context, **kwargs) -> dict:
        """Execute the tool logic."""
        try:
            # Your tool logic here
            result = await self.do_something(kwargs)
            return self.format_success_response(result)
        except Exception as e:
            return self.format_error_response(str(e))
```

### Best Practices

**✅ Do:**
- Include comprehensive docstrings
- Handle errors gracefully
- Validate input parameters
- Use descriptive parameter names
- Include usage examples
- Test with different Splunk configurations
- Follow existing code patterns

**❌ Don't:**
- Store credentials in code
- Use blocking I/O operations
- Ignore error cases
- Create overly complex tools
- Skip input validation
- Hard-code Splunk-specific values

### Tool Categories

#### 🛡️ Security Tools
Focus on threat hunting, incident response, and security analysis.

**Examples:**
- Suspicious user activity detection
- IOC (Indicator of Compromise) searching
- Threat intelligence integration
- Security event correlation

**Template:**

```python
class ThreatHuntingTool(BaseTool):
    METADATA = ToolMetadata(
        name="hunt_threats",
        description="Hunt for security threats using IOCs and behavioral patterns",
        category="security",
        tags=["security", "threat-hunting", "ioc"],
        requires_connection=True
    )
    
    async def execute(self, ctx: Context, 
                     indicators: list[str],
                     time_range: str = "-24h") -> dict:
        # Threat hunting logic
        pass
```

#### ⚙️ DevOps Tools
Monitoring, alerting, and operational intelligence.

**Examples:**
- Performance monitoring
- Capacity planning analysis
- Error rate tracking
- Service dependency mapping

**Template:**

```python
class PerformanceMonitorTool(BaseTool):
    METADATA = ToolMetadata(
        name="monitor_performance",
        description="Monitor application performance metrics and trends",
        category="devops",
        tags=["monitoring", "performance", "metrics"],
        requires_connection=True
    )
    
    async def execute(self, ctx: Context,
                     service_name: str,
                     metric_type: str = "response_time") -> dict:
        # Performance monitoring logic
        pass
```

#### 📈 Analytics Tools
Business intelligence, reporting, and data analysis.

**Examples:**
- KPI dashboards
- Trend analysis
- Predictive analytics
- Custom reporting

**Template:**

```python
class BusinessAnalyticsTool(BaseTool):
    METADATA = ToolMetadata(
        name="analyze_business_metrics",
        description="Analyze business KPIs and generate insights",
        category="analytics",
        tags=["analytics", "business", "kpi"],
        requires_connection=True
    )
    
    async def execute(self, ctx: Context,
                     metric_name: str,
                     analysis_type: str = "trend") -> dict:
        # Analytics logic
        pass
```

## 🧪 Testing Your Contributions

### Automated Testing

```bash
# Run all tests
make test

# Test only your contributions
make test-contrib

# Run with coverage
pytest --cov=contrib tests/contrib/
```

## 🔍 Code Quality

### Pre-commit Hooks

Keep formatting and linting consistent automatically.

```bash
# Install git hooks
uv run pre-commit install

# Run on all files (CI equivalent)
uv run pre-commit run --all-files

# Update hooks to latest pinned versions
uv run pre-commit autoupdate
```

Hooks configured:
- Black (formatting)
- Ruff (lint, auto-fix)
- End-of-file fixer
- Trailing whitespace

### Manual Testing

```bash
# Start development server
./scripts/build_and_run.sh --dev

# Test via MCP Inspector
open http://localhost:3001

# Test your specific tool
./contrib/scripts/test_contrib.py --tool my_tool
```

### Validation Checklist

- [ ] Tool follows naming conventions
- [ ] All required metadata fields present
- [ ] Error handling implemented
- [ ] Input validation working
- [ ] Documentation complete
- [ ] Tests pass
- [ ] No hardcoded credentials
- [ ] Follows project style guide

## 📋 Submission Process

### 1. Create a Branch

```bash
# Create feature branch
git checkout -b feature/my-awesome-tool

# Or for bug fixes
git checkout -b fix/issue-description
```

### 2. Implement Your Changes

```bash
# Create your tool
./contrib/scripts/generate_tool.py

# Test thoroughly
./contrib/scripts/validate_tools.py
make test-contrib

# Document your changes
# Update contrib/README.md if needed
```

### 3. Submit Pull Request

**Pull Request Template:**

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] New tool
- [ ] Bug fix
- [ ] Documentation update
- [ ] Feature enhancement

## Tool Details (if applicable)
- **Name**: tool_name
- **Category**: security/devops/analytics
- **Description**: What it does
- **Splunk Requirements**: Any specific Splunk setup needed

## Testing
- [ ] Tool validated with validation script
- [ ] Tested with MCP Inspector
- [ ] Unit tests added/updated
- [ ] Documentation updated

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass
```

### 4. Code Review Process

**What to expect:**
1. **Automated checks**: Style, tests, validation
2. **Community review**: Other contributors provide feedback
3. **Maintainer review**: Final review by project maintainers
4. **Merge**: Once approved, your contribution is merged!

## 👥 Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment:

- **Be respectful**: Treat everyone with kindness and respect
- **Be constructive**: Provide helpful feedback and suggestions
- **Be collaborative**: Work together towards common goals
- **Be patient**: Remember that everyone is learning

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community chat
- **Pull Requests**: Code review and collaboration
- **Documentation**: Contribute to guides and examples

### Recognition

Contributors are recognized in:
- Project README and documentation
- Release notes for their contributions
- Community showcases and examples
- Annual contributor acknowledgments

## 🎯 Priority Areas

### High-Impact Contributions

**Most needed right now:**
1. **Security tools** for threat hunting and incident response
2. **Integration examples** for popular AI frameworks
3. **Performance optimizations** for large-scale deployments
4. **Documentation** for complex use cases

**Future roadmap:**
1. **Advanced analytics** tools and visualizations
2. **Machine learning** integration capabilities
3. **Real-time streaming** data processing
4. **Multi-cloud** deployment patterns

### Beginner-Friendly Tasks

**Good first contributions:**
- Documentation improvements
- Example tool implementations
- Test coverage enhancements
- Bug fixes with clear reproduction steps

**Look for issues labeled:**
- `good-first-issue`
- `documentation`
- `beginner-friendly`
- `help-wanted`

## 🔧 Development Tools

### Available Scripts

```bash
# Development helpers
./contrib/scripts/generate_tool.py    # Interactive tool creator
./contrib/scripts/list_tools.py       # Browse existing tools
./contrib/scripts/validate_tools.py   # Validate tool implementation
./contrib/scripts/test_contrib.py     # Test community tools

# Testing and validation
make test                             # Run all tests
make test-contrib                     # Test contributions only
make test-fast                        # Quick development tests
make lint                             # Code style checks
```

### Development Environment

**Required tools:**
- Python 3.10+
- UV package manager
- Git

**Optional tools:**
- Docker (for full stack testing)
- Node.js (for MCP Inspector)

**IDE setup:**
- VSCode with Python extension
- PyCharm with FastMCP plugin
- Vim/Neovim with Python LSP

## 🎉 Success Stories

### Featured Contributions

**Community highlights:**
- **@contributor1**: Created the threat hunting toolkit with 5 security tools
- **@contributor2**: Added comprehensive Kubernetes deployment guides
- **@contributor3**: Optimized search performance by 40%

**Impact metrics:**
- 50+ community-contributed tools
- 1000+ developers using community tools
- 24/7 community support and maintenance

### How Your Contribution Helps

Every contribution makes a difference:
- **Tools**: Help organizations improve their security and operations
- **Documentation**: Enable new users to get started quickly
- **Bug fixes**: Improve reliability for everyone
- **Examples**: Teach others best practices and patterns

---

**Ready to contribute?** 🚀

Start with our [interactive tool generator](../../contrib/scripts/generate_tool.py) or browse [existing tools](../../contrib/tools/) for inspiration!

**Questions?** Join our [GitHub Discussions](https://github.com/your-org/mcp-server-for-splunk/discussions) - the community is here to help! 