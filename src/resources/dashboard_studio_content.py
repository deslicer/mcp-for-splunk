"""
Load Dashboard Studio reference content for MCP tools and resources.

The cheatsheet is authored at docs/reference/dashboard_studio_cheatsheet.md.
That file is bundled into the wheel at build time for Docker and pip installs.
"""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path

logger = logging.getLogger(__name__)

CHEATSHEET_FILENAME = "dashboard_studio_cheatsheet.md"
CHEATSHEET_SOURCE_PATH = f"docs/reference/{CHEATSHEET_FILENAME}"
BUNDLED_DOCS_PACKAGE = "src.bundled_docs"


class DashboardStudioContentError(Exception):
    """Raised when Dashboard Studio reference content cannot be loaded."""


def cheatsheet_edit_path() -> Path:
    """Return the repo-relative path where the cheatsheet should be edited."""
    return Path(__file__).resolve().parents[2] / "docs" / "reference" / CHEATSHEET_FILENAME


def load_cheatsheet_markdown() -> str:
    """
    Load the Dashboard Studio cheatsheet markdown.

    Resolution order:
    1. docs/reference/dashboard_studio_cheatsheet.md (local repo / bind-mounted dev tree)
    2. src/bundled_docs/dashboard_studio_cheatsheet.md (packaged wheel install)
    """
    dev_path = cheatsheet_edit_path()
    if dev_path.exists():
        logger.debug("Loading Dashboard Studio cheatsheet from %s", dev_path)
        return dev_path.read_text(encoding="utf-8")

    try:
        bundled_path = resources.files(BUNDLED_DOCS_PACKAGE).joinpath(CHEATSHEET_FILENAME)
        content = bundled_path.read_text(encoding="utf-8")
        logger.debug("Loading Dashboard Studio cheatsheet from bundled package")
        return content
    except (FileNotFoundError, ModuleNotFoundError, TypeError, OSError) as exc:
        raise DashboardStudioContentError(
            "Dashboard Studio cheatsheet is unavailable. "
            f"Edit {CHEATSHEET_SOURCE_PATH} in the repository and rebuild or reinstall the MCP server."
        ) from exc
