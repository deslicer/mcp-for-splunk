"""
Base classes for client-scoped Splunk resources.

Provides abstract base classes for multi-tenant resources with client isolation.
"""

import logging
from abc import abstractmethod
from typing import Any

from fastmcp import Context
from splunklib import client

from ..core.base import BaseResource
from ..core.client_identity import ClientIdentity, SecurityError, get_client_manager

logger = logging.getLogger(__name__)


class ClientScopedResource(BaseResource):
    """
    Base class for client-scoped MCP resources with security isolation.

    Features:
    - Automatic client identity management
    - Secure resource URI generation
    - Client-specific Splunk connections
    - Access control and audit logging
    """

    def __init__(
        self, base_uri_template: str, name: str, description: str, mime_type: str = "text/plain"
    ):
        # Base template will be populated with client_id
        super().__init__(base_uri_template, name, description, mime_type)
        self.base_uri_template = base_uri_template
        self.client_manager = get_client_manager()

    async def get_content(self, ctx: Context, uri: str = None) -> str:
        """
        Get resource content with client isolation.

        Args:
            ctx: MCP context containing client information
            uri: Specific resource URI (optional, uses self.uri if not provided)

        Returns:
            Resource content as string

        Raises:
            SecurityError: If client access is denied
            ConnectionError: If Splunk connection fails
        """
        # Extract client configuration from context
        client_config = self._get_client_config_from_context(ctx)
        if not client_config:
            raise SecurityError(
                "No client configuration found - resources require client-specific Splunk access"
            )

        # Get client identity and connection
        try:
            identity, service = await self.client_manager.get_client_connection(ctx, client_config)
        except Exception as e:
            self.logger.error(f"Failed to establish client connection: {e}")
            raise SecurityError(f"Client authentication failed: {str(e)}") from e

        # Validate URI belongs to this client
        if uri:
            self._validate_client_uri_access(identity, uri)

        # Get resource content with client-specific connection
        try:
            content = await self._get_client_specific_content(identity, service, uri or self.uri)

            # Audit log
            self.logger.info(f"Resource accessed by client {identity.client_id}: {uri or self.uri}")

            return content

        except Exception as e:
            self.logger.error(
                f"Failed to get resource content for client {identity.client_id}: {e}"
            )
            raise

    def generate_client_uri(self, client_id: str, **params) -> str:
        """
        Generate client-scoped URI from template.

        Args:
            client_id: Client identifier
            **params: Additional URI parameters

        Returns:
            Client-scoped resource URI
        """
        uri_params = {"client_id": client_id, **params}
        return self.base_uri_template.format(**uri_params)

    def _get_client_config_from_context(self, ctx: Context) -> dict[str, Any] | None:
        """Extract client configuration from MCP context"""
        try:
            # Try multiple sources based on your existing implementation
            if hasattr(ctx.request_context, "request") and hasattr(
                ctx.request_context.request, "state"
            ):
                if hasattr(ctx.request_context.request.state, "client_config"):
                    return ctx.request_context.request.state.client_config

            # Try lifespan context
            splunk_ctx = ctx.request_context.lifespan_context
            if hasattr(splunk_ctx, "client_config") and splunk_ctx.client_config:
                return splunk_ctx.client_config

        except Exception as e:
            self.logger.debug(f"Could not extract client config: {e}")

        return None

    def _validate_client_uri_access(self, identity: ClientIdentity, uri: str):
        """
        Validate that client can access the requested URI.

        Args:
            identity: Client identity
            uri: Requested resource URI

        Raises:
            SecurityError: If access is denied
        """
        # Check if URI contains client ID
        if identity.client_id not in uri:
            raise SecurityError(
                f"Access denied: URI {uri} does not belong to client {identity.client_id}"
            )

        # Additional URI validation can be added here
        self.logger.debug(f"URI access validated for client {identity.client_id}: {uri}")

    @abstractmethod
    async def _get_client_specific_content(
        self, identity: ClientIdentity, service: client.Service, uri: str
    ) -> str:
        """
        Get resource content using client-specific Splunk connection.

        Args:
            identity: Client identity
            service: Client's Splunk service connection
            uri: Resource URI

        Returns:
            Resource content as string
        """
        pass
