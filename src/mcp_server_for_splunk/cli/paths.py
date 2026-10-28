"""Locate a source checkout without treating site-packages as a workspace."""

from pathlib import Path


def source_checkout() -> Path | None:
    package = Path(__file__).resolve().parents[1]
    if package.parent.name == "src" and (package.parent.parent / "pyproject.toml").is_file():
        return package.parent.parent
    return None


def working_directory() -> Path:
    return source_checkout() or Path.cwd()
