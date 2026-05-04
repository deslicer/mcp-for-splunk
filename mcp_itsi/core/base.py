"""Base classes for ITSI tools, resources and prompts.

These classes are intentionally small and follow the single-responsibility
principle: each subclass implements one logical operation against a single
ITSI object type or workflow.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from fastmcp import Context

from mcp_itsi.client.http_client import ITSIError
from mcp_itsi.core.context import ITSICallContext, build_call_context
from mcp_itsi.core.responses import error_response

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolMetadata:
    name: str
    description: str
    category: str
    tags: tuple[str, ...] = ()
    requires_connection: bool = True


@dataclass(frozen=True)
class ResourceMetadata:
    uri: str
    name: str
    description: str
    mime_type: str = "text/markdown"
    category: str = "itsi"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromptMetadata:
    name: str
    description: str
    category: str = "itsi"
    tags: tuple[str, ...] = ()


class BaseITSITool(ABC):
    """Common scaffolding for ITSI tools.

    Concrete subclasses implement :meth:`execute` and define a class-level
    :attr:`METADATA` of type :class:`ToolMetadata`.
    """

    METADATA: ToolMetadata

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"mcp_itsi.tools.{self.METADATA.name}")

    async def __call__(self, ctx: Context, **kwargs: Any) -> dict[str, Any]:
        if self.METADATA.requires_connection:
            try:
                call_ctx = build_call_context(ctx)
            except ValueError as exc:
                self.logger.warning("Bad request configuration: %s", exc)
                return error_response(str(exc))
        else:
            call_ctx = None  # type: ignore[assignment]

        try:
            return await self.execute(ctx, call_ctx, **kwargs)
        except ITSIError as exc:
            self.logger.warning(
                "ITSI API error in %s: %s (status=%s)",
                self.METADATA.name,
                exc,
                exc.status_code,
            )
            return error_response(str(exc), status_code=exc.status_code, body=exc.body)
        except Exception as exc:  # noqa: BLE001 -- we surface to the caller
            self.logger.exception("Unhandled error in tool %s", self.METADATA.name)
            return error_response(f"{type(exc).__name__}: {exc}")

    @abstractmethod
    async def execute(
        self,
        mcp_ctx: Context,
        ctx: ITSICallContext | None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:  # pragma: no cover - abstract
        """Run the tool's main logic. ``ctx`` is request-scoped.

        ``ctx`` is ``None`` for tools whose ``METADATA.requires_connection``
        is ``False`` (e.g. read-only docs tools).

        Subclasses are free to declare additional named parameters; the
        ``*args`` / ``**kwargs`` here keeps overrides Liskov-compatible from
        a static-analysis standpoint while preserving descriptive signatures
        on each concrete tool.
        """


class BaseITSIResource(ABC):
    """Base class for read-only ITSI resources (URI-addressable)."""

    METADATA: ResourceMetadata

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"mcp_itsi.resources.{self.METADATA.uri}")

    @abstractmethod
    async def read(self, mcp_ctx: Context) -> str:  # pragma: no cover - abstract
        ...


class BaseITSIPrompt(ABC):
    """Base class for ITSI prompts."""

    METADATA: PromptMetadata

    def __init__(self) -> None:
        self.logger = logging.getLogger(f"mcp_itsi.prompts.{self.METADATA.name}")

    @abstractmethod
    async def render(self, mcp_ctx: Context, **kwargs: Any) -> str:  # pragma: no cover
        ...
