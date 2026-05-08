"""Glue code that registers ITSI tools/resources/prompts with FastMCP.

The shape of this module mirrors the modular registration approach used in
``mcp-for-splunk`` so operators familiar with the parent project will feel
at home.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Iterable
from typing import Any

from fastmcp import Context, FastMCP

from mcp_itsi.core.base import (
    BaseITSIPrompt,
    BaseITSIResource,
    BaseITSITool,
    PromptMetadata,
    ResourceMetadata,
    ToolMetadata,
)

logger = logging.getLogger(__name__)


def _tags_as_set(tags: tuple[str, ...] | None) -> set[str]:
    """Coerce a metadata ``tags`` tuple into the ``set`` FastMCP expects."""
    return set(tags) if tags else set()


def register_tools(mcp: FastMCP, tool_classes: Iterable[type[BaseITSITool]]) -> int:
    """Register every tool class with the given MCP server."""
    count = 0
    for tool_cls in tool_classes:
        try:
            instance = tool_cls()
            metadata: ToolMetadata = tool_cls.METADATA
            wrapper = _build_tool_wrapper(instance, metadata)
            mcp.tool(
                name=metadata.name,
                description=metadata.description,
                tags=_tags_as_set(metadata.tags),
            )(wrapper)
            count += 1
        except Exception:
            logger.exception("Failed to register tool %s", tool_cls.__name__)
    logger.info("Registered %d ITSI tools", count)
    return count


def register_resources(mcp: FastMCP, resource_classes: Iterable[type[BaseITSIResource]]) -> int:
    count = 0
    for res_cls in resource_classes:
        try:
            instance = res_cls()
            metadata: ResourceMetadata = res_cls.METADATA
            handler = _build_resource_handler(instance)
            mcp.resource(
                metadata.uri,
                name=metadata.name,
                description=metadata.description,
                mime_type=metadata.mime_type,
                tags=_tags_as_set(metadata.tags),
            )(handler)
            count += 1
        except Exception:
            logger.exception("Failed to register resource %s", res_cls.__name__)
    logger.info("Registered %d ITSI resources", count)
    return count


def register_prompts(mcp: FastMCP, prompt_classes: Iterable[type[BaseITSIPrompt]]) -> int:
    count = 0
    for prompt_cls in prompt_classes:
        try:
            instance = prompt_cls()
            metadata: PromptMetadata = prompt_cls.METADATA
            wrapper = _build_prompt_wrapper(instance, metadata)
            mcp.prompt(
                name=metadata.name,
                description=metadata.description,
                tags=_tags_as_set(metadata.tags),
            )(wrapper)
            count += 1
        except Exception:
            logger.exception("Failed to register prompt %s", prompt_cls.__name__)
    logger.info("Registered %d ITSI prompts", count)
    return count


def _build_tool_wrapper(instance: BaseITSITool, metadata: ToolMetadata) -> Callable[..., Any]:
    """Wrap ``instance.__call__`` with a FastMCP-friendly signature."""
    sig = inspect.signature(instance.execute)
    params = [p for name, p in sig.parameters.items() if name not in {"self", "mcp_ctx", "ctx"}]
    new_params = [
        inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Context),
        *params,
    ]
    new_sig = inspect.Signature(new_params)

    async def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        bound = new_sig.bind(*args, **kwargs)
        bound.apply_defaults()
        ctx = bound.arguments.pop("ctx")
        return await instance(ctx, **bound.arguments)

    wrapper.__name__ = metadata.name
    wrapper.__doc__ = metadata.description
    wrapper.__signature__ = new_sig  # type: ignore[attr-defined]
    wrapper.__annotations__ = {
        p.name: p.annotation for p in new_params if p.annotation is not inspect.Parameter.empty
    }
    return wrapper


def _build_resource_handler(instance: BaseITSIResource) -> Callable[[], Any]:
    async def handler() -> str:
        from fastmcp.server.dependencies import get_context

        ctx = get_context()
        return await instance.read(ctx)

    handler.__name__ = f"resource_{instance.METADATA.name.replace(' ', '_').lower()}"
    handler.__doc__ = instance.METADATA.description
    return handler


def _build_prompt_wrapper(instance: BaseITSIPrompt, metadata: PromptMetadata) -> Callable[..., Any]:
    sig = inspect.signature(instance.render)
    params = [p for name, p in sig.parameters.items() if name not in {"self", "mcp_ctx"}]

    async def wrapper(**kwargs: Any) -> str:
        from fastmcp.server.dependencies import get_context

        ctx = get_context()
        return await instance.render(ctx, **kwargs)

    wrapper.__name__ = metadata.name
    wrapper.__doc__ = metadata.description
    wrapper.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    annotations: dict[str, Any] = {}
    for p in params:
        if p.annotation is not inspect.Parameter.empty:
            annotations[p.name] = p.annotation
    annotations["return"] = str
    wrapper.__annotations__ = annotations
    return wrapper
