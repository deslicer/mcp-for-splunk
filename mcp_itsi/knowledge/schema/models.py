"""Dataclasses describing a single ITSI object-type schema.

These mirror the JSON produced by ``scripts/itsi_schema`` and add convenience
methods (case-insensitive attribute lookup, JSON-Schema projection).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_JSON_SCHEMA_TYPES = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "object": "object",
    "array": "array",
}


@dataclass(frozen=True)
class AttributeSpec:
    """One documented field of an ITSI object type."""

    name: str
    type: str
    description: str = ""
    required: bool = False
    read_only: bool = False
    subordinate: str | None = None
    type_raw: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttributeSpec:
        return cls(
            name=data["name"],
            type=data.get("type", "string"),
            description=data.get("description", ""),
            required=bool(data.get("required", False)),
            read_only=bool(data.get("read_only", False)),
            subordinate=data.get("subordinate"),
            type_raw=data.get("type_raw", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "read_only": self.read_only,
            "subordinate": self.subordinate,
        }


@dataclass(frozen=True)
class ObjectSchema:
    """Structured schema for an ITSI object type or subordinate structure."""

    slug: str
    title: str
    kind: str  # "object" | "subordinate"
    description: str = ""
    object_type: str | None = None
    interface: str | None = None
    endpoint: str | None = None
    subordinate_objects: tuple[str, ...] = ()
    attributes: tuple[AttributeSpec, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObjectSchema:
        return cls(
            slug=data["slug"],
            title=data.get("title", data["slug"]),
            kind=data.get("kind", "object"),
            description=data.get("description", ""),
            object_type=data.get("object_type"),
            interface=data.get("interface"),
            endpoint=data.get("endpoint"),
            subordinate_objects=tuple(data.get("subordinate_objects", ())),
            attributes=tuple(
                AttributeSpec.from_dict(a) for a in data.get("attributes", ())
            ),
        )

    def attribute(self, name: str) -> AttributeSpec | None:
        """Case-insensitive attribute lookup."""
        lowered = name.lower()
        for attr in self.attributes:
            if attr.name.lower() == lowered:
                return attr
        return None

    @property
    def field_names(self) -> list[str]:
        return [a.name for a in self.attributes]

    @property
    def required_fields(self) -> list[str]:
        return [a.name for a in self.attributes if a.required]

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "kind": self.kind,
            "object_type": self.object_type,
            "interface": self.interface,
            "endpoint": self.endpoint,
            "description": self.description,
            "subordinate_objects": list(self.subordinate_objects),
            "attributes": [a.to_dict() for a in self.attributes],
        }

    def to_json_schema(self) -> dict[str, Any]:
        """Project the schema into a (lightweight) JSON-Schema object."""
        properties: dict[str, Any] = {}
        for attr in self.attributes:
            prop: dict[str, Any] = {
                "type": _JSON_SCHEMA_TYPES.get(attr.type, "string"),
                "description": attr.description,
            }
            if attr.read_only:
                prop["readOnly"] = True
            if attr.subordinate:
                prop["x-itsi-subordinate"] = attr.subordinate
                if attr.type == "array":
                    prop["items"] = {"$ref": f"#/$defs/{attr.subordinate}"}
            properties[attr.name] = prop
        schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": self.title,
            "type": "object",
            "properties": properties,
        }
        required = self.required_fields
        if required:
            schema["required"] = required
        return schema
