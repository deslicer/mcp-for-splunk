"""Unit tests for saved search ACL helpers."""

from types import SimpleNamespace

from src.tools.search.saved_search_acl import (
    get_saved_search_acl,
    matches_app_owner,
)


def test_get_saved_search_acl_prefers_access_over_content():
    entity = SimpleNamespace(
        access={"app": "deslicer_ai_insights", "owner": "admin", "sharing": "app"},
        content={"eai:acl": {"app": "search", "owner": "nobody"}},
    )
    assert get_saved_search_acl(entity)["app"] == "deslicer_ai_insights"


def test_get_saved_search_acl_falls_back_to_content():
    entity = SimpleNamespace(
        access={},
        content={"eai:acl": {"app": "search", "owner": "admin", "sharing": "app"}},
    )
    assert get_saved_search_acl(entity)["owner"] == "admin"


def test_matches_app_owner():
    acl = {"app": "deslicer_ai_insights", "owner": "admin"}
    assert matches_app_owner(acl, "deslicer_ai_insights", "admin")
    assert not matches_app_owner(acl, "search", "admin")
    assert not matches_app_owner(acl, "deslicer_ai_insights", "nobody")
