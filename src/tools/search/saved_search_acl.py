"""ACL helpers for Splunk saved searches.

splunklib exposes ownership on ``entity.access``; ``content['eai:acl']`` is often
empty even when the search is visible via REST.
"""

from __future__ import annotations

from typing import Any


def get_saved_search_acl(saved_search: Any) -> dict[str, Any]:
    """Return ACL metadata for a saved search entity."""
    access = getattr(saved_search, "access", None)
    if isinstance(access, dict) and access:
        return dict(access)

    content = getattr(saved_search, "content", None) or {}
    acl = content.get("eai:acl")
    if isinstance(acl, dict) and acl:
        return dict(acl)
    return {}


def acl_field(acl: dict[str, Any], field: str) -> str | None:
    """Return a string ACL field when present."""
    value = acl.get(field)
    return str(value) if value is not None else None


def matches_app_owner(
    acl: dict[str, Any],
    app: str | None,
    owner: str | None,
) -> bool:
    """Return True when ACL matches optional app/owner filters."""
    if app:
        acl_app = acl_field(acl, "app")
        if acl_app is not None and acl_app != app:
            return False
    if owner:
        acl_owner = acl_field(acl, "owner")
        if acl_owner is not None and acl_owner != owner:
            return False
    return True
