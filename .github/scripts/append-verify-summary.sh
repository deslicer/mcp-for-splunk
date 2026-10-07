#!/usr/bin/env bash
# Append verify outcome (including CLI error text) to $GITHUB_STEP_SUMMARY.
set -euo pipefail

if [[ -z "${GITHUB_STEP_SUMMARY:-}" ]]; then
  echo "::warning::GITHUB_STEP_SUMMARY unset; skipping verify summary"
  exit 0
fi

PLAN_ID="${PLAN_ID:-}"
ENVIRONMENT="${ENVIRONMENT:-}"
OUTCOME="${OUTCOME:-}"
EXIT_CODE="${EXIT_CODE:-}"
VERIFY_ERROR="${VERIFY_ERROR:-}"
PLAN_STATUS="${PLAN_STATUS:-}"
PLAN_SUMMARY="${PLAN_SUMMARY:-}"
DIFF_TOTAL="${DIFF_TOTAL:-}"
DIFF_ADDITIONS="${DIFF_ADDITIONS:-}"
DIFF_MODIFICATIONS="${DIFF_MODIFICATIONS:-}"
DIFF_DELETIONS="${DIFF_DELETIONS:-}"
DESLICER_API_URL="${DESLICER_API_URL:-}"

read_github_output() {
  local key="$1"
  if [[ -z "${GITHUB_OUTPUT:-}" || ! -f "${GITHUB_OUTPUT}" ]]; then
    return 0
  fi
  grep -m1 "^${key}=" "${GITHUB_OUTPUT}" | cut -d= -f2- || true
}

if [[ -z "${PLAN_STATUS}" ]]; then
  PLAN_STATUS="$(read_github_output plan_status)"
fi
if [[ -z "${PLAN_SUMMARY}" ]]; then
  PLAN_SUMMARY="$(read_github_output plan_summary)"
fi
if [[ -z "${DIFF_TOTAL}" ]]; then
  DIFF_TOTAL="$(read_github_output diff_total)"
fi
if [[ -z "${DIFF_ADDITIONS}" ]]; then
  DIFF_ADDITIONS="$(read_github_output diff_additions)"
fi
if [[ -z "${DIFF_MODIFICATIONS}" ]]; then
  DIFF_MODIFICATIONS="$(read_github_output diff_modifications)"
fi
if [[ -z "${DIFF_DELETIONS}" ]]; then
  DIFF_DELETIONS="$(read_github_output diff_deletions)"
fi

{
  echo "## Deslicer verify"
  echo ""
  echo "| Field | Value |"
  echo "| --- | --- |"
  if [[ -n "${PLAN_ID}" ]]; then
    echo "| Plan ID | \`${PLAN_ID}\` |"
  fi
  if [[ -n "${ENVIRONMENT}" ]]; then
    echo "| Environment | \`${ENVIRONMENT}\` |"
  fi
  if [[ -n "${OUTCOME}" ]]; then
    echo "| Result | **${OUTCOME}** |"
  fi
  if [[ -n "${EXIT_CODE}" ]]; then
    echo "| Exit code | ${EXIT_CODE} |"
  fi
  if [[ -n "${PLAN_STATUS}" ]]; then
    echo "| Plan status | **${PLAN_STATUS}** |"
  fi
  if [[ -n "${PLAN_SUMMARY}" ]]; then
    echo "| Summary | ${PLAN_SUMMARY} |"
  fi
  if [[ -n "${DIFF_TOTAL}" ]]; then
    echo "| Changes | ${DIFF_TOTAL} (+${DIFF_ADDITIONS:-0} / ~${DIFF_MODIFICATIONS:-0} / -${DIFF_DELETIONS:-0}) |"
  fi
  if [[ -n "${DESLICER_API_URL}" && -n "${PLAN_ID}" ]]; then
    PORTAL="${DESLICER_API_URL%/}/dashboard/dap/plans/${PLAN_ID}"
    echo "| Portal | [Open in Deslicer](${PORTAL}) |"
  fi
} >> "${GITHUB_STEP_SUMMARY}"

if [[ "${OUTCOME}" == "failure" && -n "${VERIFY_ERROR}" ]]; then
  ERROR_MSG="$(printf '%s' "${VERIFY_ERROR}" | tr -d '\r' | cut -c1-200)"
  if [[ -n "${ERROR_MSG}" ]]; then
    {
      echo ""
      echo "### Error"
      echo ""
      echo '```'
      echo "${ERROR_MSG}"
      echo '```'
    } >> "${GITHUB_STEP_SUMMARY}"
    echo "::error::${ERROR_MSG}"
  fi
fi
