"""Unit tests for saved search namespace helpers."""

from unittest.mock import Mock

from splunklib import client as spl_client

from src.tools.search.saved_search_tools import (
    DEFAULT_SAVED_SEARCH_APP,
    _apply_saved_search_namespace,
    _namespace_for_saved_search_acl,
    _namespace_for_saved_search_create,
)


def test_namespace_for_saved_search_create_user_uses_app_context():
    namespace = _namespace_for_saved_search_create(
        app="search", owner="admin", sharing="user"
    )
    assert namespace["app"] == "search"
    assert namespace["owner"] == "admin"
    assert namespace["sharing"] == "user"


def test_namespace_for_saved_search_acl_defaults_missing_app():
    namespace = _namespace_for_saved_search_acl(
        {"owner": "admin", "sharing": "user"}
    )
    assert namespace["app"] == DEFAULT_SAVED_SEARCH_APP
    assert namespace["owner"] == "admin"
    assert namespace["sharing"] == "user"


def test_apply_saved_search_namespace_uses_acl():
    service = Mock()
    service.namespace = None
    saved_search = Mock()
    saved_search.content = {
        "eai:acl": {"app": "search", "owner": "admin", "sharing": "app"}
    }

    original = _apply_saved_search_namespace(service, saved_search)

    assert service.namespace["app"] == "search"
    assert service.namespace["sharing"] == "app"
    assert original is None


def test_apply_saved_search_namespace_fallback_for_empty_acl():
    service = Mock()
    service.namespace = spl_client.namespace(sharing="global")
    service.username = "admin"
    saved_search = Mock()
    saved_search.content = {"eai:acl": {}}

    original = _apply_saved_search_namespace(service, saved_search)

    assert service.namespace["app"] == DEFAULT_SAVED_SEARCH_APP
    assert service.namespace["owner"] == "admin"
    assert service.namespace["sharing"] == "user"
    assert original["sharing"] == "global"
