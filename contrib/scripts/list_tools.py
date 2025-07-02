#!/usr/bin/env python3
"""
Tool Browser for MCP Server for Splunk Contributors

This script helps contributors explore existing tools and their structure.
"""

import sys
from pathlib import Path


def find_tools(contrib_dir: Path) -> dict[str, list[dict]]:
    """Find all tools in the contrib directory."""
    tools_by_category = {}

    tools_dir = contrib_dir / "tools"
    if not tools_dir.exists():
        return tools_by_category

    for category_dir in tools_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        category = category_dir.name
        tools_by_category[category] = []

        for tool_file in category_dir.iterdir():
            if (
                tool_file.is_file()
                and tool_file.suffix == ".py"
                and not tool_file.name.startswith("_")
            ):
                tool_info = analyze_tool_file(tool_file)
                if tool_info:
                    tools_by_category[category].append(tool_info)

    return tools_by_category


def analyze_tool_file(tool_file: Path) -> dict | None:
    """Analyze a tool file to extract information."""
    try:
        # Read the file content
        with open(tool_file) as f:
            content = f.read()

        # Extract basic info
        tool_info = {
            "file": tool_file.name,
            "path": str(tool_file),
            "name": tool_file.stem,
            "description": "",
            "class_name": "",
            "metadata": {},
            "has_metadata": False,
            "has_tests": False,
        }

        # Try to find class definition
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()

            # Find class definition
            if line.startswith("class ") and "BaseTool" in line:
                tool_info["class_name"] = line.split("(")[0].replace("class ", "").strip()

            # Find docstring
            if '"""' in line and not tool_info["description"]:
                # Try to extract docstring
                if line.count('"""') == 2:
                    # Single line docstring
                    tool_info["description"] = line.split('"""')[1].strip()
                else:
                    # Multi-line docstring
                    for j in range(i + 1, len(lines)):
                        if '"""' in lines[j]:
                            tool_info["description"] = lines[i + 1].strip()
                            break

        # Check for metadata
        if "METADATA = ToolMetadata(" in content:
            tool_info["has_metadata"] = True
            # Try to extract metadata details
            try:
                metadata_start = content.find("METADATA = ToolMetadata(")
                metadata_end = content.find(")", metadata_start)
                if metadata_start != -1 and metadata_end != -1:
                    metadata_text = content[metadata_start : metadata_end + 1]
                    # Basic parsing - this could be improved
                    if "requires_connection=" in metadata_text:
                        if "requires_connection=True" in metadata_text:
                            tool_info["metadata"]["requires_connection"] = True
                        elif "requires_connection=False" in metadata_text:
                            tool_info["metadata"]["requires_connection"] = False
            except Exception:
                pass

        # Check for corresponding test file
        test_file = Path(
            str(tool_file)
            .replace("contrib/tools/", "tests/contrib/")
            .replace(".py", "")
            .replace(tool_file.name, f"test_{tool_file.name}")
        )
        tool_info["has_tests"] = test_file.exists()

        return tool_info

    except Exception as e:
        print(f"Warning: Could not analyze {tool_file}: {e}")
        return None


def print_tools_summary(tools_by_category: dict[str, list[dict]]):
    """Print a summary of all tools."""
    print("=" * 80)
    print("MCP Server for Splunk - Contrib Tools Summary")
    print("=" * 80)

    total_tools = sum(len(tools) for tools in tools_by_category.values())
    print(f"\nFound {total_tools} tools across {len(tools_by_category)} categories:\n")

    for category, tools in tools_by_category.items():
        if not tools:
            continue

        print(f"📁 {category.upper()} ({len(tools)} tools)")
        print("-" * 50)

        for tool in tools:
            status_indicators = []
            if tool["has_metadata"]:
                status_indicators.append("✓ Metadata")
            if tool["has_tests"]:
                status_indicators.append("✓ Tests")
            if tool["metadata"].get("requires_connection") is False:
                status_indicators.append("🔌 No Splunk required")
            elif tool["metadata"].get("requires_connection") is True:
                status_indicators.append("🔌 Splunk required")

            status = " | ".join(status_indicators) if status_indicators else "⚠️  Incomplete"

            print(f"  • {tool['name']}")
            print(f"    Class: {tool['class_name']}")
            if tool["description"]:
                print(f"    Description: {tool['description']}")
            print(f"    Status: {status}")
            print()


def print_tool_details(tool_path: str):
    """Print detailed information about a specific tool."""
    tool_file = Path(tool_path)
    if not tool_file.exists():
        print(f"Error: Tool file not found: {tool_path}")
        return

    tool_info = analyze_tool_file(tool_file)
    if not tool_info:
        print(f"Error: Could not analyze tool file: {tool_path}")
        return

    print("=" * 80)
    print(f"Tool Details: {tool_info['name']}")
    print("=" * 80)

    print(f"File: {tool_info['file']}")
    print(f"Path: {tool_info['path']}")
    print(f"Class: {tool_info['class_name']}")
    print(f"Description: {tool_info['description']}")
    print(f"Has Metadata: {'Yes' if tool_info['has_metadata'] else 'No'}")
    print(f"Has Tests: {'Yes' if tool_info['has_tests'] else 'No'}")

    if tool_info["metadata"]:
        print("\nMetadata:")
        for key, value in tool_info["metadata"].items():
            print(f"  {key}: {value}")

    # Show file content preview
    print("\nFile Preview (first 20 lines):")
    print("-" * 40)
    try:
        with open(tool_file) as f:
            for i, line in enumerate(f, 1):
                if i > 20:
                    print("... (truncated)")
                    break
                print(f"{i:2d}: {line.rstrip()}")
    except Exception as e:
        print(f"Error reading file: {e}")


def interactive_browser(tools_by_category: dict[str, list[dict]]):
    """Interactive tool browser."""
    while True:
        print("\n" + "=" * 60)
        print("Interactive Tool Browser")
        print("=" * 60)
        print("Commands:")
        print("  list         - List all tools")
        print("  category     - Browse by category")
        print("  detail <path> - Show tool details")
        print("  help         - Show this help")
        print("  quit         - Exit browser")

        choice = input("\nEnter command: ").strip().lower()

        if choice == "quit":
            break
        elif choice == "list":
            print_tools_summary(tools_by_category)
        elif choice == "category":
            print("\nAvailable categories:")
            for i, category in enumerate(tools_by_category.keys(), 1):
                print(f"  {i}. {category} ({len(tools_by_category[category])} tools)")

            try:
                cat_choice = int(input("\nSelect category number: ")) - 1
                categories = list(tools_by_category.keys())
                if 0 <= cat_choice < len(categories):
                    selected_category = categories[cat_choice]
                    tools = tools_by_category[selected_category]

                    print(f"\nTools in '{selected_category}':")
                    for i, tool in enumerate(tools, 1):
                        print(f"  {i}. {tool['name']} - {tool['description']}")
                else:
                    print("Invalid category number.")
            except ValueError:
                print("Please enter a valid number.")

        elif choice.startswith("detail "):
            tool_path = choice[7:].strip()
            print_tool_details(tool_path)
        elif choice == "help":
            continue
        else:
            print("Unknown command. Type 'help' for available commands.")


def main():
    """Main function."""
    # Determine project structure
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    contrib_dir = project_root / "contrib"

    if not contrib_dir.exists():
        print("Error: contrib directory not found")
        sys.exit(1)

    # Find all tools
    tools_by_category = find_tools(contrib_dir)

    if not tools_by_category:
        print("No tools found in contrib/tools/")
        sys.exit(0)

    # Parse command line arguments
    if len(sys.argv) == 1:
        # Default: show summary
        print_tools_summary(tools_by_category)
    elif len(sys.argv) == 2:
        if sys.argv[1] == "--interactive":
            interactive_browser(tools_by_category)
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python list_tools.py                    - Show tools summary")
            print("  python list_tools.py --interactive      - Interactive browser")
            print("  python list_tools.py --detail <path>    - Show tool details")
            print("  python list_tools.py --help             - Show this help")
        else:
            print("Unknown option. Use --help for usage information.")
    elif len(sys.argv) == 3 and sys.argv[1] == "--detail":
        print_tool_details(sys.argv[2])
    else:
        print("Invalid arguments. Use --help for usage information.")


if __name__ == "__main__":
    main()
