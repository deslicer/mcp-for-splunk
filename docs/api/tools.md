# MCP Server for Splunk - API Documentation

**Version:** 1.0.0  
**Generated:** 2025-07-03 16:06:23  
**Protocol:** Model Context Protocol (MCP) 2024-11-05

## Introduction

This document provides comprehensive API documentation for all tools available in the MCP Server for Splunk. Each tool is documented with detailed parameter information, return values, usage examples, and integration guidance.

The MCP Server for Splunk provides 20 production-ready tools organized into categories for different use cases including search operations, system administration, data management, and health monitoring.

## Table of Contents

### Tools by Category
- [Admin Tools](#admin-tools)
- [Health Tools](#health-tools)
- [Kvstore Tools](#kvstore-tools)
- [Metadata Tools](#metadata-tools)
- [Search Tools](#search-tools)

### Detailed Tool Documentation
- [`create_kvstore_collection`](#create-kvstore-collection)
- [`create_saved_search`](#create-saved-search)
- [`delete_saved_search`](#delete-saved-search)
- [`execute_saved_search`](#execute-saved-search)
- [`get_configurations`](#get-configurations)
- [`get_kvstore_data`](#get-kvstore-data)
- [`get_latest_feature_health`](#get-latest-feature-health)
- [`get_saved_search_details`](#get-saved-search-details)
- [`get_splunk_health`](#get-splunk-health)
- [`list_apps`](#list-apps)
- [`list_indexes`](#list-indexes)
- [`list_kvstore_collections`](#list-kvstore-collections)
- [`list_saved_searches`](#list-saved-searches)
- [`list_sources`](#list-sources)
- [`list_sourcetypes`](#list-sourcetypes)
- [`list_users`](#list-users)
- [`manage_apps`](#manage-apps)
- [`run_oneshot_search`](#run-oneshot-search)
- [`run_splunk_search`](#run-splunk-search)
- [`update_saved_search`](#update-saved-search)

### Additional Sections
- [API Schemas](#api-schemas)
- [Error Handling](#error-handling)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)

## Overview

The MCP Server for Splunk provides a comprehensive set of tools for interacting with Splunk environments through the Model Context Protocol. All tools are designed for production use with comprehensive error handling, validation, and documentation.

### Tool Categories

- **Admin** (4 tools) - Manage Splunk applications, users, and configuration settings
- **Health** (2 tools) - Monitor Splunk system health and connectivity status
- **Kvstore** (3 tools) - Manage KV Store collections and perform data operations
- **Metadata** (3 tools) - Discover and explore Splunk data sources, indexes, and structure
- **Search** (8 tools) - Execute Splunk searches, manage saved searches, and retrieve search results

### Authentication & Connection

All tools that require Splunk connectivity (`requires_connection: true`) use the configured Splunk connection from the server context. Connection parameters can be overridden on a per-tool basis where supported.

### Error Handling

All tools return standardized response formats:
- **Success responses** include `success: true` and relevant data
- **Error responses** include `success: false`, `error` message, and context
- **Connection errors** are handled gracefully with diagnostic information

## Admin Tools

### `get_configurations`

**Description:** Retrieves Splunk configuration settings from specified .conf files. Access settings from any Splunk configuration file (props.conf, transforms.conf, inputs.conf, outputs.conf, etc.) either by entire file or specific stanza. Returns structured configuration data showing all settings and their values.

**Tags:** configuration, settings, administration
**Requires Connection:** Yes

**Required Parameters:** `conf_file`
**Optional Parameters:** `stanza`

[→ Detailed Documentation](#get-configurations)

### `list_apps`

**Description:** Retrieve comprehensive inventory of all installed Splunk applications including metadata (name, label, version, description, author, visibility status). Returns detailed app catalog with 54+ apps typically found in enterprise environments, including core Splunk apps, add-ons (TAs), custom applications, and third-party integrations. Useful for environment auditing, app management, troubleshooting compatibility issues, and understanding the Splunk ecosystem deployment.

**Tags:** apps, administration, management, inventory, catalog, audit
**Requires Connection:** Yes

**Parameters:** None

[→ Detailed Documentation](#list-apps)

### `list_users`

**Description:** List all Splunk users and their properties

**Tags:** users, administration, management
**Requires Connection:** Yes

**Parameters:** None

[→ Detailed Documentation](#list-users)

### `manage_apps`

**Description:** Enable, disable, or restart Splunk applications

**Tags:** apps, administration, management, actions
**Requires Connection:** Yes

**Required Parameters:** `action`, `app_name`

[→ Detailed Documentation](#manage-apps)

## Health Tools

### `get_latest_feature_health`

**Description:** This tool identifies Splunk features with health issues (warning/critical status) requiring attention

**Tags:** health, monitoring, infrastructure, troubleshooting, issues
**Requires Connection:** Yes

**Optional Parameters:** `max_results`

[→ Detailed Documentation](#get-latest-feature-health)

### `get_splunk_health`

**Description:** Checks Splunk server connectivity and returns health status information including server version, connection status, and system information. Can use server-configured connection or accept custom connection parameters for testing different Splunk instances.

**Tags:** health, status, monitoring
**Requires Connection:** No

**Optional Parameters:** `splunk_host`, `splunk_port`, `splunk_username`, `splunk_password`, `splunk_scheme`, `splunk_verify_ssl`

[→ Detailed Documentation](#get-splunk-health)

## Kvstore Tools

### `create_kvstore_collection`

**Description:** Create a new KV Store collection with optional field definitions

**Tags:** kvstore, collections, create, storage
**Requires Connection:** Yes

**Required Parameters:** `app`, `collection`
**Optional Parameters:** `fields`, `accelerated_fields`, `replicated`

[→ Detailed Documentation](#create-kvstore-collection)

### `get_kvstore_data`

**Description:** Retrieves data from a specific KV Store collection with optional MongoDB-style query filtering. KV Store collections contain structured data that can be queried and filtered. Supports complex queries for finding specific records, filtering by field values, and extracting lookup data for analysis or enrichment purposes.

**Tags:** kvstore, data, query, storage
**Requires Connection:** Yes

**Required Parameters:** `collection`
**Optional Parameters:** `app`, `query`

[→ Detailed Documentation](#get-kvstore-data)

### `list_kvstore_collections`

**Description:** Lists all KV Store collections available in the Splunk environment. KV Store collections are NoSQL data stores used for lookups, storing persistent data, and caching information. Returns collection names, associated apps, and configuration details. Useful for discovering available lookup data and understanding data persistence architecture.

**Tags:** kvstore, collections, storage
**Requires Connection:** Yes

**Optional Parameters:** `app`

[→ Detailed Documentation](#list-kvstore-collections)

## Metadata Tools

### `list_indexes`

**Description:** Retrieves a list of all accessible data indexes from the Splunk instance. Returns customer indexes (excludes internal Splunk system indexes like _internal, _audit for better readability). Useful for discovering available data sources and understanding the data structure of the Splunk environment.

**Tags:** indexes, metadata, discovery
**Requires Connection:** Yes

**Parameters:** None

[→ Detailed Documentation](#list-indexes)

### `list_sources`

**Description:** List all available data sources from the configured Splunk instance

**Tags:** sources, metadata, discovery
**Requires Connection:** Yes

**Parameters:** None

[→ Detailed Documentation](#list-sources)

### `list_sourcetypes`

**Description:** List all available sourcetypes from the configured Splunk instance

**Tags:** sourcetypes, metadata, discovery
**Requires Connection:** Yes

**Parameters:** None

[→ Detailed Documentation](#list-sourcetypes)

## Search Tools

### `create_saved_search`

**Description:** Create a new saved search with configuration options for scheduling and sharing

**Tags:** saved_searches, create, management
**Requires Connection:** Yes

**Required Parameters:** `name`, `search`
**Optional Parameters:** `description`, `earliest_time`, `latest_time`, `app`, `sharing`, `is_scheduled`, `cron_schedule`, `is_visible`

[→ Detailed Documentation](#create-saved-search)

### `delete_saved_search`

**Description:** Delete a saved search with confirmation and safety checks

**Tags:** saved_searches, delete, management
**Requires Connection:** Yes

**Required Parameters:** `name`
**Optional Parameters:** `confirm`, `app`, `owner`

[→ Detailed Documentation](#delete-saved-search)

### `execute_saved_search`

**Description:** Execute a saved search by name with optional time range and parameter overrides

**Tags:** saved_searches, execute, search
**Requires Connection:** Yes

**Required Parameters:** `name`
**Optional Parameters:** `earliest_time`, `latest_time`, `mode`, `max_results`, `app`, `owner`

[→ Detailed Documentation](#execute-saved-search)

### `get_saved_search_details`

**Description:** Get comprehensive details about a specific saved search including configuration and metadata

**Tags:** saved_searches, details, metadata
**Requires Connection:** Yes

**Required Parameters:** `name`
**Optional Parameters:** `app`, `owner`

[→ Detailed Documentation](#get-saved-search-details)

### `list_saved_searches`

**Description:** Lists all saved searches available in the Splunk environment with comprehensive metadata including ownership, scheduling configuration, sharing permissions, and last execution details. Supports filtering by owner, app context, and sharing level to help discover and manage existing search automation and reports.

**Tags:** saved_searches, list, metadata
**Requires Connection:** Yes

**Optional Parameters:** `owner`, `app`, `sharing`, `include_disabled`

[→ Detailed Documentation](#list-saved-searches)

### `run_oneshot_search`

**Description:** Executes a Splunk search query immediately and returns results in a single operation. Best for simple, fast searches that complete quickly (under 30 seconds). Returns up to the specified number of results without creating a persistent search job. Ideal for quick data queries, statistics, and simple reporting.

**Tags:** search, oneshot, quick
**Requires Connection:** Yes

**Required Parameters:** `query`
**Optional Parameters:** `earliest_time`, `latest_time`, `max_results`

[→ Detailed Documentation](#run-oneshot-search)

### `run_splunk_search`

**Description:** Executes a Splunk search query as a background job with progress tracking and detailed statistics. Best for complex, long-running searches that may take more than 30 seconds. Creates a persistent search job that can be monitored for progress and provides detailed execution statistics including scan count, event count, and performance metrics.

**Tags:** search, job, tracking, complex
**Requires Connection:** Yes

**Required Parameters:** `query`
**Optional Parameters:** `earliest_time`, `latest_time`

[→ Detailed Documentation](#run-splunk-search)

### `update_saved_search`

**Description:** Update an existing saved search's configuration including query and scheduling

**Tags:** saved_searches, update, management
**Requires Connection:** Yes

**Required Parameters:** `name`
**Optional Parameters:** `search`, `description`, `earliest_time`, `latest_time`, `is_scheduled`, `cron_schedule`, `is_visible`, `app`, `owner`

[→ Detailed Documentation](#update-saved-search)


## Detailed Tool Documentation

### create_kvstore_collection

**Category:** kvstore  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** kvstore, collections, create, storage  

#### Description

Create a new KV Store collection with optional field definitions

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `app` | `str` | ✅ | `None` | No description available |
| `collection` | `str` | ✅ | `None` | No description available |
| `fields` | `list[dict[str, typing.Any]] | None` | ❌ | `None` | No description available |
| `accelerated_fields` | `dict[str, list[list[str]]] | None` | ❌ | `None` | No description available |
| `replicated` | `bool` | ❌ | `True` | No description available |

#### Returns

**Type:** `dict`

Dict containing creation status and collection details

#### Usage Example

```python
result = await create_kvstore_collection(app="search", collection="my_collection")
```

#### Source Information

**Module:** `src.tools.kvstore.collections`  
**File:** `src/tools/kvstore/collections.py`  
**Line:** 79  

### create_saved_search

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** saved_searches, create, management  

#### Description

Create a new saved search with configuration options for scheduling and sharing

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | `str` | ✅ | `None` | No description available |
| `search` | `str` | ✅ | `None` | No description available |
| `description` | `str` | ❌ | `""` | No description available |
| `earliest_time` | `str` | ❌ | `""` | No description available |
| `latest_time` | `str` | ❌ | `""` | No description available |
| `app` | `str | None` | ❌ | `None` | No description available |
| `sharing` | `Literal` | ❌ | `"user"` | No description available |
| `is_scheduled` | `bool` | ❌ | `False` | No description available |
| `cron_schedule` | `str` | ❌ | `""` | No description available |
| `is_visible` | `bool` | ❌ | `True` | No description available |

#### Returns

**Type:** `dict`

Dict containing:
- name: Name of the created saved search
- created: Whether creation was successful
- configuration: Applied configuration

#### Usage Example

```python
result = await create_saved_search(name="my_saved_search", search="index=web_logs status=500 | head 10")
```

#### Additional Examples

create_saved_search(
name="Daily Error Count",
search="index=main error | stats count",
description="Count of daily errors",
earliest_time="-24h@h",
latest_time="@h",
is_scheduled=True,
cron_schedule="0 8 * * *"
)

#### Source Information

**Module:** `src.tools.search.saved_search_tools`  
**File:** `src/tools/search/saved_search_tools.py`  
**Line:** 390  

### delete_saved_search

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** saved_searches, delete, management  

#### Description

Delete a saved search with confirmation and safety checks

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | `str` | ✅ | `None` | No description available |
| `confirm` | `bool` | ❌ | `False` | No description available |
| `app` | `str | None` | ❌ | `None` | No description available |
| `owner` | `str | None` | ❌ | `None` | No description available |

#### Returns

**Type:** `dict`

Dict containing:
- name: Name of the saved search
- deleted: Whether deletion was successful
- was_scheduled: Whether the deleted search was scheduled

#### Usage Example

```python
result = await delete_saved_search(name="my_saved_search")
```

#### Additional Examples

delete_saved_search(
name="Old Test Search",
confirm=True
)

#### Source Information

**Module:** `src.tools.search.saved_search_tools`  
**File:** `src/tools/search/saved_search_tools.py`  
**Line:** 708  

### execute_saved_search

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** saved_searches, execute, search  

#### Description

Execute a saved search by name with optional time range and parameter overrides

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | `str` | ✅ | `None` | No description available |
| `earliest_time` | `str | None` | ❌ | `None` | No description available |
| `latest_time` | `str | None` | ❌ | `None` | No description available |
| `mode` | `Literal` | ❌ | `"oneshot"` | No description available |
| `max_results` | `int` | ❌ | `100` | No description available |
| `app` | `str | None` | ❌ | `None` | No description available |
| `owner` | `str | None` | ❌ | `None` | No description available |

#### Returns

**Type:** `dict`

Dict containing:
- saved_search_name: Name of the executed saved search
- results: List of search results
- results_count: Number of results returned
- execution_mode: Mode used for execution
- job_id: Search job ID (if job mode)
- duration: Execution time in seconds

#### Usage Example

```python
result = await execute_saved_search(name="my_saved_search")
```

#### Additional Examples

execute_saved_search(
name="Security Alerts",
earliest_time="-1h",
mode="job"
)

#### Source Information

**Module:** `src.tools.search.saved_search_tools`  
**File:** `src/tools/search/saved_search_tools.py`  
**Line:** 155  

### get_configurations

**Category:** admin  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** configuration, settings, administration  

#### Description

Retrieves Splunk configuration settings from specified .conf files. Access settings from any Splunk configuration file (props.conf, transforms.conf, inputs.conf, outputs.conf, etc.) either by entire file or specific stanza. Returns structured configuration data showing all settings and their values.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `conf_file` | `str` | ✅ | `None` | Configuration file name without .conf extension (e.g., 'props', 'transforms', 'inputs', 'outputs', 'server', 'web') |
| `stanza` | `str | None` | ❌ | `None` | Specific stanza name within the conf file to retrieve. If not provided, returns all stanzas in the file. |

#### Returns

**Type:** `dict`

Dict containing configuration settings with status, file name, and configuration data

#### Usage Example

```python
result = await get_configurations(conf_file="props")
```

#### Source Information

**Module:** `src.tools.admin.config`  
**File:** `src/tools/admin/config.py`  
**Line:** 13  

### get_kvstore_data

**Category:** kvstore  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** kvstore, data, query, storage  

#### Description

Retrieves data from a specific KV Store collection with optional MongoDB-style query filtering. KV Store collections contain structured data that can be queried and filtered. Supports complex queries for finding specific records, filtering by field values, and extracting lookup data for analysis or enrichment purposes.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `collection` | `str` | ✅ | `None` | No description available |
| `app` | `str | None` | ❌ | `None` | No description available |
| `query` | `dict | None` | ❌ | `None` | No description available |

#### Returns

**Type:** `dict`

Dict containing retrieved documents

#### Usage Example

```python
result = await get_kvstore_data(collection="my_collection", query="index=main error | stats count")
```

#### Source Information

**Module:** `src.tools.kvstore.data`  
**File:** `src/tools/kvstore/data.py`  
**Line:** 13  

### get_latest_feature_health

**Category:** health  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** health, monitoring, infrastructure, troubleshooting, issues  

#### Description

This tool identifies Splunk features with health issues (warning/critical status) requiring attention

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `max_results` | `int` | ❌ | `100` | No description available |

#### Returns

**Type:** `dict`

Dict containing:
- results: List of features with health issues (warning/critical) with host, feature, and status
- results_count: Number of problematic features found
- query_executed: The actual query that was executed
- duration: Time taken to execute the query

#### Usage Example

```python
result = await get_latest_feature_health()
```

#### Additional Examples

get_latest_feature_health(max_results=50) -> {
"results": [
{"host": "splunk-server-01", "feature": "IndexProcessor", "status": "warning"},
{"host": "splunk-server-02", "feature": "SearchHead", "status": "critical"}
],
"results_count": 2,
"query_executed": "index=_internal...",
"duration": 1.234
}

Note: Healthy features are excluded from results to focus on actionable issues.

#### Source Information

**Module:** `contrib.tools.health.get_degraded_splunk_features`  
**File:** `contrib/tools/health/get_degraded_splunk_features.py`  
**Line:** 15  

### get_saved_search_details

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** saved_searches, details, metadata  

#### Description

Get comprehensive details about a specific saved search including configuration and metadata

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | `str` | ✅ | `None` | No description available |
| `app` | `str | None` | ❌ | `None` | No description available |
| `owner` | `str | None` | ❌ | `None` | No description available |

#### Returns

**Type:** `dict`

Dict containing comprehensive saved search details:
- basic_info: Name, description, search query
- scheduling: Schedule configuration and status
- dispatch: Time range and execution settings
- permissions: Access control and sharing
- actions: Alert actions configuration
- metadata: Creation and modification timestamps

#### Usage Example

```python
result = await get_saved_search_details(name="my_saved_search")
```

#### Additional Examples

get_saved_search_details(name="Security Alerts")

#### Source Information

**Module:** `src.tools.search.saved_search_tools`  
**File:** `src/tools/search/saved_search_tools.py`  
**Line:** 838  

### get_splunk_health

**Category:** health  
**Version:** 1.0.0  
**Requires Connection:** No  
**Tags:** health, status, monitoring  

#### Description

Checks Splunk server connectivity and returns health status information including server version, connection status, and system information. Can use server-configured connection or accept custom connection parameters for testing different Splunk instances.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `splunk_host` | `str | None` | ❌ | `None` | Splunk server hostname or IP address. If not provided, uses the server's configured connection. |
| `splunk_port` | `int | None` | ❌ | `None` | Splunk management port (typically 8089). Defaults to server configuration. |
| `splunk_username` | `str | None` | ❌ | `None` | Splunk username for authentication. Uses server configuration if not provided. |
| `splunk_password` | `str | None` | ❌ | `None` | Splunk password for authentication. Uses server configuration if not provided. |
| `splunk_scheme` | `str | None` | ❌ | `None` | Connection scheme ('http' or 'https'). Defaults to server configuration. |
| `splunk_verify_ssl` | `bool | None` | ❌ | `None` | Whether to verify SSL certificates. Defaults to server configuration. |

#### Returns

**Type:** `dict`

Dict containing connection status, Splunk version, server name, and connection source

#### Usage Example

```python
result = await get_splunk_health()
```

#### Source Information

**Module:** `src.tools.health.status`  
**File:** `src/tools/health/status.py`  
**Line:** 13  

### list_apps

**Category:** admin  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** apps, administration, management, inventory, catalog, audit  

#### Description

Retrieve comprehensive inventory of all installed Splunk applications including metadata (name, label, version, description, author, visibility status). Returns detailed app catalog with 54+ apps typically found in enterprise environments, including core Splunk apps, add-ons (TAs), custom applications, and third-party integrations. Useful for environment auditing, app management, troubleshooting compatibility issues, and understanding the Splunk ecosystem deployment.

#### Parameters

This tool takes no parameters.

#### Returns

**Type:** `dict`

Dict containing:
- status: "success" or "error"
- count: Total number of apps found
- apps: List of app objects with detailed metadata

Typical enterprise environments contain 50+ apps including:
- Core Splunk apps (search, launcher, dmc)
- Technology Add-ons (Splunk_TA_*)
- Custom business applications
- Third-party integrations and visualizations

#### Usage Example

```python
result = await list_apps()
```

#### Source Information

**Module:** `src.tools.admin.apps`  
**File:** `src/tools/admin/apps.py`  
**Line:** 13  

### list_indexes

**Category:** metadata  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** indexes, metadata, discovery  

#### Description

Retrieves a list of all accessible data indexes from the Splunk instance. Returns customer indexes (excludes internal Splunk system indexes like _internal, _audit for better readability). Useful for discovering available data sources and understanding the data structure of the Splunk environment.

#### Parameters

This tool takes no parameters.

#### Returns

**Type:** `dict`

Dict containing:
- indexes: Sorted list of customer index names (excludes internal indexes)
- count: Number of customer indexes found
- total_count_including_internal: Total number of all indexes including system indexes

#### Usage Example

```python
result = await list_indexes()
```

#### Source Information

**Module:** `src.tools.metadata.indexes`  
**File:** `src/tools/metadata/indexes.py`  
**Line:** 13  

### list_kvstore_collections

**Category:** kvstore  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** kvstore, collections, storage  

#### Description

Lists all KV Store collections available in the Splunk environment. KV Store collections are NoSQL data stores used for lookups, storing persistent data, and caching information. Returns collection names, associated apps, and configuration details. Useful for discovering available lookup data and understanding data persistence architecture.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `app` | `str | None` | ❌ | `None` | No description available |

#### Returns

**Type:** `dict`

Dict containing collections and their properties

#### Usage Example

```python
result = await list_kvstore_collections()
```

#### Source Information

**Module:** `src.tools.kvstore.collections`  
**File:** `src/tools/kvstore/collections.py`  
**Line:** 14  

### list_saved_searches

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** saved_searches, list, metadata  

#### Description

Lists all saved searches available in the Splunk environment with comprehensive metadata including ownership, scheduling configuration, sharing permissions, and last execution details. Supports filtering by owner, app context, and sharing level to help discover and manage existing search automation and reports.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `owner` | `str | None` | ❌ | `None` | No description available |
| `app` | `str | None` | ❌ | `None` | No description available |
| `sharing` | `Optional` | ❌ | `None` | No description available |
| `include_disabled` | `bool` | ❌ | `False` | No description available |

#### Returns

**Type:** `dict`

Dict containing:
- saved_searches: List of saved search metadata
- total_count: Total number of saved searches found
- filtered_count: Number after applying filters

#### Usage Example

```python
result = await list_saved_searches()
```

#### Additional Examples

list_saved_searches(owner="admin", app="search", include_disabled=True)

#### Source Information

**Module:** `src.tools.search.saved_search_tools`  
**File:** `src/tools/search/saved_search_tools.py`  
**Line:** 18  

### list_sources

**Category:** metadata  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** sources, metadata, discovery  

#### Description

List all available data sources from the configured Splunk instance

#### Parameters

This tool takes no parameters.

#### Returns

**Type:** `dict`

Dict containing list of sources and count

#### Usage Example

```python
result = await list_sources()
```

#### Source Information

**Module:** `src.tools.metadata.sources`  
**File:** `src/tools/metadata/sources.py`  
**Line:** 14  

### list_sourcetypes

**Category:** metadata  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** sourcetypes, metadata, discovery  

#### Description

List all available sourcetypes from the configured Splunk instance

#### Parameters

This tool takes no parameters.

#### Returns

**Type:** `dict`

Dict containing list of sourcetypes and count

#### Usage Example

```python
result = await list_sourcetypes()
```

#### Source Information

**Module:** `src.tools.metadata.sourcetypes`  
**File:** `src/tools/metadata/sourcetypes.py`  
**Line:** 14  

### list_users

**Category:** admin  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** users, administration, management  

#### Description

List all Splunk users and their properties

#### Parameters

This tool takes no parameters.

#### Returns

**Type:** `dict`

Dict containing list of users and their properties

#### Usage Example

```python
result = await list_users()
```

#### Source Information

**Module:** `src.tools.admin.users`  
**File:** `src/tools/admin/users.py`  
**Line:** 13  

### manage_apps

**Category:** admin  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** apps, administration, management, actions  

#### Description

Enable, disable, or restart Splunk applications

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | `str` | ✅ | `None` | No description available |
| `app_name` | `str` | ✅ | `None` | No description available |

#### Returns

**Type:** `dict`

Dict containing operation result

#### Usage Example

```python
result = await manage_apps(action="example_value", app_name="example_value")
```

#### Source Information

**Module:** `src.tools.admin.app_management`  
**File:** `src/tools/admin/app_management.py`  
**Line:** 16  

### run_oneshot_search

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** search, oneshot, quick  

#### Description

Executes a Splunk search query immediately and returns results in a single operation. Best for simple, fast searches that complete quickly (under 30 seconds). Returns up to the specified number of results without creating a persistent search job. Ideal for quick data queries, statistics, and simple reporting.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `str` | ✅ | `None` | No description available |
| `earliest_time` | `str` | ❌ | `"-15m"` | No description available |
| `latest_time` | `str` | ❌ | `"now"` | No description available |
| `max_results` | `int` | ❌ | `100` | No description available |

#### Returns

**Type:** `dict`

Dict containing search results, count, executed query, and execution duration

#### Usage Example

```python
result = await run_oneshot_search(query="index=main error | stats count")
```

#### Source Information

**Module:** `src.tools.search.oneshot_search`  
**File:** `src/tools/search/oneshot_search.py`  
**Line:** 15  

### run_splunk_search

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** search, job, tracking, complex  

#### Description

Executes a Splunk search query as a background job with progress tracking and detailed statistics. Best for complex, long-running searches that may take more than 30 seconds. Creates a persistent search job that can be monitored for progress and provides detailed execution statistics including scan count, event count, and performance metrics.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | `str` | ✅ | `None` | No description available |
| `earliest_time` | `str` | ❌ | `"-24h"` | No description available |
| `latest_time` | `str` | ❌ | `"now"` | No description available |

#### Returns

**Type:** `dict`

Dict containing search results, job statistics, progress information, and performance metrics

#### Usage Example

```python
result = await run_splunk_search(query="index=main error | stats count")
```

#### Source Information

**Module:** `src.tools.search.job_search`  
**File:** `src/tools/search/job_search.py`  
**Line:** 15  

### update_saved_search

**Category:** search  
**Version:** 1.0.0  
**Requires Connection:** Yes  
**Tags:** saved_searches, update, management  

#### Description

Update an existing saved search's configuration including query and scheduling

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | `str` | ✅ | `None` | No description available |
| `search` | `str | None` | ❌ | `None` | No description available |
| `description` | `str | None` | ❌ | `None` | No description available |
| `earliest_time` | `str | None` | ❌ | `None` | No description available |
| `latest_time` | `str | None` | ❌ | `None` | No description available |
| `is_scheduled` | `bool | None` | ❌ | `None` | No description available |
| `cron_schedule` | `str | None` | ❌ | `None` | No description available |
| `is_visible` | `bool | None` | ❌ | `None` | No description available |
| `app` | `str | None` | ❌ | `None` | No description available |
| `owner` | `str | None` | ❌ | `None` | No description available |

#### Returns

**Type:** `dict`

Dict containing:
- name: Name of the updated saved search
- updated: Whether update was successful
- changes_made: List of properties that were changed

#### Usage Example

```python
result = await update_saved_search(name="my_saved_search", search="index=web_logs status=500 | head 10")
```

#### Additional Examples

update_saved_search(
name="Daily Error Count",
description="Updated: Count of daily errors with severity",
search="index=main error | stats count by severity",
is_scheduled=False
)

#### Source Information

**Module:** `src.tools.search.saved_search_tools`  
**File:** `src/tools/search/saved_search_tools.py`  
**Line:** 541  


## API Schemas

### Standard Response Format

All tools return responses in a standardized format:

```json
{
  "success": true,
  "data": {
    // Tool-specific response data
  },
  "metadata": {
    "tool": "tool_name",
    "execution_time": "2024-01-01T12:00:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response Format

```json
{
  "success": false,
  "error": "Error description",
  "error_code": "ERROR_CODE",
  "details": {
    // Additional error context
  },
  "metadata": {
    "tool": "tool_name",
    "execution_time": "2024-01-01T12:00:00Z"
  }
}
```

### Connection Parameters

Tools that support connection overrides accept these parameters:

```json
{
  "splunk_host": "splunk.example.com",
  "splunk_port": 8089,
  "splunk_username": "admin",
  "splunk_password": "password",
  "splunk_scheme": "https",
  "splunk_verify_ssl": true
}
```

## Error Handling

### Common Error Codes

- `CONNECTION_ERROR` - Unable to connect to Splunk
- `AUTHENTICATION_ERROR` - Invalid credentials
- `PERMISSION_ERROR` - Insufficient permissions
- `VALIDATION_ERROR` - Invalid parameters
- `TIMEOUT_ERROR` - Operation timed out
- `NOT_FOUND_ERROR` - Resource not found
- `INTERNAL_ERROR` - Server error

### Best Practices

1. **Always check the `success` field** in responses
2. **Handle connection errors gracefully** with retry logic
3. **Validate parameters** before making tool calls
4. **Use appropriate timeouts** for long-running operations
5. **Log errors with context** for debugging

## Authentication

Authentication is handled at the server level. Tools inherit the connection context from the server configuration. Individual tools can override connection parameters where supported.

## Rate Limiting

The server implements connection pooling and request throttling to prevent overwhelming Splunk instances. Consider:

- **Batch operations** when possible
- **Reasonable time ranges** for search operations  
- **Pagination** for large result sets
- **Appropriate delays** between consecutive calls

---

## Support

- **Documentation:** [GitHub Repository](https://github.com/your-org/mcp-server-for-splunk)
- **Issues:** [Report Issues](https://github.com/your-org/mcp-server-for-splunk/issues)
- **Discussions:** [Community Support](https://github.com/your-org/mcp-server-for-splunk/discussions)

---

*This documentation was automatically generated from tool metadata and source code analysis.*  
*Last updated: 2025-07-03 16:06:23*