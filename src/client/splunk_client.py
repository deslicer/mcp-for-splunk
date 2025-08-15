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

    Args:
        client_config: Optional configuration provided by the MCP client

    Returns:
        Dict with Splunk connection configuration
    """
    # Start with environment variables as defaults
    config = {
        "host": os.getenv("SPLUNK_HOST", "localhost"),
        "port": int(os.getenv("SPLUNK_PORT", 8089)),
        "username": os.getenv("SPLUNK_USERNAME"),
        "password": os.getenv("SPLUNK_PASSWORD"),
        "scheme": os.getenv("SPLUNK_SCHEME", "https"),
        "verify": os.getenv("SPLUNK_VERIFY_SSL", "False").lower() == "true",
    }

    # Override with client-provided configuration if available
    if client_config:
        # Map client config keys to Splunk client keys
        key_mapping = {
            "splunk_host": "host",
            "splunk_port": "port",
            "splunk_username": "username",
            "splunk_password": "password",
            "splunk_scheme": "scheme",
            "splunk_verify_ssl": "verify",
        }

        for client_key, splunk_key in key_mapping.items():
            if client_key in client_config:
                value = client_config[client_key]

                # Handle special cases
                if splunk_key == "port":
                    config[splunk_key] = int(value)
                elif splunk_key == "verify":
                    config[splunk_key] = str(value).lower() == "true"
                else:
                    config[splunk_key] = value

    return config


def get_splunk_service(client_config: dict[str, Any] | None = None) -> client.Service:
    """
    Create and return a Splunk service connection.

    Args:
        client_config: Optional configuration provided by the MCP client

    Returns:
        client.Service: Configured Splunk service connection

    Raises:
        Exception: If connection cannot be established
    """
    splunk_config = get_splunk_config(client_config)
    logger.info(f"Splunk config: {splunk_config}")

    # Validate required parameters
    if not splunk_config["username"] or not splunk_config["password"]:
        raise ValueError(
            "Splunk username and password must be provided via client config or environment variables"
        )

    logger.info(
        f"Connecting to Splunk at {splunk_config['scheme']}://{splunk_config['host']}:{splunk_config['port']}"
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
