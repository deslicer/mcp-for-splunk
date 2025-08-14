#!/usr/bin/env python3
"""
Tool Validator for MCP Server for Splunk Contributors

This script validates contrib tools for compliance with project guidelines.
"""

import ast
import sys
from pathlib import Path


class ToolValidator:
    """Validates tools against project guidelines."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def validate_tool(self, tool_file: Path) -> dict[str, list[str]]:
        """Validate a single tool file."""
        self.errors = []
        self.warnings = []
        self.info = []

        if not tool_file.exists():
            self.errors.append(f"Tool file does not exist: {tool_file}")
            return self._get_results()

        try:
            with open(tool_file) as f:
                content = f.read()
        except Exception as e:
            self.errors.append(f"Cannot read tool file: {e}")
            return self._get_results()

        # Parse the AST
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            self.errors.append(f"Syntax error in tool file: {e}")
            return self._get_results()

        # Validate various aspects
        self._validate_imports(tree, content)
        self._validate_class_structure(tree, content)
        self._validate_metadata(tree, content)
        self._validate_execute_method(tree, content)
        self._validate_naming_conventions(tool_file, tree)
        self._validate_documentation(tree, content)
        self._validate_error_handling(tree, content)
        self._validate_test_file(tool_file)

        return self._get_results()

    def _get_results(self) -> dict[str, list[str]]:
        """Get validation results."""
        return {"errors": self.errors, "warnings": self.warnings, "info": self.info}

    def _validate_imports(self, tree: ast.AST, content: str):
        """Validate required imports."""
        # Check for essential imports (more flexible)
        import_checks = [
            ("typing", "Any and Dict types"),
            ("fastmcp", "Context"),
            ("src.core.base", "BaseTool and ToolMetadata"),
        ]

        for module, description in import_checks:
            if f"from {module} import" not in content and f"import {module}" not in content:
                self.errors.append(f"Missing required import from {module} ({description})")

        # Check for proper import organization
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                imports.append(node)

        if not imports:
            self.warnings.append("No imports found - this might be incorrect")

    def _validate_class_structure(self, tree: ast.AST, content: str):
        """Validate class structure."""
        tool_classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if it inherits from BaseTool
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseTool":
                        tool_classes.append(node)
                        break

        if not tool_classes:
            self.errors.append("No class inheriting from BaseTool found")
            return

        if len(tool_classes) > 1:
            self.warnings.append(
                f"Multiple BaseTool classes found: {[cls.name for cls in tool_classes]}"
            )

        # Validate the main tool class
        main_class = tool_classes[0]

        # Check class name ends with 'Tool'
        if not main_class.name.endswith("Tool"):
            self.warnings.append(f"Class name '{main_class.name}' should end with 'Tool'")

        # Check for docstring
        if not ast.get_docstring(main_class):
            self.warnings.append(f"Class '{main_class.name}' missing docstring")

    def _validate_metadata(self, tree: ast.AST, content: str):
        """Validate METADATA attribute."""
        has_metadata = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "METADATA":
                        has_metadata = True
                        break

        if not has_metadata:
            self.errors.append("Missing METADATA class attribute")
            return

        # Check metadata structure
        required_metadata_fields = ["name", "description", "category"]
        for field in required_metadata_fields:
            if f"{field}=" not in content:
                self.warnings.append(f"METADATA might be missing '{field}' field")

        # Check category validity
        valid_categories = ["examples", "security", "devops", "analytics"]
        category_found = False
        for category in valid_categories:
            if f'category="{category}"' in content:
                category_found = True
                break

        if not category_found:
            self.warnings.append(f"METADATA category should be one of: {valid_categories}")

    def _validate_execute_method(self, tree: ast.AST, content: str):
        """Validate execute method."""
        execute_methods = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "execute":
                execute_methods.append(node)

        if not execute_methods:
            self.errors.append("Missing execute method")
            return

        if len(execute_methods) > 1:
            self.warnings.append("Multiple execute methods found")

        execute_method = execute_methods[0]

        # Check method signature
        args = execute_method.args.args
        if len(args) < 2:  # self, ctx
            self.errors.append("execute method must have at least (self, ctx) parameters")
        elif args[1].arg != "ctx":
            self.warnings.append("Second parameter should be named 'ctx'")

        # Check for async
        if not isinstance(execute_method, ast.AsyncFunctionDef):
            self.errors.append("execute method must be async")

        # Check return type annotation
        if not execute_method.returns:
            self.warnings.append("execute method should have return type annotation")

        # Check for docstring
        if not ast.get_docstring(execute_method):
            self.warnings.append("execute method missing docstring")

    def _validate_naming_conventions(self, tool_file: Path, tree: ast.AST):
        """Validate naming conventions."""
        # File name should be snake_case
        filename = tool_file.stem
        if not filename.islower() or "-" in filename:
            self.warnings.append(f"File name '{filename}' should be snake_case")

        # Find the main class
        tool_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseTool":
                        tool_classes.append(node)
                        break

        if tool_classes:
            class_name = tool_classes[0].name
            # Class should be PascalCase
            if not class_name[0].isupper():
                self.warnings.append(f"Class name '{class_name}' should be PascalCase")

    def _validate_documentation(self, tree: ast.AST, content: str):
        """Validate documentation."""
        # Check for module docstring
        module_docstring = ast.get_docstring(tree)
        if not module_docstring:
            self.warnings.append("Module missing docstring")

        # Check for type hints
        if "typing" not in content:
            self.warnings.append("Consider adding type hints")

        # Check for TODO comments
        todo_count = content.count("TODO")
        if todo_count > 5:
            self.warnings.append(
                f"Many TODO comments found ({todo_count}) - consider completing implementation"
            )

    def _validate_error_handling(self, tree: ast.AST, content: str):
        """Validate error handling."""
        has_try_except = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                has_try_except = True
                break

        if not has_try_except:
            self.warnings.append("No try-except blocks found - consider adding error handling")

        # Check for proper error response formatting
        if "format_error_response" not in content:
            self.warnings.append(
                "Consider using format_error_response for consistent error handling"
            )

        if "format_success_response" not in content:
            self.warnings.append(
                "Consider using format_success_response for consistent response formatting"
            )

    def _validate_test_file(self, tool_file: Path):
        """Validate corresponding test file."""
        # Construct expected test file path
        tool_path_str = str(tool_file)
        test_path_str = tool_path_str.replace("contrib/tools/", "tests/contrib/")
        test_path_str = test_path_str.replace(tool_file.name, f"test_{tool_file.name}")
        test_file = Path(test_path_str)

        if not test_file.exists():
            self.warnings.append(f"No test file found at: {test_file}")
            return

        try:
            with open(test_file) as f:
                test_content = f.read()

            # Basic test validation
            if "pytest" not in test_content:
                self.warnings.append("Test file should use pytest")

            if "@pytest.mark.asyncio" not in test_content:
                self.warnings.append(
                    "Test file should include async tests with @pytest.mark.asyncio"
                )

            if "def test_" not in test_content:
                self.warnings.append("Test file should contain test methods (def test_*)")

        except Exception as e:
            self.warnings.append(f"Could not read test file: {e}")


def validate_all_tools(contrib_dir: Path) -> dict[str, dict[str, list[str]]]:
    """Validate all tools in contrib directory."""
    validator = ToolValidator()
    results = {}

    tools_dir = contrib_dir / "tools"
    if not tools_dir.exists():
        return results

    for category_dir in tools_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        for tool_file in category_dir.iterdir():
            if (
                tool_file.is_file()
                and tool_file.suffix == ".py"
                and not tool_file.name.startswith("_")
            ):
                tool_key = f"{category_dir.name}/{tool_file.name}"
                results[tool_key] = validator.validate_tool(tool_file)

    return results


def print_validation_results(results: dict[str, dict[str, list[str]]]):
    """Print validation results."""
    print("=" * 80)
    print("MCP Server for Splunk - Tool Validation Results")
    print("=" * 80)

    total_tools = len(results)
    tools_with_errors = sum(1 for r in results.values() if r["errors"])
    tools_with_warnings = sum(1 for r in results.values() if r["warnings"])

    print(f"\nValidated {total_tools} tools:")
    print(f"  • {total_tools - tools_with_errors} tools passed validation")
    print(f"  • {tools_with_errors} tools with errors")
    print(f"  • {tools_with_warnings} tools with warnings")

    for tool_name, result in results.items():
        errors = result["errors"]
        warnings = result["warnings"]
        info = result["info"]

        if errors or warnings:
            print(f"\n📁 {tool_name}")
            print("-" * 50)

            if errors:
                print("❌ ERRORS:")
                for error in errors:
                    print(f"   • {error}")

            if warnings:
                print("⚠️  WARNINGS:")
                for warning in warnings:
                    print(f"   • {warning}")

            if info:
                print("ℹ️  INFO:")
                for i in info:
                    print(f"   • {i}")
        else:
            print(f"✅ {tool_name} - All checks passed")


def main():
    """Main function."""
    # Determine project structure
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    contrib_dir = project_root / "contrib"

    if not contrib_dir.exists():
        print("Error: contrib directory not found")
        sys.exit(1)

    # Parse command line arguments
    if len(sys.argv) == 1:
        # Validate all tools
        results = validate_all_tools(contrib_dir)
        print_validation_results(results)
    elif len(sys.argv) == 2:
        if sys.argv[1] == "--help":
            print("Usage:")
            print("  python validate_tools.py              - Validate all tools")
            print("  python validate_tools.py <tool_path>  - Validate specific tool")
            print("  python validate_tools.py --help       - Show this help")
        else:
            # Validate specific tool
            tool_path = Path(sys.argv[1])
            validator = ToolValidator()
            result = validator.validate_tool(tool_path)

            print(f"Validation results for: {tool_path}")
            print("=" * 60)

            if result["errors"]:
                print("❌ ERRORS:")
                for error in result["errors"]:
                    print(f"   • {error}")

            if result["warnings"]:
                print("⚠️  WARNINGS:")
                for warning in result["warnings"]:
                    print(f"   • {warning}")

            if not result["errors"] and not result["warnings"]:
                print("✅ All checks passed!")
    else:
        print("Invalid arguments. Use --help for usage information.")


if __name__ == "__main__":
    main()
