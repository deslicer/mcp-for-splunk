#!/usr/bin/env bash
# Merge plan-matrix fragments from discover-inventory matrix legs.
#
# Usage: merge-plan-matrix.sh [directory]
#
# Outputs (GITHUB_OUTPUT):
#   matrix      — merged JSON {"include":[…]}
#   has_targets — true when include is non-empty
set -euo pipefail

DIR="${1:-matrices}"

python3 - "${DIR}" <<'PY'
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
includes: list[dict[str, str]] = []

for path in sorted(root.rglob("matrix.json")):
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        continue
    data = json.loads(raw)
    includes.extend(data.get("include") or [])

seen: set[tuple[str, str]] = set()
merged: list[dict[str, str]] = []
for row in includes:
    key = (row["environment"], row["inventory_group"])
    if key in seen:
        continue
    seen.add(key)
    merged.append(row)

merged.sort(key=lambda row: (row["environment"], row["inventory_group"]))
payload = json.dumps({"include": merged}, separators=(",", ":"))

github_output = os.environ["GITHUB_OUTPUT"]
with open(github_output, "a", encoding="utf-8") as handle:
    handle.write(f"matrix={payload}\n")
    if merged:
        handle.write("has_targets=true\n")
    else:
        handle.write("has_targets=false\n")

if merged:
    labels = [f"{row['environment']}/{row['inventory_group']}" for row in merged]
    print(f"Merged {len(merged)} parallel plan job(s): {', '.join(labels)}")
else:
    print("::notice::No plan matrix targets after merge — skipping plan jobs.")
PY
