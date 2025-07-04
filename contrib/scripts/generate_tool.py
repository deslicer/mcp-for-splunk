#!/usr/bin/env python3
"""
Tool Generator for MCP Server for Splunk Contributors

This script helps contributors create new tools following the project guidelines.
It generates properly structured tool files with all necessary components.
"""

import sys
from pathlib import Path

# Tool categories as defined in README
TOOL_CATEGORIES = {
    "examples": "Example tools for learning and demonstration",
    "security": "Security-focused tools for threat hunting and incident response",
    "devops": "DevOps/SRE tools for monitoring and operational tasks",
    "analytics": "Business analytics tools for reporting and data analysis",
}

# Common tags for each category
CATEGORY_TAGS = {
    "examples": ["example", "tutorial", "demo"],
    "security": ["security", "threat-hunting", "incident-response"],
    "devops": ["devops", "monitoring", "sre", "operations"],
    "analytics": ["analytics", "reporting", "business-intelligence"],
}

# Tool templates
TOOL_TEMPLATES = {
    "basic": "Basic tool template with standard functionality",
    "splunk_search": "Splunk search tool template for custom SPL queries",
}


def get_user_input(prompt: str, required: bool = True, options: list[str] = None) -> str:
    """Get user input with validation."""
    while True:
        if options:
            print(f"\nAvailable options: {', '.join(options)}")

        value = input(f"{prompt}: ").strip()

        if not value and required:
            print("This field is required. Please enter a value.")
            continue

        if options and value and value not in options:
            print(f"Invalid option. Please choose from: {', '.join(options)}")
            continue

        return value


def get_multiline_input(prompt: str, required: bool = True) -> str:
    """Get multiline input from user."""
    print(f"{prompt}")
    print(
        "(Enter your query line by line. Type 'END' on a new line to finish, or Ctrl+C to cancel)"
    )
    print("Example:")
    print("  index=main sourcetype=access_combined")
    print("  | stats count by status")
    print("  | sort -count")
    print("  END")
    print()

    lines = []

    try:
        while True:
            line = input("> ")
            if line.strip().upper() == "END":
                break
            lines.append(line)
    except KeyboardInterrupt:
        if required:
            print("\nInput required. Please try again.")
            return get_multiline_input(prompt, required)
        return ""

    result = "\n".join(lines).strip()
    if required and not result:
        print("This field is required. Please try again.")
        return get_multiline_input(prompt, required)

    return result


def to_snake_case(text: str) -> str:
    """Convert text to snake_case."""
    import re

    # Replace spaces and hyphens with underscores
    text = re.sub(r"[-\s]+", "_", text)
    # Convert camelCase/PascalCase to snake_case
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    return text.lower()


def to_pascal_case(text: str) -> str:
    """Convert text to PascalCase."""
    words = to_snake_case(text).split("_")
    return "".join(word.capitalize() for word in words if word)


def get_tool_info() -> dict[str, str]:
    """Collect tool information from user."""
    print("=" * 60)
    print("MCP Server for Splunk - Tool Generator")
    print("=" * 60)
    print("\nThis script will help you create a new tool following the project guidelines.")
    print("Please provide the following information:\n")

    # Get template type
    print("1. Tool Template")
    template_list = list(TOOL_TEMPLATES.items())
    for i, (template, desc) in enumerate(template_list, 1):
        print(f"   {i}. {template}: {desc}")

    while True:
        try:
            choice = int(
                get_user_input(f"\nSelect template (1-{len(template_list)})", required=True)
            )
            if 1 <= choice <= len(template_list):
                template = template_list[choice - 1][0]
                break
            else:
                print(f"Please enter a number between 1 and {len(template_list)}")
        except ValueError:
            print("Please enter a valid number")

    # Get category
    print("\n2. Tool Category")
    category_list = list(TOOL_CATEGORIES.items())
    for i, (cat, desc) in enumerate(category_list, 1):
        print(f"   {i}. {cat}: {desc}")

    while True:
        try:
            choice = int(
                get_user_input(f"\nSelect category (1-{len(category_list)})", required=True)
            )
            if 1 <= choice <= len(category_list):
                category = category_list[choice - 1][0]
                break
            else:
                print(f"Please enter a number between 1 and {len(category_list)}")
        except ValueError:
            print("Please enter a valid number")

    # Get basic info
    print("\n3. Tool Details")
    name = get_user_input("Tool name (e.g., 'threat hunter', 'log analyzer')", required=True)
    description = get_user_input("Description (brief summary of what the tool does)", required=True)

    # Template-specific inputs
    template_data = {}
    if template == "splunk_search":
        print("\n4. Splunk Search Configuration")

        # Get SPL query
        print("\nSplunk Search Query (SPL) Input:")
        print("   1. Multi-line input (for complex queries)")
        print("   2. Single-line input (for simple queries)")

        while True:
            try:
                choice = int(get_user_input("Select input method (1-2)", required=True))
                if choice == 1:
                    print("\nEnter your Splunk search query (SPL):")
                    spl_query = get_multiline_input("SPL Query", required=True)
                    break
                elif choice == 2:
                    print(
                        "\nExample: index=main sourcetype=access_combined | stats count by status"
                    )
                    spl_query = get_user_input("SPL Query (single line)", required=True)
                    break
                else:
                    print("Please enter 1 or 2")
            except ValueError:
                print("Please enter a valid number")

        # Get query description
        query_description = get_user_input(
            "Query description (what does this search do?)", required=True
        )

        # Get default parameters
        print("\n5. Default Search Parameters")
        default_earliest = (
            get_user_input("Default earliest time (e.g., '-1h', '-24h')", required=False) or "-15m"
        )
        default_latest = (
            get_user_input("Default latest time (e.g., 'now', '-30m')", required=False) or "now"
        )
        default_max_results = (
            get_user_input("Default max results (number)", required=False) or "100"
        )

        # Additional search parameters
        print("\nAdd custom search parameters?")
        print("   1. Yes")
        print("   2. No")

        while True:
            try:
                choice = int(get_user_input("Select option (1-2)", required=True))
                if choice == 1:
                    use_custom_params = True
                    break
                elif choice == 2:
                    use_custom_params = False
                    break
                else:
                    print("Please enter 1 or 2")
            except ValueError:
                print("Please enter a valid number")
        custom_params = []

        if use_custom_params:
            print("\n6. Custom Parameters")

            # First, ask how many parameters they want to add
            while True:
                try:
                    num_params = int(
                        get_user_input(
                            "How many custom parameters do you want to add?", required=True
                        )
                    )
                    if num_params < 0:
                        print("Please enter a non-negative number")
                        continue
                    elif num_params == 0:
                        print("No custom parameters will be added")
                        break
                    else:
                        break
                except ValueError:
                    print("Please enter a valid number")

            # Then collect that many parameters
            for i in range(num_params):
                print(f"\nParameter {i + 1} of {num_params}:")
                param_name = get_user_input("Parameter name (snake_case)", required=True)

                print(f"Type for {param_name}:")
                print("   1. str")
                print("   2. int")
                print("   3. bool")
                print("   4. float")

                type_options = ["str", "int", "bool", "float"]
                while True:
                    try:
                        type_choice = int(get_user_input("Select type (1-4)", required=True))
                        if 1 <= type_choice <= 4:
                            param_type = type_options[type_choice - 1]
                            break
                        else:
                            print("Please enter a number between 1 and 4")
                    except ValueError:
                        print("Please enter a valid number")

                param_desc = get_user_input(f"Description for {param_name}", required=True)
                param_default = get_user_input(
                    f"Default value for {param_name} (optional)", required=False
                )

                custom_params.append(
                    {
                        "name": param_name,
                        "type": param_type,
                        "description": param_desc,
                        "default": param_default,
                    }
                )

        template_data = {
            "spl_query": spl_query,
            "query_description": query_description,
            "default_earliest": default_earliest,
            "default_latest": default_latest,
            "default_max_results": default_max_results,
            "custom_params": custom_params,
        }

    # Get additional details
    section_num = (
        7
        if template == "splunk_search" and template_data.get("custom_params")
        else 5
        if template == "splunk_search"
        else 4
    )
    print(f"\n{section_num}. Additional Configuration")

    if template == "splunk_search":
        requires_connection = True
    else:
        print("Requires Splunk connection?")
        print("   1. Yes")
        print("   2. No")

        while True:
            try:
                choice = int(get_user_input("Select option (1-2)", required=True))
                if choice == 1:
                    requires_connection = True
                    break
                elif choice == 2:
                    requires_connection = False
                    break
                else:
                    print("Please enter 1 or 2")
            except ValueError:
                print("Please enter a valid number")

    # Get custom tags
    default_tags = CATEGORY_TAGS[category].copy()
    if template == "splunk_search":
        default_tags.extend(["splunk", "search", "spl"])

    print(f"\nDefault tags for {category}: {', '.join(default_tags)}")
    custom_tags = get_user_input("Additional tags (comma-separated, optional)", required=False)

    tags = default_tags
    if custom_tags:
        tags.extend([tag.strip() for tag in custom_tags.split(",")])

    # Generate names
    snake_name = to_snake_case(name)
    class_name = to_pascal_case(name) + "Tool"

    return {
        "template": template,
        "category": category,
        "name": name,
        "snake_name": snake_name,
        "class_name": class_name,
        "description": description,
        "requires_connection": str(requires_connection),
        "tags": tags,
        **template_data,
    }


def generate_splunk_search_tool_file(info: dict[str, str]) -> str:
    """Generate a Splunk search tool Python file content."""

    tags_str = ", ".join(f'"{tag}"' for tag in info["tags"])

    # Format the SPL query for Python string
    spl_query = info["spl_query"].replace('"', '\\"').replace("\n", " ").strip()

    # Generate custom parameters
    custom_params_str = ""
    custom_params_docstring = ""
    custom_params_logging = ""

    if info.get("custom_params"):
        param_parts = []
        doc_parts = []
        log_parts = []

        for param in info["custom_params"]:
            param_name = param["name"]
            param_type = param["type"]

            # Handle default values with proper formatting
            if param["default"]:
                param_default = param["default"]
                # Validate and format default values based on type
                if param_type == "str":
                    # Ensure string defaults are properly quoted
                    if not (param_default.startswith('"') and param_default.endswith('"')):
                        param_default = f'"{param_default}"'
                elif param_type == "bool":
                    # Validate boolean values
                    if param_default.lower() in ["true", "1", "yes"]:
                        param_default = "True"
                    elif param_default.lower() in ["false", "0", "no"]:
                        param_default = "False"
                    else:
                        param_default = "False"  # Default to False if invalid
                elif param_type == "int":
                    # Validate integer values
                    try:
                        int(param_default)
                    except ValueError:
                        param_default = "0"  # Default to 0 if invalid
                elif param_type == "float":
                    # Validate float values
                    try:
                        float(param_default)
                    except ValueError:
                        param_default = "0.0"  # Default to 0.0 if invalid
            else:
                # Use type-appropriate defaults when no value provided
                param_default = {"str": '""', "int": "0", "bool": "False", "float": "0.0"}[
                    param_type
                ]

            type_hint = {"str": "str", "int": "int", "bool": "bool", "float": "float"}[param_type]

            param_parts.append(f"{param_name}: {type_hint} = {param_default}")
            doc_parts.append(f"            {param_name}: {param['description']}")
            log_parts.append(param_name)

        custom_params_str = ", " + ", ".join(param_parts)
        custom_params_docstring = "\n" + "\n".join(doc_parts)
        custom_params_logging = ", " + ", ".join([f"{p}={p}" for p in log_parts])

    template = f'''"""
{info["description"]}

SPL Query: {info["query_description"]}
"""

import time
from typing import Any, Dict

from fastmcp import Context
from splunklib.results import ResultsReader
from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution, sanitize_search_query


class {info["class_name"]}(BaseTool):
    """
    {info["description"]}

    This tool executes the following Splunk search:
    {info["query_description"]}

    SPL Query:
    {info["spl_query"]}
    """

    METADATA = ToolMetadata(
        name="{info["snake_name"]}",
        description="{info["description"]}",
        category="{info["category"]}",
        tags=[{tags_str}],
        requires_connection={info["requires_connection"]},
        version="1.0.0"
    )

    async def execute(
        self,
        ctx: Context,
        earliest_time: str = "{info["default_earliest"]}",
        latest_time: str = "{info["default_latest"]}",
        max_results: int = {info["default_max_results"]}{custom_params_str}
    ) -> Dict[str, Any]:
        """
        Execute the {info["name"]} Splunk search.

        Args:
            earliest_time: Search start time (default: "{info["default_earliest"]}")
            latest_time: Search end time (default: "{info["default_latest"]}")
            max_results: Maximum number of results to return (default: {info["default_max_results"]}){custom_params_docstring}

        Returns:
            Dict containing:
                - results: List of search results as dictionaries
                - results_count: Number of results returned
                - query_executed: The actual query that was executed
                - duration: Search execution time in seconds
        """
        log_tool_execution("{info["snake_name"]}", earliest_time=earliest_time, latest_time=latest_time, max_results=max_results{custom_params_logging})

        self.logger.info(f"Executing {info["name"]} search")
        ctx.info(f"Running {info["name"]} search operation")

        try:
            is_available, service, error_msg = self.check_splunk_available(ctx)
            if not is_available:
                return self.format_error_response(error_msg)

            kwargs = {{
                "earliest_time": earliest_time,
                "latest_time": latest_time,
                "count": max_results
            }}
            ctx.info(f"Search parameters: {{kwargs}}")

            # The SPL query for this tool
            query = "{spl_query}"

            # Sanitize and prepare the query
            query = sanitize_search_query(query)
            start_time = time.time()
            job = service.jobs.oneshot(query, **kwargs)
            results = []
            result_count = 0

            for result in ResultsReader(job):
                if isinstance(result, dict):
                    results.append(result)
                    result_count += 1
                    if result_count >= max_results:
                        break

            duration = time.time() - start_time

            return self.format_success_response({{
                "results": results,
                "results_count": result_count,
                "query_executed": query,
                "duration": round(duration, 3)
            }})

        except Exception as e:
            self.logger.error(f"Failed to execute {info["name"]} search: {{str(e)}}")
            ctx.error(f"Failed to execute {info["name"]} search: {{str(e)}}")
            return self.format_error_response(str(e))
'''

    return template


def generate_tool_file(info: dict[str, str]) -> str:
    """Generate the tool Python file content based on template."""

    if info["template"] == "splunk_search":
        return generate_splunk_search_tool_file(info)

    # Default basic template (existing functionality)
    tags_str = ", ".join(f'"{tag}"' for tag in info["tags"])

    template = f'''"""
{info["description"]}
"""

from typing import Any, Dict

from fastmcp import Context

from src.core.base import BaseTool, ToolMetadata
from src.core.utils import log_tool_execution


class {info["class_name"]}(BaseTool):
    """
    {info["description"]}

    This tool provides functionality for:
    - TODO: Add specific functionality descriptions
    - TODO: Add use cases
    - TODO: Add examples
    """

    METADATA = ToolMetadata(
        name="{info["snake_name"]}",
        description="{info["description"]}",
        category="{info["category"]}",
        tags=[{tags_str}],
        requires_connection={info["requires_connection"]},
        version="1.0.0"
    )

    async def execute(self, ctx: Context, **kwargs) -> Dict[str, Any]:
        """
        Execute the {info["name"]} functionality.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Dict containing the tool results

        Example:
            {info["snake_name"]}() -> {{"result": "TODO: Add example result"}}
        """
        log_tool_execution("{info["snake_name"]}", **kwargs)

        self.logger.info(f"Executing {info["name"]} tool")
        ctx.info(f"Running {info["name"]} operation")

        try:
            # TODO: Implement tool functionality here
            #
            # If this tool requires Splunk connection:
            # is_available, service, error_msg = self.check_splunk_available(ctx)
            # if not is_available:
            #     return self.format_error_response(error_msg)
            #
            # Example implementation:
            result = {{
                "message": "TODO: Implement {info["name"]} functionality",
                "tool": "{info["snake_name"]}",
                "parameters": kwargs
            }}

            return self.format_success_response(result)

        except Exception as e:
            self.logger.error(f"Failed to execute {info["name"]}: {{str(e)}}")
            ctx.error(f"Failed to execute {info["name"]}: {{str(e)}}")
            return self.format_error_response(str(e))
'''

    return template


def generate_splunk_search_test_file(info: dict[str, str]) -> str:
    """Generate test file for Splunk search tools."""

    template = f'''"""
Tests for {info["class_name"]}.
"""

import pytest
from unittest.mock import MagicMock, patch

from fastmcp import Context
from contrib.tools.{info["category"]}.{info["snake_name"]} import {info["class_name"]}


class Test{info["class_name"]}:
    """Test cases for {info["class_name"]}."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return {info["class_name"]}(
            name="{info["snake_name"]}",
            description="{info["description"]}"
        )

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        ctx = MagicMock(spec=Context)
        ctx.info = MagicMock()
        ctx.error = MagicMock()
        return ctx

    @pytest.fixture
    def mock_splunk_service(self):
        """Create a mock Splunk service."""
        service = MagicMock()
        mock_job = MagicMock()
        mock_results = [
            {{"field1": "value1", "count": 10}},
            {{"field1": "value2", "count": 5}}
        ]

        with patch('contrib.tools.{info["category"]}.{info["snake_name"]}.ResultsReader') as mock_reader:
            mock_reader.return_value = iter(mock_results)
            service.jobs.oneshot.return_value = mock_job
            yield service

    @pytest.mark.asyncio
    async def test_execute_success_default_params(self, tool, mock_context, mock_splunk_service):
        """Test successful execution with default parameters."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.{info["category"]}.{info["snake_name"]}.ResultsReader') as mock_reader:
            mock_results = [{{"field1": "test", "count": 1}}]
            mock_reader.return_value = iter(mock_results)

            result = await tool.execute(mock_context)

        assert result["status"] == "success"
        assert "results" in result
        assert "results_count" in result
        assert "query_executed" in result
        assert "duration" in result
        assert result["results_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_custom_parameters(self, tool, mock_context, mock_splunk_service):
        """Test execution with custom time parameters."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))

        with patch('contrib.tools.{info["category"]}.{info["snake_name"]}.ResultsReader') as mock_reader:
            mock_reader.return_value = iter([])

            result = await tool.execute(
                mock_context,
                earliest_time="-1h",
                latest_time="-30m",
                max_results=50
            )

        assert result["status"] == "success"

        # Verify search parameters
        call_kwargs = mock_splunk_service.jobs.oneshot.call_args[1]
        assert call_kwargs["earliest_time"] == "-1h"
        assert call_kwargs["latest_time"] == "-30m"
        assert call_kwargs["count"] == 50

    @pytest.mark.asyncio
    async def test_execute_splunk_unavailable(self, tool, mock_context):
        """Test execution when Splunk is unavailable."""
        error_msg = "Splunk service is not available"
        tool.check_splunk_available = MagicMock(return_value=(False, None, error_msg))

        result = await tool.execute(mock_context)

        assert result["status"] == "error"
        assert result["error"] == error_msg

    @pytest.mark.asyncio
    async def test_execute_search_exception(self, tool, mock_context, mock_splunk_service):
        """Test error handling when search fails."""
        tool.check_splunk_available = MagicMock(return_value=(True, mock_splunk_service, ""))
        mock_splunk_service.jobs.oneshot.side_effect = Exception("Search failed")

        result = await tool.execute(mock_context)

        assert result["status"] == "error"
        assert "Search failed" in result["error"]

    def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = {info["class_name"]}.METADATA

        assert metadata.name == "{info["snake_name"]}"
        assert metadata.description == "{info["description"]}"
        assert metadata.category == "{info["category"]}"
        assert metadata.requires_connection is True
        assert "splunk" in metadata.tags
        assert "search" in metadata.tags
        assert metadata.version == "1.0.0"

    def test_tool_initialization(self, tool):
        """Test tool initialization."""
        assert tool.name == "{info["snake_name"]}"
        assert tool.description == "{info["description"]}"
        assert hasattr(tool, 'logger')
'''

    return template


def generate_test_file(info: dict[str, str]) -> str:
    """Generate the test file content based on template."""

    if info["template"] == "splunk_search":
        return generate_splunk_search_test_file(info)

    # Default basic template
    template = f'''"""
Tests for {info["class_name"]}.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastmcp import Context
from contrib.tools.{info["category"]}.{info["snake_name"]} import {info["class_name"]}


class Test{info["class_name"]}:
    """Test cases for {info["class_name"]}."""

    @pytest.fixture
    def tool(self):
        """Create a tool instance for testing."""
        return {info["class_name"]}(
            name="{info["snake_name"]}",
            description="{info["description"]}"
        )

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        ctx = MagicMock(spec=Context)
        ctx.info = MagicMock()
        ctx.error = MagicMock()
        return ctx

    @pytest.mark.asyncio
    async def test_execute_success(self, tool, mock_context):
        """Test successful tool execution."""
        # TODO: Implement test for successful execution
        result = await tool.execute(mock_context)

        assert result["status"] == "success"
        assert "tool" in result
        assert result["tool"] == "{info["snake_name"]}"

    @pytest.mark.asyncio
    async def test_execute_with_parameters(self, tool, mock_context):
        """Test tool execution with parameters."""
        # TODO: Add test with specific parameters
        test_params = {{"param1": "value1"}}

        result = await tool.execute(mock_context, **test_params)

        assert result["status"] == "success"
        # TODO: Add assertions for parameter handling

    @pytest.mark.asyncio
    async def test_metadata(self, tool):
        """Test tool metadata."""
        metadata = {info["class_name"]}.METADATA

        assert metadata.name == "{info["snake_name"]}"
        assert metadata.description == "{info["description"]}"
        assert metadata.category == "{info["category"]}"
        assert metadata.requires_connection == {info["requires_connection"]}
        assert len(metadata.tags) > 0

    # TODO: Add more specific tests based on tool functionality
    # - Test error handling
    # - Test edge cases
    # - Test Splunk connection requirements (if applicable)
    # - Test parameter validation
'''

    return template


def create_files(info: dict[str, str]) -> None:
    """Create the tool and test files."""

    # Determine project root (assuming script is in contrib/scripts/)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    # Create tool directory if it doesn't exist
    tool_dir = project_root / "contrib" / "tools" / info["category"]
    tool_dir.mkdir(parents=True, exist_ok=True)

    # Create __init__.py if it doesn't exist
    init_file = tool_dir / "__init__.py"
    if not init_file.exists():
        with open(init_file, "w") as f:
            f.write(f'"""\n{TOOL_CATEGORIES[info["category"]]}\n"""\n')

    # Create tool file
    tool_file = tool_dir / f"{info['snake_name']}.py"
    if tool_file.exists():
        print(f"\nFile {tool_file} already exists. Overwrite?")
        print("   1. Yes")
        print("   2. No")

        while True:
            try:
                choice = int(get_user_input("Select option (1-2)", required=True))
                if choice == 1:
                    break  # Continue with creation
                elif choice == 2:
                    print("Skipping tool file creation.")
                    return
                else:
                    print("Please enter 1 or 2")
            except ValueError:
                print("Please enter a valid number")

    with open(tool_file, "w") as f:
        f.write(generate_tool_file(info))

    print(f"✓ Created tool file: {tool_file}")

    # Ask about test file
    print("\nCreate test file?")
    print("   1. Yes")
    print("   2. No")

    while True:
        try:
            choice = int(get_user_input("Select option (1-2)", required=True))
            if choice == 1:
                create_test = True
                break
            elif choice == 2:
                create_test = False
                break
            else:
                print("Please enter 1 or 2")
        except ValueError:
            print("Please enter a valid number")

    if create_test:
        # Create test directory structure
        test_dir = project_root / "tests" / "contrib" / info["category"]
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create test __init__.py files
        for parent in [project_root / "tests" / "contrib", test_dir]:
            init_file = parent / "__init__.py"
            if not init_file.exists():
                with open(init_file, "w") as f:
                    f.write('"""\nContrib tests\n"""\n')

        # Create test file
        test_file = test_dir / f"test_{info['snake_name']}.py"
        with open(test_file, "w") as f:
            f.write(generate_test_file(info))

        print(f"✓ Created test file: {test_file}")


def main():
    """Main function."""
    try:
        # Get tool information
        info = get_tool_info()

        # Show summary
        print(f"\n{'=' * 60}")
        print("Summary")
        print(f"{'=' * 60}")
        print(f"Template: {info['template']}")
        print(f"Category: {info['category']}")
        print(f"Tool Name: {info['name']}")
        print(f"Class Name: {info['class_name']}")
        print(f"File Name: {info['snake_name']}.py")
        print(f"Description: {info['description']}")
        print(f"Requires Connection: {info['requires_connection']}")
        print(f"Tags: {', '.join(info['tags'])}")

        if info["template"] == "splunk_search":
            print("\nSplunk Search Details:")
            print(f"Query Description: {info['query_description']}")
            print(f"Default Time Range: {info['default_earliest']} to {info['default_latest']}")
            print(f"Default Max Results: {info['default_max_results']}")
            if info.get("custom_params"):
                print(f"Custom Parameters: {len(info['custom_params'])} parameters")
            print("\nSPL Query:")
            print(f"  {info['spl_query']}")

        # Confirm creation
        print("\nCreate this tool?")
        print("   1. Yes")
        print("   2. No")

        while True:
            try:
                choice = int(get_user_input("Select option (1-2)", required=True))
                if choice == 1:
                    create = True
                    break
                elif choice == 2:
                    create = False
                    break
                else:
                    print("Please enter 1 or 2")
            except ValueError:
                print("Please enter a valid number")

        if create:
            create_files(info)

            print(f"\n{'=' * 60}")
            print("Tool Created Successfully!")
            print(f"{'=' * 60}")
            print("\nNext steps:")
            print("1. Edit the generated file to implement your tool logic")
            print("2. Replace TODO comments with actual implementation")
            print("3. Add proper error handling and validation")
            print("4. Update the test file with comprehensive tests")
            print(
                f"5. Test your tool: pytest tests/contrib/{info['category']}/test_{info['snake_name']}.py"
            )
            print("6. Add your tool to the registry if needed")
            print(f"\nFile location: contrib/tools/{info['category']}/{info['snake_name']}.py")

        else:
            print("Tool creation cancelled.")

    except KeyboardInterrupt:
        print("\n\nTool creation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError creating tool: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
