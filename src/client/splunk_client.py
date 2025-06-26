"""
Splunk client connection management.

Provides connection utilities for Splunk Enterprise/Cloud instances.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from splunklib import client

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_splunk_service() -> client.Service:
    """
    Create and return a Splunk service connection.
    
    Returns:
        client.Service: Configured Splunk service connection
        
    Raises:
        Exception: If connection cannot be established
    """
    # Get Splunk connection parameters from environment
    splunk_config = {
        'host': os.getenv('SPLUNK_HOST', 'localhost'),
        'port': int(os.getenv('SPLUNK_PORT', 8089)),
        'username': os.getenv('SPLUNK_USERNAME'),
        'password': os.getenv('SPLUNK_PASSWORD'),
        'scheme': os.getenv('SPLUNK_SCHEME', 'https'),
        'verify': os.getenv('SPLUNK_VERIFY_SSL', 'False').lower() == 'true'
    }
    
    # Validate required parameters
    if not splunk_config['username'] or not splunk_config['password']:
        raise ValueError("SPLUNK_USERNAME and SPLUNK_PASSWORD must be set")
    
    logger.info(f"Connecting to Splunk at {splunk_config['scheme']}://{splunk_config['host']}:{splunk_config['port']}")
    
    try:
        service = client.connect(**splunk_config)
        logger.info("Successfully connected to Splunk")
        return service
    except Exception as e:
        logger.error(f"Failed to connect to Splunk: {str(e)}")
        raise


def get_splunk_service_safe() -> Optional[client.Service]:
    """
    Create and return a Splunk service connection, returning None on failure.
    
    This is a safe version that doesn't raise exceptions, suitable for use
    in server initialization where we want to continue running even if
    Splunk is not available.
    
    Returns:
        client.Service or None: Configured Splunk service connection or None if failed
    """
    try:
        return get_splunk_service()
    except Exception as e:
        logger.warning(f"Splunk connection failed: {str(e)}")
        logger.warning("Server will run in degraded mode without Splunk connection")
        return None 