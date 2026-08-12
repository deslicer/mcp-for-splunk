# AGENTS.md — coding agents in this repo

Instructions for AI coding agents (Cursor, Codex, Copilot, Claude Code, etc.)
working **in this repository**. For agents that only *call* the running MCP
server, prefer [`llms.txt`](llms.txt) and
[`mcp_itsi/llms.txt`](mcp_itsi/llms.txt).

## Project overview

- **Product**: MCP Server for Splunk — FastMCP 4 / MCP SDK v2 tools, resources,
  and prompts over Splunk Enterprise/Cloud (+ optional ITSI plugin).
- **Runtime pin**: `fastmcp==4.0.0b2` (see `pyproject.toml` / `uv.lock`).
- **Layout**:
  - `src/` — core server, tools, resources, middleware
  - `mcp_itsi/` — ITSI plugin package (also packaged under `packaging/mcp-itsi-server`)
  - `contrib/` — community tools/workflows
  - `scripts/` — live probes and operator helpers
  - `docs/` — human docs; follow `docs/readme-guide.md` when editing Markdown
  - `tests/` — pytest suite

## Setup

```bash
cp env.example .env   # fill Splunk host + token or user/password
uv sync --extra dev
```

Useful entry points:

```bash
uv run mcp-server --local          # local HTTP defaults (sessionless)
uv run python src/server.py --host 127.0.0.1 --port 8014
```

## Build / lint / test

```bash
uv run ruff check src/ tests/
uv run mypy src/core/client_config_cache.py   # targeted; full mypy via CI lint job
uv run pytest tests/ -q --ignore=tests/integration
```

Live Splunk (credentials via env, never commit secrets):

```bash
uv run python scripts/test_live_splunk_tools.py
uv run python scripts/test_live_mcp_client.py          # in-memory FastMCP Client
uv run python scripts/test_sessionless_http.py         # needs MCP_URL + SPLUNK_TOKEN
```

Always regenerate the lockfile when changing deps:

```bash
uv lock
uv lock --check
```

Dependabot PRs that only edit `pyproject.toml` floors without `uv.lock` are incomplete.

## Conventions

- **Python**: 3.10+; keep modules focused; prefer composition over large god-files.
- **File size**: stay under ~500 lines; split earlier around ~400.
- **Imports**: top of module only (no inline imports unless a documented cycle).
- **Markdown**: follow `.cursorrules` / `docs/readme-guide.md` (one H1, short
  paragraphs, fenced code with language tags).
- **HTTP client modes**: sessionless is the default
  (`MCP_STATELESS_HTTP=true`). See
  `docs/guides/configuration/http-client-modes.md`.
- **Workflows**: OpenAI Agents `workflow_runner` was removed (Option C). Keep
  JSON discovery/authoring tools only (`list_workflows`, `workflow_builder`,
  `workflow_requirements`).
- **Saved-search ACL**: read ownership from `entity.access` via
  `src/tools/search/saved_search_acl.py` — not `content['eai:acl']`.
- **ITSI packaging**: `mcp_itsi/` and `packaging/mcp-itsi-server/mcp_itsi/` may
  be hardlinked — edit once, verify both paths if unsure.

## Security rules for agents

- Never commit `.env`, tokens, passwords, or live host credentials.
- Prefer `X-Splunk-Token` / `SPLUNK_TOKEN` over passwords in examples.
- Do not log raw `splunk_token`, `splunk_password`, or `splunk_session_token`.
- Default TLS verification is **true**; lab stacks must set
  `SPLUNK_VERIFY_SSL=false` explicitly.
- Avoid adding `openai` / `openai-agents` back to the default install.

## Git / PR habits

- Do not push to `main` or force-push shared branches unless the user asks.
- Do not amend commits you did not create in this session.
- Squash-friendly commits: short why-focused subject.
- After squash-merges, rebase follow-up branches onto `origin/main` (do not
  merge the deleted feature-branch history).

## Where to look first

| Task | Start here |
|------|------------|
| Server / middleware / HTTP | `src/server.py`, `src/core/` |
| Splunk tools | `src/tools/` |
| Client config headers | `docs/guides/configuration/client_configuration.md` |
| Sessionless vs session HTTP | `docs/guides/configuration/http-client-modes.md` |
| ITSI tools / schemas | `mcp_itsi/`, `mcp_itsi/llms.txt` |
| Contrib tools | `contrib/README.md` |

## Optional nested agent docs

- ITSI usage for LLM operators: `mcp_itsi/llms.txt`
- Cursor markdown rules: `.cursorrules`
