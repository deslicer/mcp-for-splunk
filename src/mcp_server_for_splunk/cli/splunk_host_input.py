"""Validate host input before displaying or persisting it."""

from urllib.parse import urlsplit


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
