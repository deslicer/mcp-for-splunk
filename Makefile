.PHONY: help install test test-unit test-integration test-fast test-all lint format clean run docker-up docker-down

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync --dev

test: ## Run all tests
	uv run pytest tests/ -v

test-unit: ## Run only unit tests
	uv run pytest tests/ -v -m "unit"

test-integration: ## Run only integration tests
	uv run pytest tests/ -v -m "integration"

test-fast: ## Run tests excluding slow ones
	uv run pytest tests/ -v -m "not slow"

test-all: ## Run all tests including slow ones
	uv run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-connections: ## Test only MCP connections
	uv run pytest tests/test_mcp_server.py::TestMCPConnections -v

test-health: ## Test MCP server health checks
	uv run pytest tests/test_mcp_server.py::TestMCPConnections::test_health_resource tests/test_mcp_server.py::TestSplunkTools::test_splunk_health_check -v

lint: ## Run linting with ruff
	uv run ruff check src/ tests/
	uv run mypy src/

format: ## Format code with black and ruff
	uv run black src/ tests/
	uv run ruff check --fix src/ tests/

clean: ## Clean build artifacts
	rm -rf .pytest_cache
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

run: ## Run the MCP server locally
	uv run python src/server.py

run-inspector: ## Run with MCP Inspector
	uv run python -m mcp.debug_inspector src/server.py

docker-up: ## Start Docker containers
	docker-compose up -d

docker-down: ## Stop Docker containers
	docker-compose down

docker-logs: ## Show Docker logs
	docker-compose logs -f mcp-server

docker-rebuild: ## Rebuild and restart the MCP server container
	docker-compose up -d --build mcp-server

# Development workflow targets
dev-setup: install docker-up ## Complete development setup
	@echo "Development environment ready!"
	@echo "Run 'make test-connections' to verify everything is working"

dev-test: test-fast lint ## Quick development tests (fast tests + linting)

ci-test: test-all lint ## Full CI test suite

# Quick access to specific test classes
test-mcp: ## Test MCP connections
	uv run pytest tests/test_mcp_server.py::TestMCPConnections -v

test-splunk: ## Test Splunk tools
	uv run pytest tests/test_mcp_server.py::TestSplunkTools -v

test-apps: ## Test Splunk apps and users
	uv run pytest tests/test_mcp_server.py::TestSplunkAppsAndUsers -v

test-kvstore: ## Test KV Store functionality
	uv run pytest tests/test_mcp_server.py::TestKVStore -v 