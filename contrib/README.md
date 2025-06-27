# Contributing to MCP Server for Splunk

This directory contains community-contributed tools, resources, and prompts for the MCP Server for Splunk. We welcome and encourage contributions from the community!

## 🚀 Quick Start for Contributors

**New to contributing? Use our helper scripts!**
```bash
# Generate a new tool interactively (recommended)
./contrib/scripts/generate_tool.py

# Browse existing tools for inspiration
./contrib/scripts/list_tools.py

# Validate your tool implementation
./contrib/scripts/validate_tools.py

# Run tests for your tools
./contrib/scripts/test_contrib.py
```

See [`contrib/scripts/README.md`](scripts/README.md) for detailed script documentation.

### 1. Project Structure

Community contributions are organized by type and domain:

```
contrib/
├── scripts/                # Helper scripts for contributors
│   ├── generate_tool.py    # Interactive tool generator
│   ├── list_tools.py       # Browse existing tools
│   ├── validate_tools.py   # Validate tool compliance
│   ├── test_contrib.py     # Run contrib tests
│   └── README.md           # Script documentation
├── tools/                  # Community tools
│   ├── examples/           # Example tools for learning
│   ├── security/           # Security-focused tools
│   ├── devops/            # DevOps/SRE tools
│   └── analytics/         # Business analytics tools
├── resources/             # Community resources
└── prompts/              # Community prompts
```

### 2. Creating a New Tool

**🎯 Recommended Approach: Use the Tool Generator**
```bash
./contrib/scripts/generate_tool.py
```
This interactive script will guide you through creating a properly structured tool with all requirements.

**✨ New: Splunk Search Template!**
The generator now includes a specialized **Splunk Search Template** for creating custom Splunk search tools:
- 🔍 **Custom SPL queries** with your specific search logic
- ⚡ **Instant tool generation** based on your working `splunk_search.py` 
- 🧪 **Comprehensive tests** with Splunk mocking
- 🎯 **Perfect for**: Security tools, DevOps monitoring, Business analytics
- 📝 **User-friendly input**: Choose single-line or multi-line input (type 'END' to finish)

Select option `2` (splunk_search template) when prompted! See [`contrib/scripts/SPLUNK_SEARCH_TEMPLATE.md`](scripts/SPLUNK_SEARCH_TEMPLATE.md) for details.

**Manual Approach:**
If you prefer to create tools manually:

1. **Choose the right directory** based on your tool's purpose
2. **Create a new Python file** in the appropriate subdirectory
3. **Inherit from BaseTool** and implement the required methods
4. **Add metadata** to describe your tool
5. **Test your tool** thoroughly

#### Example: Simple Hello World Tool

```python
# contrib/tools/examples/hello_world.py

from typing import Any, Dict
from fastmcp import Context
from src.core.base import BaseTool, ToolMetadata

class HelloWorldTool(BaseTool):
    """A simple example tool that demonstrates the contribution pattern."""
    
    METADATA = ToolMetadata(
        name="hello_world",
        description="A simple hello world example tool",
        category="examples", 
        tags=["example", "tutorial"],
        requires_connection=False
    )
    
    async def execute(self, ctx: Context, name: str = "World") -> Dict[str, Any]:
        """Say hello to someone."""
        message = f"Hello, {name}!"
        return self.format_success_response({"message": message})
```

### 3. Tool Categories

#### Security Tools (`contrib/tools/security/`)
Tools focused on security analysis, threat hunting, and incident response.

#### DevOps Tools (`contrib/tools/devops/`)
Tools for monitoring, alerting, and operational tasks.

#### Analytics Tools (`contrib/tools/analytics/`)
Tools for business intelligence, reporting, and data analysis.

### 4. Development Guidelines

#### Tool Requirements
- **Inherit from BaseTool**: All tools must extend the `BaseTool` class
- **Include Metadata**: Every tool must have a `METADATA` class attribute
- **Handle Errors Gracefully**: Use the base class error handling methods
- **Document Thoroughly**: Include clear docstrings and examples
- **Test Comprehensively**: Include unit tests for your tools

#### Naming Conventions
- **File names**: Use snake_case (e.g., `threat_hunting.py`)
- **Class names**: Use PascalCase (e.g., `ThreatHuntingTool`)
- **Tool names**: Use snake_case (e.g., `threat_hunting`)

#### Code Quality
- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Include comprehensive docstrings
- Handle edge cases and errors appropriately

### 5. Testing Your Contributions

**🧪 Quick Testing with Helper Scripts:**
```bash
# Run all contrib tests
./contrib/scripts/test_contrib.py

# Validate your tool implementation
./contrib/scripts/validate_tools.py contrib/tools/your_category/your_tool.py

# Run tests for specific category
./contrib/scripts/test_contrib.py your_category
```

**Manual Testing:**
Before submitting, make sure to:

1. **Run the existing test suite**: `pytest tests/`
2. **Test your tool individually**: Create unit tests in `tests/contrib/`
3. **Test integration**: Ensure your tool works with the MCP server
4. **Validate against live Splunk**: Test with actual Splunk instance if possible

### 6. Submission Process

1. **Fork the repository** on GitHub
2. **Create a feature branch** for your contribution
3. **Add your tool/resource/prompt** in the appropriate directory
4. **Include tests** for your contribution
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description

### 7. Review Process

All contributions will be reviewed for:
- **Code quality and style**
- **Security best practices**
- **Documentation completeness**
- **Test coverage**
- **Compatibility with existing tools**

### 8. Getting Help

- **Check the examples** in `contrib/tools/examples/`
- **Read the architecture docs** in `ARCHITECTURE.md`
- **Open an issue** on GitHub for questions
- **Join the discussion** in GitHub Discussions

## Advanced Contribution Patterns

### Custom Resource Example

```python
# contrib/resources/examples/sample_data.py

from fastmcp import Context
from src.core.base import BaseResource, ResourceMetadata

class SampleDataResource(BaseResource):
    """Provides sample Splunk data for testing."""
    
    METADATA = ResourceMetadata(
        uri="resource://sample_data",
        name="Sample Data",
        description="Sample Splunk search data for testing",
        category="examples"
    )
    
    async def get_content(self, ctx: Context) -> str:
        return "Sample data content here..."
```

### Custom Prompt Example

```python
# contrib/prompts/examples/basic_prompts.py

from fastmcp import Context
from src.core.base import BasePrompt, PromptMetadata

class SearchAssistantPrompt(BasePrompt):
    """Helps users build Splunk search queries."""
    
    METADATA = PromptMetadata(
        name="search_assistant",
        description="Assists with building Splunk search queries",
        category="examples",
        arguments=[
            {"name": "data_type", "description": "Type of data to search for"}
        ]
    )
    
    async def get_prompt(self, ctx: Context, data_type: str = "logs") -> Dict[str, Any]:
        template = f"Help me build a Splunk search query for {data_type}..."
        return {"template": template, "data_type": data_type}
```

## Community Resources

- **Documentation**: [Project Wiki](link-to-wiki)
- **Examples**: See `contrib/tools/examples/` for complete examples
- **Best Practices**: Check existing core tools in `src/tools/`
- **Issues**: [GitHub Issues](link-to-issues)
- **Discussions**: [GitHub Discussions](link-to-discussions)

Thank you for contributing to the MCP Server for Splunk community! 