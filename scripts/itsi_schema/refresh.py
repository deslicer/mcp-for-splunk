"""Refresh bundled ITSI schemas from the live Splunk docs.

Pipeline:
1. Scrape the ITSI 4.21 REST API schema page with the Firecrawl CLI.
2. Parse the markdown into structured ``data/*.json`` (parse_schema_md).
3. Render the bundled ``content/api/schema.md`` (render_markdown).

Requires the ``firecrawl`` CLI to be installed and authenticated
(`firecrawl --status`). Run from the repo root:

    python -m scripts.itsi_schema.refresh
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts.itsi_schema import parse_schema_md, render_markdown

SCHEMA_URL = (
    "https://help.splunk.com/en/splunk-it-service-intelligence/"
    "splunk-it-service-intelligence/leverage-rest-apis/4.21/"
    "itsi-rest-api-schema/itsi-rest-api-schema"
)


def scrape(url: str, dest: Path, *, wait_ms: int = 4000) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = dest.with_suffix(".raw.json")
    cmd = [
        "firecrawl", "scrape", url,
        "--format", "markdown,links",
        "--wait-for", str(wait_ms),
        "--json", "-o", str(raw),
    ]
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    data = json.loads(raw.read_text(encoding="utf-8"))
    markdown = data.get("markdown") or ""
    if not markdown:
        raise SystemExit("Firecrawl returned no markdown content.")
    dest.write_text(markdown, encoding="utf-8")
    print(f"Scraped {len(markdown)} chars -> {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=SCHEMA_URL)
    parser.add_argument("--source", default=".research/itsi/schema.md")
    parser.add_argument("--data", default="mcp_itsi/knowledge/schema/data")
    parser.add_argument("--doc", default="mcp_itsi/knowledge/content/api/schema.md")
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Reuse the existing --source markdown instead of re-scraping.",
    )
    args = parser.parse_args()

    source = Path(args.source)
    if not args.skip_scrape:
        scrape(args.url, source)
    elif not source.exists():
        print(f"--skip-scrape set but {source} is missing", file=sys.stderr)
        raise SystemExit(1)

    markdown = source.read_text(encoding="utf-8")
    common = parse_schema_md._extract_common_attrs(markdown)
    schemas = parse_schema_md.build_schemas(markdown, common)
    parse_schema_md.write_output(schemas, Path(args.data))
    print(f"Generated {len(schemas)} schemas -> {args.data}")

    doc = render_markdown.render(Path(args.data))
    Path(args.doc).parent.mkdir(parents=True, exist_ok=True)
    Path(args.doc).write_text(doc, encoding="utf-8")
    print(f"Rendered doc -> {args.doc}")


if __name__ == "__main__":
    main()
