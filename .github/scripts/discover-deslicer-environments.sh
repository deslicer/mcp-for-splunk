#!/usr/bin/env bash
# List tenant stems from `.deslicer/environments/*.yml`.
# Convention: GitHub Environment name === YAML stem === `--environment`.
# Do not read repository variable DESLICER_ENVIRONMENT.
set -euo pipefail

PIN="${PIN:-}"
MODE="${MODE:-matrix}"
root=".deslicer/environments"

stems=()
if [[ -d "${root}" ]]; then
  while IFS= read -r -d '' path; do
    stem="$(basename "${path}")"
    stem="${stem%.*}"
    if [[ "${stem}" == "README" || "${stem}" == "readme" ]]; then
      continue
    fi
    stems+=("${stem}")
  done < <(find "${root}" \( -name '*.yml' -o -name '*.yaml' \) -print0 | sort -z)
fi

if [[ -n "${PIN}" ]]; then
  found=0
  for stem in "${stems[@]+"${stems[@]}"}"; do
    if [[ "${stem}" == "${PIN}" ]]; then
      found=1
      break
    fi
  done
  if [[ "${found}" -ne 1 ]]; then
    echo "::error::No ${root}/${PIN}.yml (or .yaml). GitHub Environment name must match the YAML stem."
    exit 1
  fi
  stems=("${PIN}")
fi

if [[ "${#stems[@]}" -eq 0 ]]; then
  echo "::error::Add at least one ${root}/<tenant-slug>.yml. CI discovers the tenant from that filename."
  exit 1
fi

if [[ "${MODE}" == "one" ]]; then
  if [[ "${#stems[@]}" -ne 1 ]]; then
    echo "::error::Multiple environment files (${stems[*]}). Pass the environment workflow input."
    exit 1
  fi
  echo "target=${stems[0]}" >> "${GITHUB_OUTPUT}"
  echo "Resolved environment: ${stems[0]}"
  exit 0
fi

python3 - "${stems[@]}" <<'PY'
import json
import os
import sys

stems = sys.argv[1:]
payload = json.dumps(stems, separators=(",", ":"))
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
    handle.write(f"targets={payload}\n")
print(f"Resolved environments: {', '.join(stems)}")
PY
