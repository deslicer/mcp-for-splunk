# Product Requirements Document: Splunk MCP Server (MVP)

## 1. Introduction
The Splunk MCP Server is an open-source project designed to enable seamless interaction between Large Language Models (LLMs), AI agents, and Splunk instances (Enterprise/Cloud) via the Model Context Protocol (MCP). This Minimum Viable Product (MVP) focuses on establishing the core framework and essential tools to prove the concept and provide initial utility.

## 2. Goals
* Deliver a functional MCP server exposing basic Splunk read (list indexes) and search capabilities.
* Enable testing with MCP clients, particularly IDEs like Cursor, and a proof-of-concept Google ADK agent.
* Provide a solid foundation for future community contributions of new Splunk tools.
* Package the server for easy local deployment and testing using Docker.

## 3. Features (MVP Scope)

**F1: MCP Server Core**
* **F1.1:** Server setup using the `modelcontext` Python SDK.
* **F1.2:** Secure and configurable Splunk connection (supporting host, port, and authentication via environment variables for token or username/password).
* **F1.3:** Dockerfile and `docker-compose.yml` for straightforward local execution and development.
* **F1.4:** Basic logging for server operations and error handling.
* **F1.5:** Health check endpoint (e.g., `/health`) to verify server status and Splunk connectivity.

**F2: Splunk Tool - `list_splunk_indexes`**
* **F2.1: Tool Definition:**
    * **Name:** `list_splunk_indexes`
    * **Description:** "Retrieves a list of all accessible indexes from the configured Splunk instance."
    * **Parameters:** None.
    * **Returns:** An object containing a list of index names (e.g., `{"indexes": ["main", "_internal", "web"]}`).
* **F2.2: Implementation:** Utilizes the Splunk Python SDK to fetch and return index names.

**F3: Splunk Tool - `run_splunk_search`**
* **F3.1: Tool Definition:**
    * **Name:** `run_splunk_search`
    * **Description:** "Executes a Splunk Search Processing Language (SPL) query and returns the results. Use this for specific data queries."
    * **Parameters:**
        * `query` (string, required): The SPL query.
        * `earliest_time` (string, optional, default: "-15m"): Search start time.
        * `latest_time` (string, optional, default: "now"): Search end time.
        * `max_results` (integer, optional, default: 50): Maximum number of results to return.
    * **Returns:** An object containing a list of search results (e.g., `{"search_results": [{"_time": "...", "field1": "val1"}, ...]}`).
* **F3.2: Implementation:** Uses the Splunk Python SDK's `oneshot` search capability. Includes parameter handling and basic result formatting.

**F4: Google ADK Agent (Proof of Concept)**
* **F4.1:** Minimal Google ADK agent setup as a separate demonstration project.
* **F4.2:** Agent capable of calling at least one of the Splunk MCP tools (e.g., `list_splunk_indexes` or a predefined `run_splunk_search`) and displaying/logging the result. This demonstrates end-to-end functionality.

**F5: Documentation & Repository**
* **F5.1:** Public GitHub repository with an open-source license (e.g., MIT or Apache 2.0).
* **F5.2:** Comprehensive `README.md` detailing MVP setup, configuration for Splunk connection, how to run the server, and instructions for the ADK agent PoC.
* **F5.3:** Basic `CONTRIBUTING.md` to guide potential contributors.

## 4. Non-Goals (For MVP)
* A comprehensive toolset beyond the two defined (`list_splunk_indexes`, `run_splunk_search`).
* Advanced Splunk features (e.g., real-time searches, search job management beyond oneshot, input/data modification, advanced configuration object management like macros or KV Store manipulation).
* User management, authentication, or authorization for the MCP server itself (beyond Splunk connection auth).
* Production-grade hardening, extensive CI/CD pipelines, or advanced scalability features.
* GUI/Web UI for the MCP server.

## 5. Success Metrics (MVP)
* The MCP server runs successfully in a Docker container.
* The server can connect to a configured Splunk instance (Cloud or Enterprise).
* Both `list_splunk_indexes` and `run_splunk_search` tools are discoverable via the MCP `/tools` endpoint.
* Both tools are invokable via the MCP `/run_tool` endpoint and return correct data from Splunk.
* An MCP-compatible IDE (e.g., Cursor) can successfully discover and use the exposed tools.
* The proof-of-concept Google ADK agent successfully calls an MCP tool and processes the response.
* The code, Docker configuration, and initial documentation (README, license, basic contributing guidelines) are available on GitHub.