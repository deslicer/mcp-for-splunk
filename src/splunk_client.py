import logging
import os
import time

from dotenv import load_dotenv
from splunklib import client

load_dotenv()

logger = logging.getLogger(__name__)


def get_splunk_service(retry_count: int = 3, retry_delay: int = 5) -> client.Service:
    """Create and return a Splunk service connection with retry logic"""
    host = os.getenv("SPLUNK_HOST", "localhost")
    port = int(os.getenv("SPLUNK_PORT", "8089"))
    username = os.getenv("SPLUNK_USERNAME")
    password = os.getenv("SPLUNK_PASSWORD")
    token = os.getenv("SPLUNK_TOKEN")

    if not token and not (username and password):
        raise ValueError("Either SPLUNK_TOKEN or SPLUNK_USERNAME/SPLUNK_PASSWORD must be provided")

    last_exception = None

    for attempt in range(retry_count):
        try:
            logger.info(
                f"Attempting to connect to Splunk at {host}:{port} (attempt {attempt + 1}/{retry_count})"
            )

            if token:
                service = client.Service(host=host, port=port, token=token, verify=False)
            else:
                service = client.Service(
                    host=host, port=port, username=username, password=password, verify=False
                )

            # Explicitly attempt login and verify connection
            service.login()

            # Test the connection by trying to get server info
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

    # If we get here, all attempts failed
    raise ValueError(
        f"Failed to connect to Splunk after {retry_count} attempts: {str(last_exception)}\n"
        f"Using host={host}, port={port}, "
        f"auth_type={'token' if token else 'username/password'}"
    )


def get_splunk_service_safe() -> client.Service | None:
    """Safe version that returns None instead of raising an exception"""
    try:
        return get_splunk_service()
    except Exception as e:
        logger.error(f"Splunk connection failed: {str(e)}")
        return None
