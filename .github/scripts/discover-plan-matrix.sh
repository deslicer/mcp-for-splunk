#!/usr/bin/env bash
# Build a GitHub Actions matrix from `.deslicer/environments/*.{yml,yaml}`.
# One parallel plan job per (environment stem, inventory_group) where the
# destination declares at least one non-empty apps[].source_path.
#
# Parent inventory groups expand to leaf groups via GET
# /api/v1/groups/hierarchy/{name}/descendants when OBSERVER_API_URL and
# DESLICER_API_TOKEN are set, or via `deslicer inventory list` when
# DESLICER_CLI is set (GitHub App path). Expansion failures fail closed.
#
# inventory_group names are allowlisted (^[A-Za-z0-9_-]+$) before they enter
# the matrix. change-action splits command-args on whitespace; the previous
# UUID resolve could not carry injected flags — names need this validation.
#
# Outputs (GITHUB_OUTPUT):
#   matrix      — JSON {"include":[{"environment":"…","inventory_group":"…"},…]}
#   has_targets — true when include is non-empty, else false
#
# Env:
#   PIN                  — optional stem filter (workflow_dispatch input)
#   MATRIX_OUTPUT_PATH   — optional file path (matrix fragment artifact)
#   OBSERVER_API_URL     — optional Observer base URL (GitHub Environment secret)
#   DESLICER_API_TOKEN   — optional tools-scope API key (GitHub Environment secret)
#   DESLICER_CLI         — optional path to installed deslicer (GitHub App OIDC)
#   DESLICER_ENVIRONMENT — environment stem for CLI inventory expansion
set -euo pipefail

export PIN="${PIN:-}"
export MATRIX_OUTPUT_PATH="${MATRIX_OUTPUT_PATH:-}"

python3 - <<'PY'
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

root = Path(".deslicer/environments")
pin = os.environ.get("PIN", "").strip()
matrix_output_path = os.environ.get("MATRIX_OUTPUT_PATH", "").strip()
observer_api_url = os.environ.get("OBSERVER_API_URL", "").strip()
api_token = os.environ.get("DESLICER_API_TOKEN", "").strip()
INVENTORY_GROUP_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def assert_safe_inventory_group_name(name: str) -> str:
    """Reject names that would inject argv via whitespace-split command-args."""
    if not INVENTORY_GROUP_NAME_RE.fullmatch(name):
        print(
            f"::error::Invalid inventory_group {name!r}: must match "
            r"^[A-Za-z0-9_-]+$ (no whitespace or CLI flags). "
            "Previous UUID matrix output closed this; names require allowlisting.",
            file=sys.stderr,
        )
        sys.exit(1)
    return name


def parse_group_scalar(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def apps_block_has_source_path(inline_suffix: str, body_lines: list[str]) -> bool:
    if inline_suffix.strip() == "[]":
        return False
    for line in body_lines:
        trimmed = line.strip()
        if trimmed.startswith("- source_path:"):
            if trimmed.split(":", 1)[1].strip():
                return True
    return False


def inventory_groups_with_apps(content: str) -> list[str]:
    groups: list[str] = []
    pending: str | None = None
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("  - inventory_group:"):
            pending = parse_group_scalar(line.split(":", 1)[1])
            i += 1
            continue
        if pending is None:
            i += 1
            continue
        if not line.startswith("    apps:"):
            i += 1
            continue

        inline_suffix = line[len("    apps:") :]
        body_lines: list[str] = []
        i += 1
        while i < len(lines):
            next_line = lines[i]
            if not next_line.strip():
                break
            indent = len(next_line) - len(next_line.lstrip(" "))
            if indent <= 4:
                break
            body_lines.append(next_line)
            i += 1

        if apps_block_has_source_path(inline_suffix, body_lines):
            groups.append(assert_safe_inventory_group_name(pending))
        pending = None

    return groups


def expand_via_observer(group_name: str) -> list[str]:
    assert_safe_inventory_group_name(group_name)
    encoded = urllib.parse.quote(group_name, safe="")
    url = f"{observer_api_url.rstrip('/')}/api/v1/groups/hierarchy/{encoded}/descendants"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(
            f"::error::Could not expand inventory_group {group_name!r} (HTTP {exc.code})",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as exc:
        print(
            f"::error::Could not expand inventory_group {group_name!r}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    descendants = data.get("descendants") or []
    leaf_groups = data.get("leaf_groups") or []
    if descendants and leaf_groups:
        print(
            f"Expanded parent group {group_name!r} -> {', '.join(leaf_groups)}",
            file=sys.stderr,
        )
        return list(leaf_groups)
    if leaf_groups:
        return list(leaf_groups)
    return [group_name]


def expand_via_cli(group_name: str) -> list[str]:
    assert_safe_inventory_group_name(group_name)
    cli = os.environ.get("DESLICER_CLI", "").strip()
    environment = (
        os.environ.get("DESLICER_ENVIRONMENT", "").strip()
        or os.environ.get("PIN", "").strip()
    )
    cmd = [cli, "inventory", "list", "--log-format", "json"]
    if environment:
        cmd.extend(["--environment", environment])
    try:
        completed = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=25
        )
        parsed = json.loads(completed.stdout)
        if not isinstance(parsed, list):
            raise TypeError("inventory list JSON must be an array")
        groups = parsed
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, TypeError):
        print(
            f"::error::Could not expand inventory_group {group_name!r} via CLI",
            file=sys.stderr,
        )
        sys.exit(1)

    by_name = {
        item.get("name"): item
        for item in groups
        if isinstance(item, dict) and item.get("name")
    }

    def leaf_names(start: str) -> list[str]:
        node = by_name.get(start)
        if node is None:
            return [start]
        children = [child for child in (node.get("children") or []) if child]
        if not children:
            return [start]
        leaves: list[str] = []
        for child in children:
            leaves.extend(leaf_names(child))
        return leaves or [start]

    leaves = leaf_names(group_name)
    if leaves != [group_name]:
        print(
            f"Expanded parent group {group_name!r} -> {', '.join(leaves)}",
            file=sys.stderr,
        )
    return leaves


def expand_to_leaf_groups(group_name: str) -> list[str]:
    if observer_api_url and api_token:
        leaves = expand_via_observer(group_name)
    elif os.environ.get("DESLICER_CLI", "").strip():
        leaves = expand_via_cli(group_name)
    else:
        leaves = [group_name]
    return [assert_safe_inventory_group_name(leaf) for leaf in leaves]


def list_stems() -> list[str]:
    if not root.is_dir():
        return []
    stems: list[str] = []
    for pattern in ("*.yml", "*.yaml"):
        for path in sorted(root.glob(pattern)):
            stem = path.stem
            if stem.lower() == "readme":
                continue
            stems.append(stem)
    return sorted(set(stems))


stems = list_stems()
if pin:
    if pin not in stems:
        print(
            f"::error::No {root}/{pin}.yml (or .yaml). "
            "GitHub Environment name must match the YAML stem.",
            file=sys.stderr,
        )
        sys.exit(1)
    stems = [pin]

include: list[dict[str, str]] = []
seen: set[tuple[str, str]] = set()
for stem in stems:
    content_path: Path | None = None
    for ext in (".yml", ".yaml"):
        candidate = root / f"{stem}{ext}"
        if candidate.is_file():
            content_path = candidate
            break
    if content_path is None:
        continue
    content = content_path.read_text(encoding="utf-8")
    for inventory_group in inventory_groups_with_apps(content):
        for leaf_group in expand_to_leaf_groups(inventory_group):
            key = (stem, leaf_group)
            if key in seen:
                continue
            seen.add(key)
            include.append({"environment": stem, "inventory_group": leaf_group})

include.sort(key=lambda row: (row["environment"], row["inventory_group"]))

payload_obj = {"include": include}
payload = json.dumps(payload_obj, separators=(",", ":"))

if matrix_output_path:
    Path(matrix_output_path).write_text(payload + "\n", encoding="utf-8")

github_output = os.environ["GITHUB_OUTPUT"]
if not include:
    with open(github_output, "a", encoding="utf-8") as handle:
        handle.write('matrix={"include":[]}\n')
        handle.write("has_targets=false\n")
    print(
        "::notice::No destinations with apps under .deslicer/environments/ — skipping plan jobs."
    )
    sys.exit(0)

with open(github_output, "a", encoding="utf-8") as handle:
    handle.write(f"matrix={payload}\n")
    handle.write("has_targets=true\n")

labels = [f"{row['environment']}/{row['inventory_group']}" for row in include]
print(f"Resolved {len(include)} parallel plan job(s): {', '.join(labels)}")
PY
