"""Tests for the ITSI schema knowledge layer and pre-flight validation."""

from __future__ import annotations

import pytest

from mcp_itsi.knowledge.schema import PayloadValidator, registry
from mcp_itsi.knowledge.schema.examples import examples_for
from mcp_itsi.tools import _itoa_ops as ops
from mcp_itsi.tools._validation import (
    PayloadValidationError,
    drain_warnings,
    preflight,
    reset_warnings,
)

# --- Registry -------------------------------------------------------------


def test_registry_loads_core_object_types():
    slugs = {s.slug for s in registry.list_object_types()}
    assert {"service", "kpi_base_search", "entity", "entity_type"} <= slugs


def test_registry_get_by_object_type_and_slug():
    assert registry.get("service") is registry.get("service")
    assert registry.get("SERVICE").slug == "service"
    assert registry.get("does_not_exist") is None


def test_service_schema_marks_required_and_nested():
    svc = registry.get("service")
    assert "title" in svc.required_fields
    kpis = svc.attribute("kpis")
    assert kpis is not None and kpis.subordinate == "service_kpi"


def test_json_schema_projection_has_types_and_required():
    js = registry.get("service").to_json_schema()
    assert js["type"] == "object"
    assert js["properties"]["title"]["type"] == "string"
    assert "title" in js["required"]


# --- Validator ------------------------------------------------------------


def test_valid_payload_passes():
    result = PayloadValidator().validate("service", {"title": "Web", "enabled": 1})
    assert result.ok
    assert not result.errors


def test_unknown_typo_field_is_error_with_suggestion():
    result = PayloadValidator().validate("service", {"titel": "Web"})
    assert not result.ok
    messages = " ".join(e.message for e in result.errors)
    assert "title" in messages


def test_unknown_nontypo_field_is_warning_not_error():
    result = PayloadValidator().validate(
        "service", {"title": "Web", "totally_unrelated_field_xyz": 1}
    )
    assert result.ok
    assert any("not in the documented" in w.message for w in result.warnings)


def test_wrong_type_is_error():
    result = PayloadValidator().validate("service", {"title": 123})
    assert not result.ok
    assert any(e.field == "title" for e in result.errors)


def test_boolean_field_accepts_integer():
    # ITSI uses 1/0 for documented "Boolean" fields like enabled.
    assert PayloadValidator().validate("service", {"title": "x", "enabled": 1}).ok
    assert not PayloadValidator().validate("service", {"title": "x", "enabled": "yes"}).ok


def test_missing_required_is_error_unless_partial():
    full = PayloadValidator().validate("service", {"description": "d"})
    assert not full.ok
    partial = PayloadValidator().validate("service", {"description": "d"}, is_partial=True)
    assert partial.ok


def test_read_only_field_is_warning():
    result = PayloadValidator().validate("service", {"title": "x", "object_type": "service"})
    assert result.ok
    assert any(w.field == "object_type" for w in result.warnings)


def test_nested_kpi_validation_recurses():
    result = PayloadValidator().validate(
        "service", {"title": "x", "kpis": [{"titel": "bad"}]}
    )
    assert not result.ok
    assert any("Service KPI" in e.message for e in result.errors)


def test_unknown_object_type_errors():
    result = PayloadValidator().validate("nope", {"title": "x"})
    assert not result.ok


# --- Examples -------------------------------------------------------------


@pytest.mark.parametrize("object_type", ["service", "kpi_base_search"])
def test_curated_examples_validate_clean(object_type):
    curated = examples_for(registry.get(object_type)).get("curated")
    assert curated is not None
    result = PayloadValidator().validate(object_type, curated)
    assert result.ok, [e.message for e in result.errors]
    assert not result.warnings


def test_minimal_example_contains_required_fields():
    minimal = examples_for(registry.get("service"))["minimal"]
    assert "title" in minimal


# --- Write-path pre-flight ------------------------------------------------


def test_preflight_raises_on_hard_error():
    reset_warnings()
    with pytest.raises(PayloadValidationError):
        preflight("service", {"titel": "x"}, is_partial=False)


def test_preflight_records_warnings_without_raising():
    reset_warnings()
    preflight("service", {"title": "x", "object_type": "service"}, is_partial=False)
    warnings = drain_warnings()
    assert warnings
    assert drain_warnings() == []  # buffer cleared after drain


def test_preflight_skips_unknown_object_type():
    reset_warnings()
    preflight("unknown_type", {"anything": True}, is_partial=False)  # no raise


async def test_create_object_blocks_before_network():
    # ctx is None: if pre-flight did not block first, we'd hit an AttributeError
    # trying to open a client. A PayloadValidationError proves it blocked early.
    reset_warnings()
    with pytest.raises(PayloadValidationError):
        await ops.create_object(None, "service", {"titel": "x"})


# --- Tools ----------------------------------------------------------------


async def test_list_object_schemas_tool():
    from mcp_itsi.tools.schema import ListObjectSchemas

    result = await ListObjectSchemas().execute(None, None)
    assert result["status"] == "success"
    assert result["count"] >= 15
    assert any(e["object_type"] == "service" for e in result["object_types"])


async def test_get_object_schema_tool_offline():
    from mcp_itsi.tools.schema import GetObjectSchema

    result = await GetObjectSchema().execute(None, None, object_type="service")
    assert result["status"] == "success"
    assert result["object_type"] == "service"
    assert "service_kpi" in result["subordinate_schemas"]
    assert "json_schema" in result
    assert "curated" in result["examples"]


async def test_get_object_schema_unknown_type():
    from mcp_itsi.tools.schema import GetObjectSchema

    result = await GetObjectSchema().execute(None, None, object_type="nope")
    assert result["status"] == "error"


async def test_validate_payload_tool_reports_errors():
    from mcp_itsi.tools.schema import ValidateObjectPayload

    result = await ValidateObjectPayload().execute(
        None, None, object_type="service", payload={"titel": "x"}
    )
    assert result["status"] == "success"
    assert result["ok"] is False
    assert result["errors"]
