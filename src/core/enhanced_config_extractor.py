"""
Enhanced client configuration extractor for multi-transport MCP environments.

Supports multiple ways for clients to provide Splunk configurations:
- HTTP headers (existing)
- Environment variables (existing)
- Configuration files
- MCP client metadata
- WebSocket messages
- JSON configuration payloads
- Client certificates with embedded config
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastmcp import Context

logger = logging.getLogger(__name__)

from .shared_context import http_headers_context  # noqa: E402


class EnhancedConfigExtractor:
    """
    Enhanced configuration extractor supporting multiple transport methods.

    Priority order:
    1. Tool-level parameters (highest priority)
    2. HTTP headers
    3. MCP client metadata
    4. Configuration files
    5. Environment variables
    6. WebSocket/Session data
    7. Server defaults (lowest priority)
    """

    def __init__(self, config_dir: str = None):
        self.config_dir = config_dir or os.path.join(os.getcwd(), "client_configs")
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Ensure config directory exists
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

    async def extract_client_config(
        self, ctx: Context, tool_params: dict[str, Any] = None
    ) -> dict[str, Any] | None:
        """
        Extract client configuration from multiple sources in priority order.

        Args:
            ctx: MCP context
            tool_params: Optional tool parameters that may contain config

        Returns:
            Client configuration dict or None
        """
        # Add debug logging about the context
        self.logger.debug(f"Extracting client config from context type: {type(ctx)}")
        self.logger.debug(
            f"Context attributes: {[attr for attr in dir(ctx) if not attr.startswith('_')]}"
        )

        extraction_methods = [
            ("tool_parameters", lambda: self._extract_from_tool_params(tool_params)),
            ("context_variable_headers", lambda: self._extract_from_context_variable_headers()),
            ("middleware_context", lambda: self._extract_from_middleware_context(ctx)),
            ("http_headers", lambda: self._extract_from_http_headers(ctx)),
            ("mcp_metadata", lambda: self._extract_from_mcp_metadata(ctx)),
            ("config_file", lambda: self._extract_from_config_file(ctx)),
            ("environment", lambda: self._extract_from_environment(ctx)),
            ("websocket_session", lambda: self._extract_from_websocket_session(ctx)),
            ("client_certificate", lambda: self._extract_from_client_certificate(ctx)),
            ("json_payload", lambda: self._extract_from_json_payload(ctx)),
        ]

        for method_name, extract_func in extraction_methods:
            try:
                config = extract_func()
                if config:
                    self.logger.info(f"Successfully extracted client config using: {method_name}")
                    return self._normalize_config(config)
            except Exception as e:
                self.logger.debug(f"Failed to extract config using {method_name}: {e}")

        # NEW: If no client configuration found, return server default configuration
        # This allows resources to work with the default Splunk connection
        self.logger.info("No client configuration found - using server default configuration")
        return self._get_server_default_config()

    def _extract_from_tool_params(self, tool_params: dict[str, Any]) -> dict[str, Any] | None:
        """Extract config from tool parameters (highest priority)"""
        if not tool_params:
            return None

        config = {}
        splunk_keys = [key for key in tool_params.keys() if key.startswith("splunk_")]

        for key in splunk_keys:
            config[key] = tool_params[key]

        return config if config else None

    def _extract_from_context_variable_headers(self) -> dict[str, Any] | None:
        """Extract config from context variable headers"""
        try:
            # Get headers from the context variable
            headers = http_headers_context.get({})
            if headers:
                self.logger.debug(f"Found HTTP headers in context variable: {list(headers.keys())}")
                # Extract Splunk config from the headers
                config = self._extract_config_from_headers(headers)
                if config:
                    self.logger.debug(
                        "Successfully extracted Splunk config from context variable headers"
                    )
                    return config
            else:
                self.logger.debug("No headers found in context variable")
        except Exception as e:
            self.logger.debug(f"Error extracting from context variable headers: {e}")

        return None

    def _extract_from_middleware_context(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from middleware context attributes"""
        try:
            # Check if there's any middleware-related data accessible through the context
            # This might be stored in various ways depending on how FastMCP handles middleware data

            # Check for common middleware attribute names
            potential_attrs = [
                "splunk_client_config",
                "client_config",
                "middleware_data",
                "request_data",
            ]

            for attr_name in potential_attrs:
                if hasattr(ctx, attr_name):
                    attr_value = getattr(ctx, attr_name)
                    if attr_value:
                        self.logger.debug(f"Found config in context attribute: {attr_name}")
                        return attr_value

            # Check if the context has access to the request context with middleware data
            if hasattr(ctx, "request_context") and hasattr(ctx.request_context, "middleware_data"):
                middleware_data = ctx.request_context.middleware_data
                if isinstance(middleware_data, dict) and "splunk_client_config" in middleware_data:
                    return middleware_data["splunk_client_config"]

        except Exception as e:
            self.logger.debug(f"Error extracting from middleware context: {e}")

        return None

    def _extract_from_http_headers(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from HTTP headers (existing method)"""
        try:
            # First, check if the middleware stored the config in the request state
            if hasattr(ctx.request_context, "request") and hasattr(
                ctx.request_context.request, "state"
            ):
                if hasattr(ctx.request_context.request.state, "client_config"):
                    return ctx.request_context.request.state.client_config

            # Also check if the middleware stored it as splunk_client_config in the context
            # This is where ClientConfigMiddleware actually stores it
            if hasattr(ctx, "splunk_client_config") and ctx.splunk_client_config:
                return ctx.splunk_client_config

        except Exception as e:
            self.logger.debug(f"Error extracting from HTTP headers: {e}")

        return None

    def _extract_from_mcp_metadata(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from MCP client metadata"""
        try:
            # Check if MCP context has client metadata
            if hasattr(ctx, "client_info") and ctx.client_info:
                client_info = ctx.client_info

                # Look for Splunk configuration in client metadata
                if "splunk_config" in client_info:
                    return client_info["splunk_config"]

                # Check for individual metadata fields
                config = {}
                metadata_mapping = {
                    "splunk_host": "splunk_host",
                    "splunk_instance": "splunk_host",
                    "splunk_server": "splunk_host",
                    "splunk_port": "splunk_port",
                    "splunk_username": "splunk_username",
                    "splunk_user": "splunk_username",
                    "splunk_password": "splunk_password",
                    "splunk_token": "splunk_password",  # Support token auth
                    "splunk_scheme": "splunk_scheme",
                    "splunk_protocol": "splunk_scheme",
                }

                for meta_key, config_key in metadata_mapping.items():
                    if meta_key in client_info:
                        config[config_key] = client_info[meta_key]

                return config if config else None

        except Exception as e:
            self.logger.debug(f"Error extracting from MCP metadata: {e}")

        return None

    def _extract_from_config_file(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from client-specific configuration files"""
        try:
            # Try to get client ID or session ID for config file lookup
            client_id = self._get_client_identifier(ctx)
            if not client_id:
                return None

            # Look for configuration files in multiple formats
            config_files = [
                f"{client_id}.json",
                f"{client_id}.yaml",
                f"{client_id}.yml",
                f"client_{client_id}.json",
                "default_client.json",
            ]

            for config_file in config_files:
                config_path = Path(self.config_dir) / config_file

                if config_path.exists():
                    self.logger.debug(f"Found config file: {config_path}")

                    if config_file.endswith(".json"):
                        with open(config_path) as f:
                            config_data = json.load(f)
                            if "splunk" in config_data:
                                return config_data["splunk"]
                            return config_data

                    elif config_file.endswith((".yaml", ".yml")):
                        try:
                            import yaml

                            with open(config_path) as f:
                                config_data = yaml.safe_load(f)
                                if "splunk" in config_data:
                                    return config_data["splunk"]
                                return config_data
                        except ImportError:
                            self.logger.warning("PyYAML not installed, skipping YAML config files")
                            continue

        except Exception as e:
            self.logger.debug(f"Error reading config file: {e}")

        return None

    def _extract_from_environment(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from environment variables (existing method)"""
        try:
            # Check if we can access the lifespan context
            if hasattr(ctx.request_context, "lifespan_context"):
                splunk_ctx = ctx.request_context.lifespan_context
                self.logger.debug(f"Found lifespan context: {type(splunk_ctx)}")

                # Check if the middleware updated the client_config
                if hasattr(splunk_ctx, "client_config") and splunk_ctx.client_config:
                    self.logger.debug("Found client_config in lifespan context")
                    return splunk_ctx.client_config
                else:
                    self.logger.debug(
                        f"No client_config in lifespan context. Available attributes: {[attr for attr in dir(splunk_ctx) if not attr.startswith('_')]}"
                    )
            else:
                self.logger.debug("No lifespan_context found in request_context")

        except Exception as e:
            self.logger.debug(f"Error extracting from environment: {e}")

        return None

    def _extract_from_websocket_session(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from WebSocket session data"""
        try:
            # Check if this is a WebSocket connection with session data
            if hasattr(ctx, "websocket") and ctx.websocket:
                ws = ctx.websocket

                # Look for session state or cookies
                if hasattr(ws, "session") and ws.session:
                    session = ws.session

                    # Check for Splunk config in session
                    if "splunk_config" in session:
                        return session["splunk_config"]

                # Check WebSocket headers for configuration
                if hasattr(ws, "headers") and ws.headers:
                    return self._extract_config_from_headers(dict(ws.headers))

        except Exception as e:
            self.logger.debug(f"Error extracting from WebSocket session: {e}")

        return None

    def _extract_from_client_certificate(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from client certificate metadata"""
        try:
            # Check if client provided a certificate with embedded metadata
            if hasattr(ctx.request_context, "request") and hasattr(
                ctx.request_context.request, "scope"
            ):
                scope = ctx.request_context.request.scope

                # Look for client certificate in ASGI scope
                if "client" in scope and scope["client"]:
                    _client_info = scope["client"]

                    # Check for TLS client certificate
                    if "tls" in scope and "client_cert" in scope["tls"]:
                        cert_data = scope["tls"]["client_cert"]

                        # Extract Splunk config from certificate subject or extensions
                        # This is a placeholder - real implementation would parse cert
                        if "splunk_host" in str(cert_data):
                            # Parse certificate for embedded configuration
                            pass

        except Exception as e:
            self.logger.debug(f"Error extracting from client certificate: {e}")

        return None

    def _extract_from_json_payload(self, ctx: Context) -> dict[str, Any] | None:
        """Extract config from JSON payload in request body"""
        try:
            # Check if request has a JSON body with configuration
            if hasattr(ctx.request_context, "request") and hasattr(
                ctx.request_context.request, "json"
            ):
                request = ctx.request_context.request

                # For POST requests, check if body contains config
                if hasattr(request, "_json") and request._json:
                    json_data = request._json

                    if "splunk_config" in json_data:
                        return json_data["splunk_config"]

                    # Check for direct Splunk parameters in JSON
                    config = {}
                    for key, value in json_data.items():
                        if key.startswith("splunk_"):
                            config[key] = value

                    return config if config else None

        except Exception as e:
            self.logger.debug(f"Error extracting from JSON payload: {e}")

        return None

    def _get_client_identifier(self, ctx: Context) -> str | None:
        """Get a client identifier for config file lookup"""
        try:
            # Try multiple sources for client ID

            # 1. Check if context has session ID
            if hasattr(ctx, "session_id") and ctx.session_id:
                return str(ctx.session_id)

            # 2. Check if HTTP request has client identifier
            if hasattr(ctx.request_context, "request"):
                request = ctx.request_context.request

                # Check headers for client ID
                if hasattr(request, "headers"):
                    headers = dict(request.headers)
                    client_id = (
                        headers.get("x-client-id")
                        or headers.get("x-mcp-client-id")
                        or headers.get("client-id")
                    )
                    if client_id:
                        return client_id

                # Check query parameters
                if hasattr(request, "query_params"):
                    client_id = request.query_params.get("client_id")
                    if client_id:
                        return client_id

            # 3. Check MCP client info
            if hasattr(ctx, "client_info") and ctx.client_info:
                client_info = ctx.client_info
                if "client_id" in client_info:
                    return client_info["client_id"]
                if "name" in client_info:
                    return client_info["name"]

        except Exception as e:
            self.logger.debug(f"Error getting client identifier: {e}")

        return None

    def _extract_config_from_headers(self, headers: dict[str, str]) -> dict[str, Any] | None:
        """Helper to extract Splunk config from headers dict"""
        config = {}

        header_mapping = {
            "X-Splunk-Host": "splunk_host",
            "X-Splunk-Port": "splunk_port",
            "X-Splunk-Username": "splunk_username",
            "X-Splunk-Password": "splunk_password",
            "X-Splunk-Token": "splunk_password",  # Support token auth
            "X-Splunk-Scheme": "splunk_scheme",
            "X-Splunk-Verify-SSL": "splunk_verify_ssl",
        }

        for header_name, config_key in header_mapping.items():
            header_value = headers.get(header_name) or headers.get(header_name.lower())
            if header_value:
                if config_key == "splunk_port":
                    config[config_key] = int(header_value)
                elif config_key == "splunk_verify_ssl":
                    config[config_key] = header_value.lower() == "true"
                else:
                    config[config_key] = header_value

        return config if config else None

    def _normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Normalize configuration to standard format"""
        normalized = {}

        # Standard field mapping
        field_mapping = {
            "host": "splunk_host",
            "hostname": "splunk_host",
            "server": "splunk_host",
            "port": "splunk_port",
            "username": "splunk_username",
            "user": "splunk_username",
            "password": "splunk_password",
            "token": "splunk_password",
            "auth_token": "splunk_password",
            "scheme": "splunk_scheme",
            "protocol": "splunk_scheme",
            "verify_ssl": "splunk_verify_ssl",
            "ssl_verify": "splunk_verify_ssl",
            "verify": "splunk_verify_ssl",
        }

        # Normalize field names
        for key, value in config.items():
            normalized_key = field_mapping.get(key, key)

            # Ensure all keys have splunk_ prefix
            if not normalized_key.startswith("splunk_"):
                normalized_key = f"splunk_{normalized_key}"

            normalized[normalized_key] = value

        # Apply type conversions
        if "splunk_port" in normalized:
            try:
                normalized["splunk_port"] = int(normalized["splunk_port"])
            except (ValueError, TypeError):
                normalized["splunk_port"] = 8089

        if "splunk_verify_ssl" in normalized:
            ssl_value = normalized["splunk_verify_ssl"]
            if isinstance(ssl_value, str):
                normalized["splunk_verify_ssl"] = ssl_value.lower() in ("true", "1", "yes", "on")
            else:
                normalized["splunk_verify_ssl"] = bool(ssl_value)

        return normalized

    async def save_client_config(self, client_id: str, config: dict[str, Any]) -> bool:
        """
        Save client configuration to file for future use.

        Args:
            client_id: Client identifier
            config: Configuration to save

        Returns:
            True if saved successfully
        """
        try:
            config_file = Path(self.config_dir) / f"{client_id}.json"

            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)

            self.logger.info(f"Saved client config to {config_file}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save client config: {e}")
            return False

    def _get_server_default_config(self) -> dict[str, Any]:
        """
        Get server default configuration from environment variables.

        This serves as a fallback when no client-specific configuration is provided,
        allowing resources to use the default Splunk connection configured for the server.

        Returns:
            Server default configuration dict
        """
        try:
            # Extract from standard server environment variables
            default_config = {}

            # Standard server environment variables
            env_mapping = {
                "SPLUNK_HOST": "splunk_host",
                "SPLUNK_PORT": "splunk_port",
                "SPLUNK_USERNAME": "splunk_username",
                "SPLUNK_PASSWORD": "splunk_password",
                "SPLUNK_SCHEME": "splunk_scheme",
                "SPLUNK_VERIFY_SSL": "splunk_verify_ssl",
            }

            for env_var, config_key in env_mapping.items():
                env_value = os.getenv(env_var)
                if env_value:
                    # Handle type conversions
                    if config_key == "splunk_port":
                        default_config[config_key] = int(env_value)
                    elif config_key == "splunk_verify_ssl":
                        default_config[config_key] = env_value.lower() in ("true", "1", "yes", "on")
                    else:
                        default_config[config_key] = env_value

            # Set reasonable defaults if not specified
            if "splunk_port" not in default_config:
                default_config["splunk_port"] = 8089
            if "splunk_scheme" not in default_config:
                default_config["splunk_scheme"] = "https"
            if "splunk_verify_ssl" not in default_config:
                default_config["splunk_verify_ssl"] = False

            # Mark this as server default config for identification
            default_config["_config_source"] = "server_default"
            default_config["_is_default"] = True

            self.logger.info(f"Server default config keys: {list(default_config.keys())}")
            return default_config

        except Exception as e:
            self.logger.error(f"Failed to get server default config: {e}")
            # Return minimal fallback config
            return {"_config_source": "server_default", "_is_default": True, "_error": str(e)}


# Global instance
_config_extractor = EnhancedConfigExtractor()


def get_enhanced_config_extractor() -> EnhancedConfigExtractor:
    """Get the global enhanced config extractor instance"""
    return _config_extractor
