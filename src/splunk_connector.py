# src/splunk_connector.py
import os
import logging
import splunklib.client as client
from splunklib.binding import HTTPError
from dotenv import load_dotenv

# Load environment variables from .env file at the start
load_dotenv()

logger = logging.getLogger(__name__)

# --- Configuration ---
SPLUNK_HOST = os.getenv("SPLUNK_HOST")
SPLUNK_PORT_STR = os.getenv("SPLUNK_PORT", "8089") # Default Splunkd port
SPLUNK_USERNAME = os.getenv("SPLUNK_USERNAME")
SPLUNK_PASSWORD = os.getenv("SPLUNK_PASSWORD")
SPLUNK_TOKEN = os.getenv("SPLUNK_TOKEN")
# Optional: Explicitly set scheme if needed, otherwise defaults based on port might work
# SPLUNK_SCHEME = os.getenv("SPLUNK_SCHEME", "https")

# --- State ---
# Module-level variable to cache the Splunk service connection object
_service = None

# --- Custom Exception ---
class SplunkConnectionError(Exception):
    """Custom exception for Splunk connection issues."""
    pass

# --- Connection Function ---
def get_splunk_service() -> client.Service:
    """
    Connects to Splunk using environment variables and returns a Service object.
    Caches the connection for reuse. Attempts reconnection if the cached
    connection seems stale (based on a light check).

    Raises:
        ValueError: If required configuration environment variables are missing.
        SplunkConnectionError: If connection to Splunk fails for any reason.

    Returns:
        splunklib.client.Service: An authenticated Splunk service object.
    """
    global _service

    # --- Check Cache ---
    if _service:
        try:
            # Perform a lightweight check to see if the connection is likely still valid.
            # Listing apps with count=1 is usually a fast operation.
            _service.apps.list(count=1)
            logger.debug("Using cached Splunk service connection.")
            return _service
        except (HTTPError, ConnectionError, Exception) as e:
            # Catch potential errors indicating a stale connection
            logger.warning(f"Cached Splunk connection seems stale ({type(e).__name__}). Attempting reconnection.")
            _service = None # Reset cache

    # --- Validate Configuration ---
    if not SPLUNK_HOST:
        raise ValueError("SPLUNK_HOST environment variable not set.")

    try:
        splunk_port = int(SPLUNK_PORT_STR)
    except ValueError:
        raise ValueError(f"Invalid SPLUNK_PORT: '{SPLUNK_PORT_STR}'. Must be an integer.")

    # Determine connection arguments based on provided credentials
    connect_args = {
        "host": SPLUNK_HOST,
        "port": splunk_port,
        # "scheme": SPLUNK_SCHEME # Uncomment if explicitly setting scheme
        # Add other options like 'owner', 'app' if needed globally
    }

    auth_method = None
    if SPLUNK_TOKEN:
        connect_args["token"] = SPLUNK_TOKEN
        auth_method = "token"
    elif SPLUNK_USERNAME and SPLUNK_PASSWORD:
        connect_args["username"] = SPLUNK_USERNAME
        connect_args["password"] = SPLUNK_PASSWORD
        auth_method = "username/password"
    else:
        raise ValueError("Splunk authentication details (SPLUNK_TOKEN or SPLUNK_USERNAME/SPLUNK_PASSWORD) not fully provided in environment variables.")

    # --- Attempt Connection ---
    try:
        logger.info(f"Attempting to connect to Splunk at {SPLUNK_HOST}:{splunk_port} using {auth_method}...")
        service = client.connect(**connect_args)

        # Verify connection by fetching server info (includes version)
        server_info = service.info
        splunk_version = server_info.get('version', 'N/A')
        logger.info(f"Successfully connected to Splunk version {splunk_version}")

        _service = service # Cache the successful connection
        return _service

    # --- Handle Specific Errors ---
    except HTTPError as he:
        # Log the detailed error from Splunk if possible
        error_body = "No details available."
        try:
            if he.body:
                error_body = he.body.read().decode()
        except Exception:
            pass # Ignore errors reading the body itself
        logger.error(f"Splunk HTTP Error ({he.status}): {he.reason}. Details: {error_body}", exc_info=False) # Set exc_info=False to avoid redundant traceback for HTTPError
        raise SplunkConnectionError(f"Splunk authentication or API error ({he.status}): {he.reason}. Check credentials and Splunk service health. Details: {error_body}") from he

    except ConnectionRefusedError as cre:
        logger.error(f"Splunk connection refused at {SPLUNK_HOST}:{splunk_port}. Is Splunk running and accessible?", exc_info=False)
        raise SplunkConnectionError(f"Connection refused by Splunk at {SPLUNK_HOST}:{splunk_port}. Ensure Splunkd is running and the port is accessible.") from cre

    except Exception as e:
        # Catch other potential exceptions during connection (network issues, SSL errors, etc.)
        logger.error(f"Failed to connect to Splunk due to an unexpected error: {e}", exc_info=True)
        raise SplunkConnectionError(f"An unexpected error occurred while connecting to Splunk: {str(e)}") from e
# --- End of Connection Function ---