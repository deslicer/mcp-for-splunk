#!/usr/bin/env bash
# Append changed plan files to $GITHUB_STEP_SUMMARY.
# Reads OBSERVER_API_URL + DESLICER_API_TOKEN; never prints config values (REQ-LOG-007).
set -euo pipefail

PLAN_ID="${1:-}"
if [[ -z "${PLAN_ID}" ]]; then
  echo "::error::plan id required"
  exit 1
fi
if [[ -z "${OBSERVER_API_URL:-}" || -z "${DESLICER_API_TOKEN:-}" ]]; then
  echo "::warning::OBSERVER_API_URL and DESLICER_API_TOKEN unset; skipping changed-files summary"
  exit 0
fi
if [[ -z "${GITHUB_STEP_SUMMARY:-}" ]]; then
  echo "::warning::GITHUB_STEP_SUMMARY unset; skipping changed-files summary"
  exit 0
fi

DETAILS_URL="${OBSERVER_API_URL%/}/api/v1/plans/${PLAN_ID}/details"
TMP="$(mktemp)"
trap 'rm -f "${TMP}"' EXIT

HTTP_CODE="$(
  curl -sS -o "${TMP}" -w "%{http_code}" --connect-timeout 10 --max-time 60 \
    -H "Authorization: Bearer ${DESLICER_API_TOKEN}" \
    -H "Accept: application/json" \
    "${DETAILS_URL}"
)"

if [[ "${HTTP_CODE}" != "200" ]]; then
  echo "::warning::Could not load plan details (HTTP ${HTTP_CODE}); skipping changed-files summary"
  exit 0
fi

python3 - "${TMP}" <<'PY' >>"${GITHUB_STEP_SUMMARY}"
import json
import sys
from collections import Counter

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    body = json.load(fh)

items = body.get("items") or []
if not isinstance(items, list):
    items = []

rows = []
files = []
for item in items:
    if not isinstance(item, dict):
        continue
    change = str(item.get("change_type") or "").strip() or "?"
    target = str(item.get("target_path") or "").strip()
    if not target:
        app = str(item.get("target_app") or "").strip()
        target = app or "(unknown path)"
    section = str(item.get("target_section") or "").strip()
    option = str(item.get("target_option") or "").strip()
    rows.append((change, target, section, option))
    files.append(target)

print("")
print('### Changed files')
print("")
if not rows:
    print("_No change items on this plan._")
    raise SystemExit(0)

unique = sorted(set(files))
print(f"{len(rows)} change item(s) across **{len(unique)}** file(s).")
print("")
print("| File | Changes |")
print("| --- | ---: |")
for path, count in Counter(files).most_common():
    print(f"| `{path}` | {count} |")

print("")
print("<details>")
print("<summary>Change items (path / section / key)</summary>")
print("")
print("| Change | Path | Section | Key |")
print("| --- | --- | --- | --- |")
for change, target, section, option in rows:
    print(f"| `{change}` | `{target}` | `{section}` | `{option}` |")
print("")
print("</details>")
PY
