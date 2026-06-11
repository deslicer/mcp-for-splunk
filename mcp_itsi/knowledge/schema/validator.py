"""Validate ITSI payloads against bundled object schemas.

The validator distinguishes hard errors (which should block a write) from
warnings (which should not). It recurses into subordinate objects so that, for
example, every KPI inside ``service.kpis[]`` is checked too.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any

from mcp_itsi.knowledge.schema.models import ObjectSchema
from mcp_itsi.knowledge.schema.registry import SchemaRegistry
from mcp_itsi.knowledge.schema.registry import registry as _default_registry

# Map JSON-Schema type names to the Python types we accept for them.
# ITSI documents many flags as "Boolean" but stores/accepts integer 1/0, so
# boolean fields accept both bool and int.
_PY_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool, int),
    "object": (dict,),
    "array": (list,),
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "field": self.field, "message": self.message}


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    def add_error(self, issue: ValidationIssue) -> None:
        self.errors.append(issue)
        self.ok = False

    def add_warning(self, issue: ValidationIssue) -> None:
        self.warnings.append(issue)

    def merge(self, other: ValidationResult) -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if other.errors:
            self.ok = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }


class PayloadValidator:
    """Validate a payload dict against an :class:`ObjectSchema`."""

    def __init__(self, schema_registry: SchemaRegistry | None = None) -> None:
        self._registry = schema_registry or _default_registry

    def validate(
        self,
        object_type: str,
        payload: Any,
        *,
        is_partial: bool = False,
    ) -> ValidationResult:
        result = ValidationResult()
        schema = self._registry.get(object_type)
        if schema is None:
            result.add_error(
                ValidationIssue(
                    path="$",
                    field=object_type,
                    message=(
                        f"Unknown object type '{object_type}'. Call "
                        "itsi_list_object_schemas to see supported types."
                    ),
                )
            )
            return result
        self._validate_object(schema, payload, "$", is_partial, result)
        return result

    def _validate_object(
        self,
        schema: ObjectSchema,
        payload: Any,
        path: str,
        is_partial: bool,
        result: ValidationResult,
    ) -> None:
        if not isinstance(payload, dict):
            result.add_error(
                ValidationIssue(
                    path=path,
                    field=schema.slug,
                    message=f"Expected a JSON object for '{schema.title}', got {_kind(payload)}.",
                )
            )
            return

        for key, value in payload.items():
            self._validate_field(schema, key, value, path, is_partial, result)

        if not is_partial:
            for required in schema.required_fields:
                if not _has_key(payload, required):
                    result.add_error(
                        ValidationIssue(
                            path=path,
                            field=required,
                            message=f"Missing required field '{required}' for '{schema.title}'.",
                        )
                    )

    def _validate_field(
        self,
        schema: ObjectSchema,
        key: str,
        value: Any,
        path: str,
        is_partial: bool,
        result: ValidationResult,
    ) -> None:
        child_path = f"{path}.{key}"
        attr = schema.attribute(key)
        if attr is None:
            # The 4.21 docs are not exhaustive (real objects carry extra
            # generated fields), so an unrecognized field is only a hard error
            # when it looks like a typo of a known field. Otherwise warn.
            suggestion = _suggest(key, schema.field_names)
            if suggestion is not None:
                result.add_error(
                    ValidationIssue(
                        path=child_path,
                        field=key,
                        message=(
                            f"Unknown field '{key}' for '{schema.title}'. "
                            f"Did you mean '{suggestion}'?"
                        ),
                    )
                )
            else:
                result.add_warning(
                    ValidationIssue(
                        path=child_path,
                        field=key,
                        message=(
                            f"Field '{key}' is not in the documented ITSI 4.21 "
                            f"schema for '{schema.title}'. It may be valid; "
                            "verify the spelling."
                        ),
                    )
                )
            return

        if attr.read_only:
            result.add_warning(
                ValidationIssue(
                    path=child_path,
                    field=key,
                    message=(
                        f"Field '{key}' is server-generated/read-only and is "
                        "typically ignored or rejected on write."
                    ),
                )
            )

        if value is None:
            return

        expected = _PY_TYPES.get(attr.type)
        if expected and not _type_ok(value, expected):
            result.add_error(
                ValidationIssue(
                    path=child_path,
                    field=key,
                    message=(
                        f"Field '{key}' should be {attr.type} "
                        f"(doc type '{attr.type_raw or attr.type}'), got {_kind(value)}."
                    ),
                )
            )
            return

        if attr.subordinate:
            self._validate_subordinate(attr.subordinate, value, child_path, result)

    def _validate_subordinate(
        self,
        slug: str,
        value: Any,
        path: str,
        result: ValidationResult,
    ) -> None:
        child_schema = self._registry.get(slug)
        if child_schema is None:
            return
        if isinstance(value, list):
            for idx, item in enumerate(value):
                self._validate_object(
                    child_schema, item, f"{path}[{idx}]", False, result
                )
        elif isinstance(value, dict):
            self._validate_object(child_schema, value, path, False, result)


def _has_key(payload: dict[str, Any], name: str) -> bool:
    lowered = name.lower()
    return any(k.lower() == lowered for k in payload)


def _type_ok(value: Any, expected: tuple[type, ...]) -> bool:
    # bool is a subclass of int; guard so True is not accepted as integer.
    if bool not in expected and isinstance(value, bool):
        return False
    return isinstance(value, expected)


def _kind(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def _suggest(name: str, candidates: list[str]) -> str | None:
    # High cutoff: only flag near-identical names as typos, so genuinely
    # different (possibly undocumented) field names fall through to a warning.
    matches = difflib.get_close_matches(
        name.lower(), [c.lower() for c in candidates], n=1, cutoff=0.8
    )
    if not matches:
        return None
    for c in candidates:
        if c.lower() == matches[0]:
            return c
    return None
