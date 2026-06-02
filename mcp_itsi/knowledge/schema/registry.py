"""Load and serve bundled ITSI object schemas.

The registry lazily loads the generated ``data/*.json`` files once and exposes
lookup, listing and search. A module-level :data:`registry` instance is shared
across tools.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from functools import cached_property
from pathlib import Path

from mcp_itsi.knowledge.schema.models import ObjectSchema

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "data"
_INDEX_FILE = "index.json"


class SchemaRegistry:
    """In-memory store of parsed ITSI object schemas (manager)."""

    def __init__(self, data_dir: Path = _DATA_DIR) -> None:
        self._data_dir = data_dir

    @cached_property
    def _schemas(self) -> dict[str, ObjectSchema]:
        schemas: dict[str, ObjectSchema] = {}
        if not self._data_dir.is_dir():
            logger.warning("Schema data dir missing: %s", self._data_dir)
            return schemas
        for path in sorted(self._data_dir.glob("*.json")):
            if path.name == _INDEX_FILE:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                schema = ObjectSchema.from_dict(data)
                schemas[schema.slug] = schema
            except (OSError, ValueError, KeyError):
                logger.exception("Failed to load schema file %s", path)
        return schemas

    @cached_property
    def index(self) -> dict:
        path = self._data_dir / _INDEX_FILE
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("Schema index missing or invalid: %s", path)
            return {}

    def get(self, slug: str) -> ObjectSchema | None:
        """Look up a schema by slug or object_type id (case-insensitive)."""
        if not slug:
            return None
        direct = self._schemas.get(slug)
        if direct is not None:
            return direct
        lowered = slug.lower()
        for schema in self._schemas.values():
            if schema.slug.lower() == lowered or (
                schema.object_type and schema.object_type.lower() == lowered
            ):
                return schema
        return None

    def list_object_types(self) -> list[ObjectSchema]:
        return sorted(
            (s for s in self._schemas.values() if s.kind == "object"),
            key=lambda s: s.slug,
        )

    def list_all(self) -> list[ObjectSchema]:
        return sorted(self._schemas.values(), key=lambda s: s.slug)

    def known_slugs(self) -> Iterable[str]:
        return self._schemas.keys()

    def search(self, query: str, *, limit: int = 20) -> list[ObjectSchema]:
        q = query.strip().lower()
        if not q:
            return []
        scored: list[tuple[int, ObjectSchema]] = []
        for schema in self._schemas.values():
            haystack = " ".join(
                [schema.slug, schema.title, schema.description]
                + [a.name for a in schema.attributes]
            ).lower()
            score = haystack.count(q)
            if score:
                scored.append((score, schema))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:limit]]


registry = SchemaRegistry()
