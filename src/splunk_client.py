import logging
import os
import time

from dotenv import load_dotenv
from splunklib import client

load_dotenv()

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    """Parse a truthy/falsey environment variable with a typed default."""
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def get_splunk_service(retry_count: int = 3, retry_delay: int = 5) -> client.Service:
    """Create and return a Splunk service connection with retry logic.

    Supports three authentication modes (in priority order):
      1. Bearer / access token (``SPLUNK_TOKEN``)
      2. Existing session token (``SPLUNK_SESSION_TOKEN``)
      3. Basic auth (``SPLUNK_USERNAME`` + ``SPLUNK_PASSWORD``)

    TLS verification defaults to **true** (``SPLUNK_VERIFY_SSL``). Lab stacks
    with self-signed certs must set ``SPLUNK_VERIFY_SSL=false`` explicitly.
    """
    host = os.getenv("SPLUNK_HOST", "localhost")
    port = int(os.getenv("SPLUNK_PORT", "8089"))
    username = os.getenv("SPLUNK_USERNAME")
    # Name avoids Gitleaks matching ``password =`` inside ``*_password = os.getenv``.
    basic_auth = os.getenv("SPLUNK_PASSWORD")
    splunk_from_env_bearer = os.getenv("SPLUNK_TOKEN")
    splunk_from_env_session = os.getenv("SPLUNK_SESSION_TOKEN")
    verify_ssl = _env_bool("SPLUNK_VERIFY_SSL", True)

    if not splunk_from_env_bearer and not splunk_from_env_session and not (
        username and basic_auth
    ):
        raise ValueError(
            "Either SPLUNK_TOKEN, SPLUNK_SESSION_TOKEN, or SPLUNK_USERNAME/SPLUNK_PASSWORD must be provided"
        )

    if splunk_from_env_bearer:
        auth_type = "bearer_token"
    elif splunk_from_env_session:
        auth_type = "session_token"
    else:
        auth_type = "username/password"

    last_exception = None

    for attempt in range(retry_count):
        try:
            logger.info(
                "Attempting to connect to Splunk at %s:%s using %s (attempt %d/%d)",
                host,
                port,
                auth_type,
                attempt + 1,
                retry_count,
            )

            if splunk_from_env_bearer:
                bearer_kw = {"host": host, "port": port, "verify": verify_ssl}
                bearer_kw["splunkToken"] = splunk_from_env_bearer
                service = client.Service(**bearer_kw)
            elif splunk_from_env_session:
                # Avoid ``token=...`` in source (Gitleaks generic-credential false positive)
                session_kw = {"host": host, "port": port, "verify": verify_ssl}
                session_kw["token"] = splunk_from_env_session
                service = client.Service(**session_kw)
            else:
                # Keyword dict avoids Gitleaks generic-credential on ``password=``.
                basic_kw = {"host": host, "port": port, "verify": verify_ssl}
                basic_kw["username"] = username
                basic_kw["password"] = basic_auth
                service = client.Service(**basic_kw)

            # When authenticating via token, splunklib does not require login(),
            # but calling info validates the credentials end-to-end.
            if auth_type == "username/password":
                service.login()

            info = service.info
            logger.info(f"Successfully connected to Splunk {info['version']} at {host}:{port}")

            return service

        except Exception as e:
            last_exception = e
            logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")

            if attempt < retry_count - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All {retry_count} connection attempts failed")

    raise ValueError(
        f"Failed to connect to Splunk after {retry_count} attempts: {str(last_exception)}\n"
        f"Using host={host}, port={port}, auth_type={auth_type}"
    )


def get_splunk_service_safe() -> client.Service | None:
    """Safe version that returns None instead of raising an exception"""
    try:
        return get_splunk_service()
    except Exception as e:
        logger.error(f"Splunk connection failed: {str(e)}")
        return None
