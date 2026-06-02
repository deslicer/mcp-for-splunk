"""Parse the scraped ITSI 4.21 schema markdown into structured JSON.

Usage:
    python -m scripts.itsi_schema.parse_schema_md \
        --source .research/itsi/schema.md \
        --out mcp_itsi/knowledge/schema/data

The output is one ``<slug>.json`` file per object type / subordinate structure,
plus an ``index.json`` describing the corpus. These files are bundled with the
package and consumed by ``mcp_itsi.knowledge.schema.registry``.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from scripts.itsi_schema import mapping

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*?)\s*$")
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_BULLET_LINK_RE = re.compile(r"^\s*-\s*\[([^\]]+)\]")

_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "int": "integer",
    "number": "number",
    "float": "number",
    "boolean": "boolean",
    "bool": "boolean",
    "object": "object",
    "objects": "array",
    "dict": "object",
    "array": "array",
    "list": "array",
    "boolean operator": "string",
}


@dataclass
class Attribute:
    name: str
    label: str
    type: str
    type_raw: str
    required: bool
    read_only: bool
    description: str
    subordinate: str | None = None


@dataclass
class Schema:
    slug: str
    title: str
    kind: str  # "object" | "subordinate"
    description: str = ""
    object_type: str | None = None
    interface: str | None = None
    endpoint: str | None = None
    subordinate_objects: list[str] = field(default_factory=list)
    attributes: list[Attribute] = field(default_factory=list)


def _clean_field_name(cell: str) -> str:
    """Turn a doc field cell like ``_\\_key_`` into ``_key``."""
    text = cell.strip()
    m = re.match(r"^_(.*)_$", text)
    if m:
        text = m.group(1)
    text = text.replace("\\_", "_").replace("\\", "")
    text = text.strip()
    return mapping.FIELD_NAME_OVERRIDES.get(text, text)


def _normalize_type(cell: str) -> tuple[str, str]:
    raw = cell.strip()
    key = raw.lower().strip(" .")
    return _TYPE_MAP.get(key, "string"), raw


def _clean_description(cell: str) -> str:
    text = cell.replace("<br>", " ").replace("\\_", "_")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_row(line: str) -> list[str] | None:
    m = _TABLE_ROW_RE.match(line)
    if not m:
        return None
    return [c.strip() for c in m.group(1).split("|")]


def _parse_attribute_table(lines: list[str], start: int) -> tuple[list[Attribute], int]:
    """Parse a markdown table starting at/after ``start``; return rows + next idx."""
    attrs: list[Attribute] = []
    i = start
    seen: set[str] = set()
    in_table = False
    while i < len(lines):
        line = lines[i]
        if _HEADING_RE.match(line):
            break
        cells = _split_row(line)
        if cells is None:
            if in_table:
                break
            i += 1
            continue
        # Header / separator rows.
        joined = "".join(cells).replace("-", "").replace(":", "").strip()
        if not joined or {c.lower() for c in cells} >= {"field", "type", "description"}:
            in_table = True
            i += 1
            continue
        in_table = True
        if len(cells) < 3:
            i += 1
            continue
        name = _clean_field_name(cells[0])
        if not name or name.lower() in seen:
            i += 1
            continue
        seen.add(name.lower())
        type_norm, type_raw = _normalize_type(cells[1])
        attrs.append(
            Attribute(
                name=name,
                label=name,
                type=type_norm,
                type_raw=type_raw,
                required=False,
                read_only=name.lower() in mapping.READ_ONLY_FIELDS,
                description=_clean_description("|".join(cells[2:])),
            )
        )
        i += 1
    return attrs, i


def _parse_sections(lines: list[str]) -> dict[str, dict]:
    """Split the doc body into raw section dicts keyed by section title."""
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == "# ITSI REST API schema"),
        0,
    )
    sections: dict[str, dict] = {}
    current: dict | None = None
    i = start
    while i < len(lines):
        line = lines[i]
        m = _HEADING_RE.match(line)
        if m and len(m.group(1)) == 2:
            title = m.group(2).strip()
            current = {"title": title, "description": "", "attributes": [], "subs": []}
            sections[title] = current
            i += 1
            continue
        if current is None:
            i += 1
            continue
        if m and m.group(2).strip() == "Description":
            desc, i = _collect_description(lines, i + 1)
            current["description"] = desc
            continue
        if m and m.group(2).strip() == "Attributes":
            attrs, i = _parse_attribute_table(lines, i + 1)
            current["attributes"] = attrs
            continue
        if m and m.group(2).strip().startswith("Subordinate"):
            subs, i = _collect_subordinates(lines, i + 1)
            current["subs"] = subs
            continue
        i += 1
    return sections


def _collect_description(lines: list[str], start: int) -> tuple[str, int]:
    out: list[str] = []
    i = start
    while i < len(lines):
        if _HEADING_RE.match(lines[i]):
            break
        text = lines[i].strip()
        if text:
            out.append(text)
        i += 1
    return " ".join(out).strip(), i


def _collect_subordinates(lines: list[str], start: int) -> tuple[list[str], int]:
    titles: list[str] = []
    i = start
    while i < len(lines):
        if _HEADING_RE.match(lines[i]):
            break
        m = _BULLET_LINK_RE.match(lines[i])
        if m:
            titles.append(m.group(1).strip())
        i += 1
    return titles, i


def _resolve_slug(title: str) -> tuple[str, str] | None:
    """Return ``(slug, kind)`` for a section title, or ``None`` to skip."""
    if title in mapping.SKIP_SECTIONS:
        return None
    if title in mapping.TOP_LEVEL_OBJECTS:
        return mapping.TOP_LEVEL_OBJECTS[title], "object"
    if title in mapping.SUBORDINATE_OBJECTS:
        return mapping.SUBORDINATE_OBJECTS[title], "subordinate"
    return None


def _title_to_slug(title: str) -> str | None:
    if title in mapping.TOP_LEVEL_OBJECTS:
        return mapping.TOP_LEVEL_OBJECTS[title]
    if title in mapping.SUBORDINATE_OBJECTS:
        return mapping.SUBORDINATE_OBJECTS[title]
    return None


def build_schemas(markdown: str, common_attrs: list[Attribute]) -> dict[str, Schema]:
    lines = markdown.splitlines()
    sections = _parse_sections(lines)
    schemas: dict[str, Schema] = {}
    for title, raw in sections.items():
        resolved = _resolve_slug(title)
        if resolved is None:
            continue
        slug, kind = resolved
        schema = Schema(slug=slug, title=title, kind=kind, description=raw["description"])
        if kind == "object":
            schema.object_type = slug
            schema.interface = mapping.interface_for(slug)
            schema.endpoint = f"{schema.interface}/{slug}"
        schema.subordinate_objects = [
            s for t in raw["subs"] if (s := _title_to_slug(t)) is not None
        ]
        attrs: list[Attribute] = list(raw["attributes"])
        _apply_required(slug, attrs)
        _apply_nesting(slug, attrs)
        _merge_common(attrs, common_attrs)
        schema.attributes = attrs
        schemas[slug] = schema
    return schemas


def _apply_required(slug: str, attrs: list[Attribute]) -> None:
    required = set(mapping.REQUIRED_FIELDS.get(slug, ()))
    for attr in attrs:
        if attr.name in required or attr.name.lower() in required:
            attr.required = True


def _apply_nesting(slug: str, attrs: list[Attribute]) -> None:
    for attr in attrs:
        child = mapping.NESTING.get((slug, attr.name))
        if child:
            attr.subordinate = child


def _merge_common(attrs: list[Attribute], common: list[Attribute]) -> None:
    have = {a.name.lower() for a in attrs}
    for c in common:
        if c.name.lower() not in have:
            attrs.append(c)


def _extract_common_attrs(markdown: str) -> list[Attribute]:
    lines = markdown.splitlines()
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m and m.group(2).strip() == "Common Attributes":
            attrs, _ = _parse_attribute_table(lines, i + 1)
            return attrs
    return []


def write_output(schemas: dict[str, Schema], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for slug, schema in sorted(schemas.items()):
        payload = asdict(schema)
        (out_dir / f"{slug}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    index = {
        "version": "4.21",
        "source": (
            "https://help.splunk.com/en/splunk-it-service-intelligence/"
            "splunk-it-service-intelligence/leverage-rest-apis/4.21/"
            "itsi-rest-api-schema/itsi-rest-api-schema"
        ),
        "object_types": sorted(
            s.slug for s in schemas.values() if s.kind == "object"
        ),
        "subordinate_structures": sorted(
            s.slug for s in schemas.values() if s.kind == "subordinate"
        ),
        "entries": {
            slug: {
                "title": s.title,
                "kind": s.kind,
                "object_type": s.object_type,
                "endpoint": s.endpoint,
                "attribute_count": len(s.attributes),
                "subordinate_objects": s.subordinate_objects,
            }
            for slug, s in sorted(schemas.items())
        },
    }
    (out_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=".research/itsi/schema.md")
    parser.add_argument("--out", default="mcp_itsi/knowledge/schema/data")
    args = parser.parse_args()

    markdown = Path(args.source).read_text(encoding="utf-8")
    common = _extract_common_attrs(markdown)
    schemas = build_schemas(markdown, common)
    write_output(schemas, Path(args.out))
    print(f"Wrote {len(schemas)} schemas to {args.out} (common attrs: {len(common)})")


if __name__ == "__main__":
    main()
