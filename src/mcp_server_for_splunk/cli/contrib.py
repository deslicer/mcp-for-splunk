"""Entrypoints for contributor commands that require a source checkout."""

import sys
from importlib import import_module

from .paths import source_checkout


def _run(module: str) -> int:
    checkout = source_checkout()
    if checkout is None:
        print(
            "Contributor commands require a source checkout; run uv sync there first.",
            file=sys.stderr,
        )
        return 2
    if str(checkout) not in sys.path:
        sys.path.insert(0, str(checkout))
    result = import_module(module).main()
    return 0 if result is None else int(result)


def generate_tool() -> int:
    return _run("contrib.scripts.generate_tool")


def validate_tools() -> int:
    return _run("contrib.scripts.validate_tools")
