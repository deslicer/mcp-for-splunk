# Contributor Helper Scripts

This directory contains helper scripts to streamline the contribution process for MCP Server for Splunk tools.

## Available Scripts

### 🛠️ generate_tool.py
Interactive tool generator that follows project guidelines.

```bash
# Generate a new tool interactively
./generate_tool.py

# Or run with Python
python contrib/scripts/generate_tool.py
```

**Features:**
- Prompts for all required information
- Generates properly structured tool files
- Creates corresponding test files
- Follows naming conventions automatically
- Includes TODO comments for easy completion
- **NEW: Splunk Search Template** - Create custom Splunk search tools instantly!

**Generated Structure:**
- Tool file: `contrib/tools/{category}/{tool_name}.py`
- Test file: `tests/contrib/{category}/test_{tool_name}.py`
- Proper imports and base class inheritance
- Metadata with appropriate tags
- Error handling templates

**Templates Available:**
- `basic`: Standard tool template with TODO placeholders
- `splunk_search`: **NEW!** Specialized template for Splunk search tools
  - Custom SPL query embedding with user-friendly input (single-line or multi-line)
  - Time range and result limit parameters
  - Comprehensive Splunk mocking in tests
  - Based on your working `splunk_search.py` tool

See [`SPLUNK_SEARCH_TEMPLATE.md`](SPLUNK_SEARCH_TEMPLATE.md) for detailed Splunk search template documentation.

---

### 📋 list_tools.py
Browse and explore existing contrib tools.

```bash
# List all tools summary
./list_tools.py

# Interactive browser
./list_tools.py --interactive

# Show detailed tool information
./list_tools.py --detail contrib/tools/examples/hello_world.py

# Show help
./list_tools.py --help
```

**Features:**
- Shows tool status (metadata, tests, Splunk requirements)
- Groups tools by category
- Interactive browsing mode
- Detailed file previews
- Identifies incomplete tools

---

### ✅ validate_tools.py
Validate tools for compliance with project guidelines.

```bash
# Validate all contrib tools
./validate_tools.py

# Validate specific tool
./validate_tools.py contrib/tools/examples/hello_world.py

# Show help
./validate_tools.py --help
```

**Validation Checks:**
- Required imports and class structure
- METADATA attribute completeness
- Proper execute method signature
- Naming conventions (snake_case files, PascalCase classes)
- Documentation (docstrings, type hints)
- Error handling patterns
- Test file existence and structure

---

### 🧪 test_contrib.py
Test runner specifically for contrib tools.

```bash
# Run all contrib tests
./test_contrib.py

# Run with verbose output
./test_contrib.py --verbose

# Run with coverage report
./test_contrib.py --coverage

# Run tests for specific category
./test_contrib.py examples

# List available test files
./test_contrib.py --list

# Check test environment
./test_contrib.py --check
```

**Features:**
- Focused on contrib tools only
- Category-specific test runs
- Environment validation
- Coverage reporting
- Clean output formatting

## Quick Start Workflow

1. **Generate a new tool:**
   ```bash
   ./generate_tool.py
   ```

2. **Implement your tool logic** (replace TODO comments)

3. **Validate your implementation:**
   ```bash
   ./validate_tools.py contrib/tools/your_category/your_tool.py
   ```

4. **Run tests:**
   ```bash
   ./test_contrib.py your_category
   ```

5. **Browse existing tools for inspiration:**
   ```bash
   ./list_tools.py --interactive
   ```

## Development Tips

### Tool Creation Best Practices
- Choose the right category (examples, security, devops, analytics)
- Use descriptive names and documentation
- Follow the error handling patterns
- Include comprehensive tests
- Use type hints throughout

### Testing Strategy
- Test both success and error cases
- Mock Splunk connections when needed
- Use `@pytest.mark.asyncio` for async tests
- Include parameter validation tests

### Validation Guidelines
- All tools should pass validation without errors
- Warnings are suggestions for improvement
- Run validation before submitting pull requests

## Script Requirements

These scripts require:
- Python 3.8+
- Project dependencies installed (`pip install -e .`)
- Running from project root directory

## Contributing to Scripts

If you want to improve these helper scripts:

1. Follow the same validation standards
2. Add tests for new functionality
3. Update this documentation
4. Test across different tool categories

## Troubleshooting

### Common Issues

**"Module not found" errors:**
- Ensure you're running from the project root
- Install dependencies: `pip install -e .`

**"No tests found":**
- Generate tools with test files using `generate_tool.py`
- Check that test files follow naming convention: `test_*.py`

**Validation failures:**
- Review the specific error messages
- Check the hello_world.py example for reference
- Ensure all required imports are present

**Permission errors:**
- Make scripts executable: `chmod +x contrib/scripts/*.py`
- Or run with: `python contrib/scripts/script_name.py`

## Getting Help

- Check the main contrib README: `contrib/README.md`
- Review existing examples: `contrib/tools/examples/`
- Open an issue on GitHub for bugs or feature requests
- Use `--help` flag on any script for usage information 