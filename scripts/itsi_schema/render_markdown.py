"""Render the parsed schema JSON into a single bundled markdown doc.

Produces ``mcp_itsi/knowledge/content/api/schema.md`` from ``data/*.json`` so
the doc tools (``itsi_read_doc('api/schema')``) and the
``itsi://docs/api/schema`` resource serve the complete, regenerable schema.

Usage:
    python -m scripts.itsi_schema.render_markdown \
        --data mcp_itsi/knowledge/schema/data \
        --out mcp_itsi/knowledge/content/api/schema.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

_HEADER = """# ITSI REST API schema (4.21)

> Source: <{source}>
>
> Auto-generated from the ITSI 4.21 REST API schema docs by
> `scripts/itsi_schema`. Do not edit by hand — run the refresh script instead.
> For machine-usable schemas and validation, use the `itsi_get_object_schema`,
> `itsi_list_object_schemas` and `itsi_validate_object_payload` tools.

ITSI stores its configuration in the splunkd KV store. **Do not** write to the
KV store directly — always go through the REST endpoints. Common system fields
(`object_type`, `create_time`, `mod_time`, `_owner`, `_user`, `version`, ...)
are server-generated and read-only.
"""


def _load(data_dir: Path) -> tuple[dict, dict[str, dict]]:
    index = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
    schemas: dict[str, dict] = {}
    for path in data_dir.glob("*.json"):
        if path.name == "index.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        schemas[data["slug"]] = data
    return index, schemas


def _render_attributes(attrs: list[dict]) -> str:
    rows = ["| Field | Type | Req | Description |", "| --- | --- | --- | --- |"]
    for a in attrs:
        flags = []
        if a.get("required"):
            flags.append("yes")
        if a.get("read_only"):
            flags.append("read-only")
        sub = f" *(nested: `{a['subordinate']}`)*" if a.get("subordinate") else ""
        desc = (a.get("description", "") or "").replace("|", "\\|")
        rows.append(
            f"| `{a['name']}` | {a.get('type', '')} | {', '.join(flags) or '-'} | {desc}{sub} |"
        )
    return "\n".join(rows)


def _render_schema(slug: str, schema: dict) -> str:
    lines = [f"## {schema['title']} (`{slug}`)", ""]
    if schema.get("endpoint"):
        lines.append(f"**Endpoint:** `{schema['endpoint']}`  ")
    if schema.get("kind") == "subordinate":
        lines.append("**Kind:** subordinate (nested) structure  ")
    desc = schema.get("description", "")
    if desc:
        lines.append("")
        lines.append(desc)
    subs = schema.get("subordinate_objects") or []
    if subs:
        lines.append("")
        lines.append("**Subordinate objects:** " + ", ".join(f"`{s}`" for s in subs))
    lines.append("")
    lines.append(_render_attributes(schema.get("attributes", [])))
    lines.append("")
    return "\n".join(lines)


def render(data_dir: Path) -> str:
    index, schemas = _load(data_dir)
    parts = [_HEADER.format(source=index.get("source", ""))]

    object_types = index.get("object_types", [])
    subordinate = index.get("subordinate_structures", [])

    parts.append("\n## Object types\n")
    parts.append(", ".join(f"`{t}`" for t in object_types))
    parts.append("\n## Subordinate structures\n")
    parts.append(", ".join(f"`{t}`" for t in subordinate))
    parts.append("")

    parts.append("---\n\n# Object type schemas\n")
    for slug in object_types:
        parts.append(_render_schema(slug, schemas[slug]))

    parts.append("---\n\n# Subordinate structure schemas\n")
    for slug in subordinate:
        parts.append(_render_schema(slug, schemas[slug]))

    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="mcp_itsi/knowledge/schema/data")
    parser.add_argument("--out", default="mcp_itsi/knowledge/content/api/schema.md")
    args = parser.parse_args()

    markdown = render(Path(args.data))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    print(f"Wrote {len(markdown)} chars to {args.out}")


if __name__ == "__main__":
    main()
