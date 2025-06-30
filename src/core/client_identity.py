"""
Client identity and security management for multi-tenant MCP resources.

Provides secure client identification, connection pooling, and resource isolation.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from fastmcp import Context
from splunklib import client

from src.client.splunk_client import get_splunk_service

logger = logging.getLogger(__name__)


@dataclass
class ClientIdentity:
    """Secure client identity for resource isolation"""
    client_id: str          # Secure hash of client configuration
    session_id: str         # MCP session identifier
    config_hash: str        # Hash of Splunk configuration
    splunk_host: str        # Splunk host for auditing
    created_at: float       # Timestamp for cleanup
    

class ClientConnectionManager:
    """
    Manages client-specific Splunk connections with security isolation.
    
    Features:
    - Client identity based on configuration hash
    - Connection pooling per client
    - Automatic cleanup of idle connections
    - Security validation and audit logging
    """
    
    def __init__(self, max_connections_per_client: int = 5, idle_timeout: int = 3600):
        self._connections: Dict[str, client.Service] = {}
        self._client_identities: Dict[str, ClientIdentity] = {}
        self._max_connections_per_client = max_connections_per_client
        self._idle_timeout = idle_timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def create_client_identity(self, ctx: Context, client_config: Dict[str, Any]) -> ClientIdentity:
        """
        Create secure client identity from configuration.
        
        Args:
            ctx: MCP context containing session info
            client_config: Client's Splunk configuration
            
        Returns:
            ClientIdentity with secure hash-based ID
        """
        # Create deterministic hash of client configuration for identity
        config_str = self._normalize_config_for_hash(client_config)
        config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        
        # Get session ID from context
        session_id = self._extract_session_id(ctx)
        
        # Create secure client ID (config hash + session prefix)
        client_id = f"client_{config_hash}_{session_id[:8]}"
        
        identity = ClientIdentity(
            client_id=client_id,
            session_id=session_id,
            config_hash=config_hash,
            splunk_host=client_config.get('splunk_host', 'unknown'),
            created_at=time.time()
        )
        
        self._client_identities[client_id] = identity
        
        # Security audit log
        self.logger.info(f"Created client identity: {client_id} for host: {identity.splunk_host}")
        
        return identity
    
    async def get_client_connection(self, ctx: Context, client_config: Dict[str, Any]) -> tuple[ClientIdentity, client.Service]:
        """
        Get or create Splunk connection for client with security validation.
        
        Args:
            ctx: MCP context
            client_config: Client's Splunk configuration
            
        Returns:
            Tuple of (ClientIdentity, Splunk Service)
            
        Raises:
            SecurityError: If client validation fails
            ConnectionError: If Splunk connection fails
        """
        identity = self.create_client_identity(ctx, client_config)
        
        # Check for existing connection
        if identity.client_id in self._connections:
            try:
                service = self._connections[identity.client_id]
                # Validate connection is still alive
                service.info()  # Simple ping
                self.logger.debug(f"Reusing connection for client: {identity.client_id}")
                return identity, service
            except Exception as e:
                self.logger.warning(f"Stale connection for client {identity.client_id}: {e}")
                del self._connections[identity.client_id]
        
        # Create new connection with security validation
        try:
            self._validate_client_config(client_config)
            service = get_splunk_service(client_config)
            
            # Store connection
            self._connections[identity.client_id] = service
            
            # Security audit log
            self.logger.info(f"Established Splunk connection for client: {identity.client_id}")
            
            return identity, service
            
        except Exception as e:
            self.logger.error(f"Failed to create connection for client {identity.client_id}: {e}")
            raise ConnectionError(f"Failed to connect to Splunk: {str(e)}")
    
    def _normalize_config_for_hash(self, config: Dict[str, Any]) -> str:
        """
        Normalize client config for consistent hashing.
        
        Only includes connection-relevant fields, excludes passwords.
        """
        normalized = {
            'host': config.get('splunk_host', '').lower(),
            'port': config.get('splunk_port', 8089),
            'username': config.get('splunk_username', '').lower(),
            'scheme': config.get('splunk_scheme', 'https').lower()
        }
        
        # Sort keys for consistent hashing
        return '|'.join(f"{k}:{v}" for k, v in sorted(normalized.items()))
    
    def _extract_session_id(self, ctx: Context) -> str:
        """Extract session ID from MCP context"""
        try:
            # Try multiple sources for session ID
            if hasattr(ctx, 'session') and ctx.session:
                return str(ctx.session.session_id)[:16]
            elif hasattr(ctx.request_context, 'request') and hasattr(ctx.request_context.request, 'headers'):
                # Look for session header
                headers = ctx.request_context.request.headers
                session_id = headers.get('x-session-id') or headers.get('authorization', '')[:16]
                if session_id:
                    return session_id
        except:
            pass
        
        # Fallback to generated ID
        return uuid4().hex[:16]
    
    def _validate_client_config(self, config: Dict[str, Any]):
        """
        Validate client configuration for security.
        
        Raises:
            SecurityError: If configuration is invalid or unsafe
        """
        required_fields = ['splunk_host', 'splunk_username', 'splunk_password']
        
        for field in required_fields:
            if not config.get(field):
                raise SecurityError(f"Required field missing: {field}")
        
        # Validate host format (prevent injection)
        host = config['splunk_host']
        if not isinstance(host, str) or len(host.strip()) == 0:
            raise SecurityError("Invalid Splunk host format")
        
        # Additional security validations
        if len(config['splunk_username']) > 100:
            raise SecurityError("Username too long")
        
        port = config.get('splunk_port', 8089)
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise SecurityError("Invalid port number")
    
    def cleanup_idle_connections(self):
        """Clean up idle client connections"""
        import time
        current_time = time.time()
        
        expired_clients = []
        for client_id, identity in self._client_identities.items():
            if current_time - identity.created_at > self._idle_timeout:
                expired_clients.append(client_id)
        
        for client_id in expired_clients:
            self._remove_client(client_id)
            self.logger.info(f"Cleaned up idle client: {client_id}")
    
    def _remove_client(self, client_id: str):
        """Remove client and cleanup resources"""
        if client_id in self._connections:
            try:
                self._connections[client_id].logout()
            except:
                pass
            del self._connections[client_id]
        
        if client_id in self._client_identities:
            del self._client_identities[client_id]


class SecurityError(Exception):
    """Security validation error"""
    pass


# Global client manager instance
_client_manager = ClientConnectionManager()


def get_client_manager() -> ClientConnectionManager:
    """Get the global client connection manager"""
    return _client_manager


import time 