"""Unit tests for shared entity_acl() used by config resources.

Saved-search tools already use get_saved_search_acl() (see
tests/test_saved_search_acl.py). This module pins the shared
src.core.utils.entity_acl helper for indexes/saved-search resources.
"""

from src.core.utils import entity_acl


class FakeEntity:
    """Mimics a live splunklib Entity: ACL on .access, NOT in .content."""

    def __init__(self, access=None, content=None, name="fake"):
        self.name = name
        if access is not None:
            self.access = access
        self.content = content if content is not None else {}


def test_entity_acl_prefers_access_record():
    entity = FakeEntity(
        access={"app": "my_app", "owner": "nobody", "sharing": "global"},
        content={"search": "index=main"},
    )
    acl = entity_acl(entity)
    assert acl["app"] == "my_app"
    assert acl["owner"] == "nobody"


def test_entity_acl_falls_back_to_content_for_fakes():
    del_entity = FakeEntity(content={"eai:acl": {"app": "search", "owner": "admin"}})
    if hasattr(del_entity, "access"):
        delattr(del_entity, "access")
    assert entity_acl(del_entity)["app"] == "search"


def test_entity_acl_non_dict_access_falls_back():
    class WeirdAccess:
        pass

    entity = FakeEntity(content={"eai:acl": {"owner": "admin"}})
    entity.access = WeirdAccess()
    assert entity_acl(entity) == {"owner": "admin"}


def test_entity_acl_empty_when_nothing_available():
    entity = FakeEntity(content={"search": "index=main"})
    if hasattr(entity, "access"):
        delattr(entity, "access")
    assert entity_acl(entity) == {}
