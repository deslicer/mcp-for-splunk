"""
Base classes for MCP tools, resources, and prompts.

Provides consistent interfaces and shared functionality for all MCP components.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from fastmcp import Context
from splunklib import client

logger = logging.getLogger(__name__)


class SplunkContext:
    """Shared context for Splunk operations"""

    def __init__(
        self,
        service: client.Service | None,
        is_connected: bool,
        client_config: dict[str, Any] = None,
    ):
        self.service = service
        self.is_connected = is_connected
        self.client_config = client_config or {}


class BaseTool(ABC):
    """
    Base class for all MCP tools.

    Provides common functionality like error handling, logging, and Splunk connection validation.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def extract_client_config(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Extract Splunk configuration from tool parameters.

        Looks for parameters that start with 'splunk_' and returns them as a dict.
        Also removes them from kwargs to prevent passing to tool logic.

        Args:
            kwargs: Tool parameters that may contain Splunk config

        Returns:
            Dict containing extracted Splunk configuration
        """
        client_config = {}
        splunk_keys = [key for key in list(kwargs.keys()) if key.startswith("splunk_")]

        for key in splunk_keys:
            value = kwargs.pop(key)
            # Ignore unset values to avoid passing None (e.g., int(None)) downstream
            if value is not None:
                client_config[key] = value

        return client_config if client_config else None

    def get_client_config_from_context(self, ctx: Context) -> dict[str, Any] | None:
        """
        Get client configuration from MCP context.

        Checks multiple sources in priority order:
        1. Context state (set by middleware per request)
        2. HTTP request headers (for HTTP transport)
        3. MCP client environment variables (lifespan context)

        Args:
            ctx: MCP context

        Returns:
            Client configuration dict or None
        """
        # Priority 1: Context state (preferred, set by middleware)
        try:
            if hasattr(ctx, "get_state"):
                state_cfg = ctx.get_state("client_config")  # type: ignore[attr-defined]
                if state_cfg:
                    self.logger.info(
                        "Using client config from context state (keys=%s)", list(state_cfg.keys())
                    )
                    return state_cfg
        except Exception as e:
            self.logger.debug("Failed to get client config from context state: %s", e)

        # Priority 2: HTTP headers (using FastMCP runtime dependencies)
        try:
            from fastmcp.server.dependencies import get_http_headers

            headers = get_http_headers(include_all=True)
            if headers:
                self.logger.debug(
                    "Attempting to extract config from HTTP headers (available: %s)",
                    list(headers.keys()),
                )

                # Extract Splunk configuration from headers
                from src.server import extract_client_config_from_headers

                client_config = extract_client_config_from_headers(headers)

                if client_config:
                    self.logger.info(
                        "Using client config from HTTP headers (keys=%s)",
                        list(client_config.keys()),
                    )
                    return client_config
        except Exception as e:
            self.logger.debug("Failed to get client config from HTTP headers: %s", e)

        # Priority 3: Lifespan context (client environment)
        try:
            splunk_ctx = ctx.request_context.lifespan_context
            if hasattr(splunk_ctx, "client_config") and splunk_ctx.client_config:
                self.logger.info("Using client config from environment variables")
                return splunk_ctx.client_config
        except Exception as e:
            self.logger.debug("Failed to get client config from lifespan context: %s", e)

        self.logger.debug("No client config found in any source")
        return None

    async def get_splunk_service(
        self, ctx: Context, tool_level_config: dict[str, Any] | None = None
    ) -> client.Service:
        """
        Get Splunk service connection using client config or fallback to server default.

        Priority order:
        1. Tool-level configuration (passed as parameter)
        2. MCP client configuration (from headers or environment)
        3. Server default connection

        Args:
            ctx: MCP context
            tool_level_config: Optional tool-level Splunk configuration

        Returns:
            Splunk service connection

        Raises:
            Exception: If no connection available and client config doesn't work
        """
        # Priority 1: Tool-level configuration
        if tool_level_config:
            try:
                from src.client.splunk_client import get_splunk_service

                self.logger.info("Using tool-level Splunk configuration")
                return get_splunk_service(tool_level_config)
            except Exception as e:
                self.logger.warning(f"Failed to connect with tool-level config: {e}")

        # Priority 2: MCP client configuration
        client_config = self.get_client_config_from_context(ctx)
        if client_config:
            try:
                from src.client.splunk_client import get_splunk_service

                self.logger.info("Using MCP client configuration")
                return get_splunk_service(client_config)
            except Exception as e:
                self.logger.warning(f"Failed to connect with MCP client config: {e}")

        # Priority 3: Server default connection
        is_available, service, error = self.check_splunk_available(ctx)

        if not is_available:
            raise Exception(f"Splunk connection not available: {error}")

        return service

    def check_splunk_available(self, ctx: Context) -> tuple[bool, client.Service | None, str]:
        """
        Check if Splunk is available and return status.

        Returns:
            Tuple of (is_available, service, error_message)
        """
        splunk_ctx = ctx.request_context.lifespan_context

        # First, prefer per-request client configuration (HTTP headers / client env)
        try:
            client_config = None
            # From HTTP request state (preferred for HTTP transport)
            if (
                hasattr(ctx.request_context, "request")
                and hasattr(ctx.request_context.request, "state")
                and hasattr(ctx.request_context.request.state, "client_config")
            ):
                client_config = ctx.request_context.request.state.client_config
            # Or from lifespan context (set by middleware/cache or client env)
            elif hasattr(splunk_ctx, "client_config") and splunk_ctx.client_config:
                client_config = splunk_ctx.client_config

            if client_config:
                try:
                    from src.client.splunk_client import get_splunk_service

                    service = get_splunk_service(client_config)
                    return True, service, ""
                except Exception as e:
                    # Fall back to server default if client-config connection fails
                    logger.warning(
                        f"Client-config Splunk connection failed in availability check: {e}"
                    )
        except Exception:
            # Ignore header/env extraction issues and continue with server default
            pass

        # Fallback: use server default service established at startup
        if not splunk_ctx.is_connected or not splunk_ctx.service:
            return (
                False,
                None,
                "Splunk service is not available. MCP server is running in degraded mode.",
            )

        return True, splunk_ctx.service, ""

    def format_error_response(self, error: str, **kwargs) -> dict[str, Any]:
        """Format a consistent error response"""
        return {"status": "error", "error": error, **kwargs}

    def format_success_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Format a consistent success response"""
        return {"status": "success", **data}

    @abstractmethod
    async def execute(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Execute the tool's main functionality"""
        pass


class BaseResource(ABC):
    """
    Base class for all MCP resources.

    Resources provide read-only data that can be accessed by MCP clients.
    """

    def __init__(self, uri: str, name: str, description: str, mime_type: str = "text/plain"):
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = mime_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def get_content(self, ctx: Context) -> str:
        """Get the resource content"""
        pass


class BasePrompt(ABC):
    """
    Base class for all MCP prompts.

    Prompts provide templated interactions for common use cases.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def get_prompt(self, ctx: Context, **kwargs) -> dict[str, Any]:
        """Get the prompt content with any dynamic variables filled in"""
        pass


class ToolMetadata:
    """Metadata for tool registration and discovery"""

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        tags: list[str] | None = None,
        requires_connection: bool = True,
        version: str = "1.0.0",
    ):
        self.name = name
        self.description = description
        self.category = category
        self.tags = tags or []
        self.requires_connection = requires_connection
        self.version = version


class ResourceMetadata:
    """Metadata for resource registration and discovery"""

    def __init__(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "text/plain",
        category: str = "general",
        tags: list[str] | None = None,
    ):
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = mime_type
        self.category = category
        self.tags = tags or []


class PromptMetadata:
    """Metadata for prompt registration and discovery"""

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        tags: list[str] | None = None,
        arguments: list[dict[str, Any]] | None = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.tags = tags or []
        self.arguments = arguments or []
