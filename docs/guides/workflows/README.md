# Workflows Guide

## Overview

Workflows are JSON-defined Splunk troubleshooting procedures. You create, validate, and discover them with these tools:

- `workflow_requirements`: requirements and schema
- `workflow_builder`: create/edit/validate/process workflows
- `list_workflows`: discover available core and contrib workflows

OpenAI-based `workflow_runner` execution was removed (Option C / FastMCP 4 upgrade). Definitions remain for discovery, validation, and external orchestration by your MCP client or custom runner.

## Prerequisites

No OpenAI API key is required for workflow discovery or authoring.

## Where workflows live

- Core: `src/tools/workflows/core/`
- Contrib (your custom workflows): `contrib/workflows/<category>/<workflow_id>.json`

## Core workflows

- `missing_data_troubleshooting`: Systematic 10-step missing data analysis. Follows Splunk’s guidance for inputs and metrics troubleshooting; see [I can't find my data!](https://help.splunk.com/en/splunk-enterprise/administer/troubleshoot/10.0/splunk-web-and-search-problems/i-cant-find-my-data).
- `performance_analysis`: Parallel performance diagnostics (resources, search performance, scheduling).

## Typical flow

1. Call `list_workflows` to discover IDs.
2. Call `workflow_requirements` for schema details.
3. Use `workflow_builder` (`template` → `process` → `validate`) to author JSON.
4. Save under `contrib/workflows/` and rediscover with `list_workflows`.

## Related docs

- [Workflows overview](workflows-overview.md) (legacy runner notes may remain; prefer this page)
- [Contrib guide](../../contrib/contributing.md)
