"""Single source of truth for the package version.

The version lives in ``packaging/mcp-itsi-server/pyproject.toml`` and is
read here at import time via :func:`importlib.metadata.version` so that
release-please only has to update one file. We previously kept a literal
``__version__`` string here too and asked release-please to update it via
``extra-files``, but the package lives at ``packaging/mcp-itsi-server``
while the source tree lives at the repo root, and release-please rejects
``..`` traversal in extra-file paths (``illegal pathing characters``).

When running directly from a source checkout where the distribution
metadata isn't installed yet (e.g. ``python -m mcp_itsi`` before
``uv sync --extra itsi``), we fall back to a clearly-fake version rather
than raising on import.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _distribution_version

_DISTRIBUTION_NAME = "mcp-itsi-server"
_FALLBACK_VERSION = "0.0.0+local"

try:
    __version__ = _distribution_version(_DISTRIBUTION_NAME)
except PackageNotFoundError:
    __version__ = _FALLBACK_VERSION
