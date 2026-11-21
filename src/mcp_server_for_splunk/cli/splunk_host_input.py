"""Validate host input before displaying or persisting it."""

from urllib.parse import urlsplit

from mcp_server_for_splunk.cli.secure_input import read_hidden_input


def normalize_splunk_host(value: str) -> str:
    """Accept a host or HTTP(S) origin, never embedded credentials or URL secrets."""
    value = value.strip()
    if not value:
        return ""
    error = "Use a hostname or HTTP(S) origin without credentials, path, query or fragment."
    if any(char.isspace() or ord(char) < 32 for char in value) or "\\" in value:
        raise ValueError(error)
    try:
        parsed = urlsplit(value if "://" in value else "//" + value)
        if (
            parsed.scheme not in ("", "http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "@" in parsed.netloc
            or "%" in parsed.netloc
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(error)
        # Validate port syntax without including the supplied value in errors.
        _ = parsed.port
    except ValueError:
        raise ValueError(error) from None
    return parsed.netloc


def prompt_splunk_host(current: str) -> str:
    """Read without terminal echo, including when a user pastes URL credentials."""
    prompt = f"Enter Splunk host/URL (hidden; Enter to keep {current or 'unset'}): "
    value = read_hidden_input(prompt)
    host = normalize_splunk_host(value.strip() or current)
    if not host:
        raise ValueError("Splunk host is required.")
    return host
