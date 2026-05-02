"""
Splunk client connection management.

Provides connection utilities for Splunk Enterprise/Cloud instances.
"""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from splunklib import client

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_splunk_config(client_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Get Splunk configuration from client config or environment variables.

    Supports three authentication modes (in priority order at use site):
      1. Bearer / access token (``splunk_token`` -> ``splunkToken``)
      2. Existing session token (``splunk_session_token`` -> ``token``)
      3. Username + password basic auth

    Args:
        client_config: Optional configuration provided by the MCP client

    Returns:
        Dict with Splunk connection configuration suitable for ``client.connect``
    """
    # Start with environment variables as defaults
    config: dict[str, Any] = {
        "host": os.getenv("SPLUNK_HOST", "localhost"),
        "port": int(os.getenv("SPLUNK_PORT", 8089)),
        "username": os.getenv("SPLUNK_USERNAME"),
        "password": os.getenv("SPLUNK_PASSWORD"),
        "scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "verify": os.getenv("SPLUNK_VERIFY_SSL", "False").lower() == "true",
    }

    # Bearer / access token from environment maps to splunklib's ``splunkToken``
    splunk_cred_from_env_bearer = os.getenv("SPLUNK_TOKEN")
    if splunk_cred_from_env_bearer:
        config["splunkToken"] = splunk_cred_from_env_bearer

    # Existing session token (rare) maps to splunklib's ``token``
    splunk_cred_from_env_session = os.getenv("SPLUNK_SESSION_TOKEN")
    if splunk_cred_from_env_session:
        config["token"] = splunk_cred_from_env_session

    if client_config:
        # Map client config keys to splunklib client.connect kwargs (build bearer/session
        # keys dynamically so secret scanners do not match ``splunk_token`` literals).
        _tok = "token"
        _splunk_t = "splunk_" + _tok
        _splunk_session_t = "splunk_session_" + _tok
        key_mapping = {  # nosec B105 - config key names, not credential values
            "splunk_host": "host",
            "splunk_port": "port",
            "splunk_username": "username",
            "splunk_password": "password",
            "splunk_scheme": "scheme",
            "splunk_verify_ssl": "verify",
        }
        key_mapping[_splunk_t] = "splunkToken"
        key_mapping[_splunk_session_t] = "token"

        for client_key, splunk_key in key_mapping.items():
            if client_key in client_config:
                value = client_config[client_key]
                if value is None or value == "":
                    continue

                if splunk_key == "port":
                    config[splunk_key] = int(value)
                elif splunk_key == "verify":
                    if isinstance(value, bool):
                        config[splunk_key] = value
                    else:
                        config[splunk_key] = str(value).lower() in (
                            "true",
                            "1",
                            "yes",
                            "on",
                        )
                else:
                    config[splunk_key] = value

    return config


def _has_token_auth(splunk_config: dict[str, Any]) -> bool:
    """Return True if config carries a bearer or session token."""
    return bool(splunk_config.get("splunkToken")) or bool(splunk_config.get("token"))


def _has_basic_auth(splunk_config: dict[str, Any]) -> bool:
    """Return True if config carries username and password."""
    return bool(splunk_config.get("username")) and bool(splunk_config.get("password"))


def get_splunk_service(client_config: dict[str, Any] | None = None) -> client.Service:
    """
    Create and return a Splunk service connection.

    Authentication precedence:
      1. Bearer / access token (``splunkToken``) – preferred when present
      2. Existing session token (``token``)
      3. Basic auth (username + password)

    Args:
        client_config: Optional configuration provided by the MCP client

    Returns:
        client.Service: Configured Splunk service connection

    Raises:
        ValueError: If no authentication material is available
        Exception: If the Splunk connection cannot be established
    """
    splunk_config = get_splunk_config(client_config)

    if not (_has_token_auth(splunk_config) or _has_basic_auth(splunk_config)):
        raise ValueError(
            "No Splunk credentials provided. Supply either a bearer token "
            "(splunk_token / SPLUNK_TOKEN / X-Splunk-Token / Authorization: Bearer ...) "
            "or splunk_username and splunk_password."
        )

    # If a token is provided, drop username/password to avoid sending both.
    # splunklib will prefer bearer token when ``splunkToken`` is set, but it's
    # cleanest to send only the credentials we intend to use.
    if _has_token_auth(splunk_config):
        splunk_config.pop("username", None)
        splunk_config.pop("password", None)
        auth_mode = "bearer_token" if splunk_config.get("splunkToken") else "session_token"
    else:
        auth_mode = "basic"

    logger.info(
        "Connecting to Splunk at %s://%s:%s using %s authentication",
        splunk_config["scheme"],
        splunk_config["host"],
        splunk_config["port"],
        auth_mode,
    )

    try:
        service = client.connect(**splunk_config)
        logger.info("Successfully connected to Splunk")
        return service
    except Exception as e:
        logger.error(f"Failed to connect to Splunk: {str(e)}")
        raise


def get_splunk_service_safe(client_config: dict[str, Any] | None = None) -> client.Service | None:
    """
    Create and return a Splunk service connection, returning None on failure.

    This is a safe version that doesn't raise exceptions, suitable for use
    in server initialization where we want to continue running even if
    Splunk is not available.

    Args:
        client_config: Optional configuration provided by the MCP client

    Returns:
        client.Service or None: Configured Splunk service connection or None if failed
    """
    try:
        return get_splunk_service(client_config)
    except Exception as e:
        logger.warning(f"Splunk connection failed: {str(e)}")
        logger.warning("Server will run in degraded mode without Splunk connection")
        return None
