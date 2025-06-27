"""
Base classes for MCP tools, resources, and prompts.

Provides consistent interfaces and shared functionality for all MCP components.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from fastmcp import Context
from splunklib import client

logger = logging.getLogger(__name__)


class SplunkContext:
    """Shared context for Splunk operations"""
    
    def __init__(self, service: client.Service | None, is_connected: bool):
        self.service = service
        self.is_connected = is_connected


class BaseTool(ABC):
    """
    Base class for all MCP tools.
    
    Provides common functionality like error handling, logging, and Splunk connection validation.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def extract_client_config(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
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
        splunk_keys = [key for key in kwargs.keys() if key.startswith('splunk_')]
        
        for key in splunk_keys:
            client_config[key] = kwargs.pop(key)
            
        return client_config if client_config else None

    async def get_splunk_service(self, ctx: Context, client_config: Optional[Dict[str, Any]] = None) -> client.Service:
        """
        Get Splunk service connection using client config or fallback to server default.
        
        Args:
            ctx: MCP context
            client_config: Optional client-provided Splunk configuration
            
        Returns:
            Splunk service connection
            
        Raises:
            Exception: If no connection available and client config doesn't work
        """
        # Try client-provided configuration first
        if client_config:
            try:
                from src.client.splunk_client import get_splunk_service
                self.logger.info("Using client-provided Splunk configuration")
                return get_splunk_service(client_config)
            except Exception as e:
                self.logger.warning(f"Failed to connect with client config: {e}")
                # Fall through to try server default
        
        # Fall back to server default connection
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
        
        if not splunk_ctx.is_connected or not splunk_ctx.service:
            return False, None, "Splunk service is not available. MCP server is running in degraded mode."
        
        return True, splunk_ctx.service, ""
    
    def format_error_response(self, error: str, **kwargs) -> Dict[str, Any]:
        """Format a consistent error response"""
        return {
            "status": "error",
            "error": error,
            **kwargs
        }
    
    def format_success_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a consistent success response"""
        return {
            "status": "success",
            **data
        }
    
    @abstractmethod
    async def execute(self, ctx: Context, **kwargs) -> Dict[str, Any]:
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
    async def get_prompt(self, ctx: Context, **kwargs) -> Dict[str, Any]:
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
        version: str = "1.0.0"
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
        tags: list[str] | None = None
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
        arguments: list[Dict[str, Any]] | None = None
    ):
        self.name = name
        self.description = description
        self.category = category
        self.tags = tags or []
        self.arguments = arguments or [] 