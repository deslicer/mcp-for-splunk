#!/usr/bin/env python3
"""
Test Runner for MCP Server for Splunk Contributors

This script runs tests for contrib tools with helpful output and filtering.
"""

import subprocess
import sys
from pathlib import Path


def find_test_files(contrib_dir: Path, category: str | None = None) -> list[Path]:
    """Find test files for contrib tools."""
    test_files = []

    # Base test directory for contrib
    test_base = contrib_dir.parent / "tests" / "contrib"

    if not test_base.exists():
        return test_files

    if category:
        # Look for tests in specific category
        category_dir = test_base / category
        if category_dir.exists():
            for test_file in category_dir.iterdir():
                if test_file.is_file() and test_file.name.startswith('test_') and test_file.suffix == '.py':
                    test_files.append(test_file)
    else:
        # Find all contrib test files
        for category_dir in test_base.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('.'):
                for test_file in category_dir.iterdir():
                    if test_file.is_file() and test_file.name.startswith('test_') and test_file.suffix == '.py':
                        test_files.append(test_file)

    return sorted(test_files)


def run_pytest(test_files: list[Path], verbose: bool = False, coverage: bool = False) -> int:
    """Run pytest on the specified test files."""
    if not test_files:
        print("No test files found to run.")
        return 0

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    if coverage:
        cmd.extend(["--cov=contrib", "--cov-report=term-missing"])

    # Add test files
    cmd.extend([str(f) for f in test_files])

    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, cwd=Path.cwd())
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        return 130
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def list_test_files(contrib_dir: Path):
    """List available test files."""
    test_files = find_test_files(contrib_dir)

    if not test_files:
        print("No contrib test files found.")
        return

    print("Available contrib test files:")
    print("=" * 50)

    # Group by category
    by_category = {}
    test_base = contrib_dir.parent / "tests" / "contrib"

    for test_file in test_files:
        # Extract category from path
        rel_path = test_file.relative_to(test_base)
        category = rel_path.parts[0] if len(rel_path.parts) > 1 else "unknown"

        if category not in by_category:
            by_category[category] = []
        by_category[category].append(test_file)

    for category, files in sorted(by_category.items()):
        print(f"\n📁 {category.upper()}:")
        for test_file in files:
            print(f"  • {test_file.name}")


def check_test_environment():
    """Check if the test environment is set up correctly."""
    import importlib.util

    issues = []

    # Check if pytest is available
    try:
        subprocess.run(["python", "-m", "pytest", "--version"],
                      capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("pytest is not installed or not available")

    # Check if we can import required modules
    if importlib.util.find_spec("fastmcp") is None:
        issues.append("fastmcp module not available")

    if importlib.util.find_spec("src.core.base") is None:
        issues.append("src.core.base module not available - run from project root")

    if issues:
        print("❌ Test environment issues:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    else:
        print("✅ Test environment looks good")
        return True


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
        # Run all contrib tests
        if not check_test_environment():
            sys.exit(1)

        test_files = find_test_files(contrib_dir)
        if not test_files:
            print("No contrib test files found. Use 'python generate_tool.py' to create tools with tests.")
            sys.exit(0)

        exit_code = run_pytest(test_files)
        sys.exit(exit_code)

    elif len(sys.argv) == 2:
        arg = sys.argv[1]

        if arg == '--help':
            print("Usage:")
            print("  python test_contrib.py                    - Run all contrib tests")
            print("  python test_contrib.py --list             - List available test files")
            print("  python test_contrib.py --verbose          - Run tests with verbose output")
            print("  python test_contrib.py --coverage         - Run tests with coverage report")
            print("  python test_contrib.py --check            - Check test environment")
            print("  python test_contrib.py <category>         - Run tests for specific category")
            print("  python test_contrib.py --help             - Show this help")

        elif arg == '--list':
            list_test_files(contrib_dir)

        elif arg == '--check':
            if check_test_environment():
                print("Environment is ready for testing.")
            else:
                sys.exit(1)

        elif arg == '--verbose':
            if not check_test_environment():
                sys.exit(1)
            test_files = find_test_files(contrib_dir)
            exit_code = run_pytest(test_files, verbose=True)
            sys.exit(exit_code)

        elif arg == '--coverage':
            if not check_test_environment():
                sys.exit(1)
            test_files = find_test_files(contrib_dir)
            exit_code = run_pytest(test_files, coverage=True)
            sys.exit(exit_code)

        else:
            # Assume it's a category name
            if not check_test_environment():
                sys.exit(1)

            category = arg
            test_files = find_test_files(contrib_dir, category)

            if not test_files:
                print(f"No test files found for category: {category}")
                print("Available categories:")
                all_files = find_test_files(contrib_dir)
                test_base = contrib_dir.parent / "tests" / "contrib"
                categories = set()
                for test_file in all_files:
                    rel_path = test_file.relative_to(test_base)
                    if len(rel_path.parts) > 1:
                        categories.add(rel_path.parts[0])
                for cat in sorted(categories):
                    print(f"  • {cat}")
                sys.exit(1)

            exit_code = run_pytest(test_files)
            sys.exit(exit_code)

    else:
        print("Invalid arguments. Use --help for usage information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
