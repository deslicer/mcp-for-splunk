# Architecture Deep Dive

This document provides an in-depth look at the modular architecture of the MCP Server for Splunk, explaining how components work together and how the discovery and loading system operates.

## Core Architecture Components

### 1. Core Framework (`src/core/`)

The core framework provides the foundation for all modular components:

#### Base Classes (`base.py`)

**BaseTool**
- Abstract base class for all tools
- Provides standardized interfaces for execution
- Handles error formatting and response structure
- Manages context and connection access
- Implements common utilities like logging

**BaseResource**
- Base class for MCP resources (future extension)
- Provides content retrieval interfaces
- Handles resource metadata and URIs

**BasePrompt**
- Base class for MCP prompts (future extension)
- Manages prompt templates and arguments
- Provides context-aware prompt generation

**Metadata Classes**
- `ToolMetadata` - Tool description and configuration
- `ResourceMetadata` - Resource identification and properties
- `PromptMetadata` - Prompt templates and parameters

#### Discovery System (`discovery.py`)

The discovery system automatically finds and catalogs components:

```python
def discover_tools(search_paths: List[str] = None) -> List[Type[BaseTool]]:
    """
    Discover all tool classes in the specified paths.

    Process:
    1. Scan directories recursively for .py files
    2. Import modules and inspect for BaseTool subclasses
    3. Validate metadata and tool structure
    4. Return list of discovered tool classes
    """
```

**Discovery Process:**
1. **Path Scanning** - Recursively scan `src/tools/` and `contrib/tools/`
2. **Module Import** - Dynamically import Python modules
3. **Class Inspection** - Find classes inheriting from `BaseTool`
4. **Metadata Validation** - Ensure tools have valid `METADATA` attributes
5. **Capability Check** - Verify required methods are implemented

#### Registry System (`registry.py`)

Centralized component management:

```python
class ComponentRegistry:
    """
    Manages registration and retrieval of MCP components.

    Features:
    - Tool registration and lookup
    - Category-based organization
    - Metadata indexing
    - Conflict resolution
    """

    def register_tool(self, tool_class: Type[BaseTool]) -> None:
        """Register a tool class with the registry."""

    def get_tool(self, name: str) -> Optional[Type[BaseTool]]:
        """Retrieve a tool class by name."""

    def list_tools(self, category: str = None) -> List[Type[BaseTool]]:
        """List tools, optionally filtered by category."""
```

#### Dynamic Loader (`loader.py`)

Runtime component loading and FastMCP integration:

```python
class ComponentLoader:
    """
    Handles dynamic loading of components into FastMCP server.

    Responsibilities:
    - Component instantiation
    - FastMCP registration
    - Error handling during loading
    - Hot-reload support (future)
    """

    async def load_tools(self, server: FastMCP) -> None:
        """Load and register all discovered tools with FastMCP server."""

    async def load_tool(self, tool_class: Type[BaseTool], server: FastMCP) -> None:
        """Load a single tool class into the server."""
```

### 2. Tool Organization (`src/tools/`)

Core tools are organized by functional domain:

#### Search Tools (`search/`)
- **Oneshot Search** - Quick queries with immediate results
- **Job Search** - Complex searches with progress tracking
- **Future**: Real-time searches, saved searches

#### Metadata Tools (`metadata/`)
- **Indexes** - List and explore Splunk indexes
- **Sourcetypes** - Discover data source types
- **Sources** - List data sources
- **Future**: Field discovery, data model exploration

#### Health Tools (`health/`)
- **Status Checks** - Connection and system health
- **Future**: Performance monitoring, capacity checks

#### Admin Tools (`admin/`)
- **Apps** - Splunk application management
- **Users** - User and role management
- **Configuration** - Access to .conf files
- **Future**: Cluster management, deployment

#### KV Store Tools (`kvstore/`)
- **Collections** - Collection management
- **Data Operations** - CRUD operations on KV data
- **Future**: Indexing, backup/restore

### 3. Community Framework (`contrib/`)

Structured system for community contributions:

#### Tool Categories
- **Examples** (`contrib/tools/examples/`) - Learning templates
- **Security** (`contrib/tools/security/`) - Security analysis tools
- **DevOps** (`contrib/tools/devops/`) - Operational tools
- **Analytics** (`contrib/tools/analytics/`) - Business intelligence

#### Development Tools (`contrib/scripts/`)
- **Tool Generator** - Interactive tool creation
- **Validator** - Code quality and compliance checking
- **Test Runner** - Automated testing for contrib tools
- **Tool Browser** - Discovery and exploration

## Component Lifecycle

### 1. Discovery Phase

```
Startup → Scan Paths → Import Modules → Inspect Classes → Validate Metadata → Register Components
```

**Path Resolution:**
```python
# Default search paths
search_paths = [
    "src/tools",      # Core tools
    "contrib/tools",  # Community tools
    "plugins/tools"   # External plugins (future)
]
```

**Module Import Process:**
```python
for py_file in find_python_files(search_paths):
    try:
        module = importlib.import_module(module_name)
        classes = inspect_classes(module, BaseTool)

        for cls in classes:
            if validate_tool(cls):
                registry.register_tool(cls)

    except ImportError as e:
        logger.warning(f"Failed to import {py_file}: {e}")
```

### 2. Registration Phase

Tool classes are registered with metadata indexing:

```python
def register_tool(self, tool_class: Type[BaseTool]) -> None:
    """Register tool with full metadata indexing."""

    metadata = tool_class.METADATA

    # Primary registration
    self._tools[metadata.name] = tool_class

    # Category indexing
    self._by_category[metadata.category].append(tool_class)

    # Tag indexing
    for tag in metadata.tags:
        self._by_tag[tag].append(tool_class)

    # Capability indexing
    if metadata.requires_connection:
        self._splunk_tools.append(tool_class)
```

### 3. Loading Phase

Tools are instantiated and registered with FastMCP:

```python
async def load_tools(self, server: FastMCP) -> None:
    """Load all registered tools into FastMCP server."""

    for tool_class in registry.list_tools():
        try:
            # Instantiate tool
            tool_instance = tool_class()

            # Create MCP tool definition
            @server.tool()
            async def tool_handler(ctx: Context, **kwargs):
                return await tool_instance.execute(ctx, **kwargs)

            # Set metadata
            tool_handler.__name__ = tool_class.METADATA.name
            tool_handler.__doc__ = tool_class.METADATA.description

        except Exception as e:
            logger.error(f"Failed to load tool {tool_class.METADATA.name}: {e}")
```

## Context Management

### MCP Context Flow

```
Client Request → FastMCP → Context Creation → Tool Execution → Response
```

**Context Structure:**
```python
class ToolContext:
    """Enhanced context for tool execution."""

    def __init__(self, mcp_context: Context):
        self.mcp_context = mcp_context
        self.session_id = mcp_context.session.session_id
        self.splunk_service = None  # Lazy initialization

    async def get_splunk_service(self):
        """Get or create Splunk service connection."""
        if not self.splunk_service:
            self.splunk_service = await create_splunk_connection()
        return self.splunk_service
```

### Connection Management

**Singleton Pattern for Splunk Connections:**
```python
class SplunkConnectionManager:
    """Manages Splunk connections with connection pooling."""

    _instance = None
    _connections = {}

    async def get_connection(self, session_id: str):
        """Get or create connection for session."""

        if session_id not in self._connections:
            self._connections[session_id] = await self._create_connection()

        return self._connections[session_id]
```

## Error Handling Architecture

### Hierarchical Error Handling

**Tool Level:**
```python
async def execute(self, ctx: Context, **kwargs) -> Dict[str, Any]:
    """Tool execution with standardized error handling."""
    try:
        result = await self._perform_operation(kwargs)
        return self.format_success_response(result)

    except ToolValidationError as e:
        return self.format_error_response(f"Validation failed: {e}")
    except SplunkConnectionError as e:
        return self.format_error_response(f"Splunk connection error: {e}")
    except Exception as e:
        self.logger.error(f"Unexpected error in {self.METADATA.name}: {e}")
        return self.format_error_response("Internal tool error")
```

**Framework Level:**
```python
async def safe_tool_execution(tool_instance, ctx, **kwargs):
    """Framework-level error handling wrapper."""
    try:
        return await tool_instance.execute(ctx, **kwargs)

    except Exception as e:
        # Log for debugging
        logger.exception(f"Tool execution failed: {tool_instance.METADATA.name}")

        # Return safe error response
        return {
            "success": False,
            "error": "Tool execution failed",
            "tool": tool_instance.METADATA.name
        }
```

## Performance Considerations

### Lazy Loading

**Module Import:**
```python
# Import modules only when needed
def get_tool_class(name: str) -> Type[BaseTool]:
    """Get tool class with lazy module loading."""

    if name not in _loaded_tools:
        module_path = _tool_modules[name]
        module = importlib.import_module(module_path)
        _loaded_tools[name] = getattr(module, _tool_classes[name])

    return _loaded_tools[name]
```

**Connection Pooling:**
```python
# Reuse Splunk connections across tools
class ConnectionPool:
    """Connection pool for Splunk services."""

    def __init__(self, max_connections: int = 10):
        self.pool = asyncio.Queue(maxsize=max_connections)
        self.active_connections = {}

    async def get_connection(self) -> SplunkService:
        """Get connection from pool or create new one."""

    async def return_connection(self, connection: SplunkService):
        """Return connection to pool."""
```

### Memory Management

**Result Streaming:**
```python
async def stream_search_results(self, search_query: str):
    """Stream large search results to manage memory."""

    job = service.jobs.create(search_query)

    # Process results in chunks
    while not job.is_done():
        results = job.preview(count=1000)  # Process 1000 at a time

        for result in results:
            yield dict(result)

        await asyncio.sleep(0.1)  # Yield control
```

## Security Architecture

### Input Validation

**Parameter Sanitization:**
```python
def validate_search_query(query: str) -> bool:
    """Validate SPL query for security."""

    # Block dangerous operations
    dangerous_commands = ['delete', 'output', 'script']

    for cmd in dangerous_commands:
        if f'| {cmd}' in query.lower():
            raise SecurityError(f"Command '{cmd}' not allowed")

    return True
```

**Access Control:**
```python
def check_tool_permissions(user_context: UserContext, tool: BaseTool) -> bool:
    """Check if user has permissions for tool."""

    required_capabilities = tool.METADATA.required_capabilities
    user_capabilities = user_context.capabilities

    return all(cap in user_capabilities for cap in required_capabilities)
```

## Extension Points

### Custom Tool Categories

Add new tool categories by creating directory structure:

```
contrib/tools/
└── your_category/
    ├── __init__.py
    ├── tool1.py
    └── tool2.py
```

### Plugin System (Future)

External plugins will be supported via:

```python
# plugins/your_plugin/setup.py
def register_tools():
    """Register plugin tools with the system."""
    return [YourCustomTool, AnotherTool]

def register_resources():
    """Register plugin resources."""
    return [YourResource]
```

### Custom Base Classes

Extend functionality with specialized base classes:

```python
class SecurityTool(BaseTool):
    """Specialized base class for security tools."""

    async def log_security_event(self, event_type: str, details: dict):
        """Log security-related events."""

    async def validate_ioc(self, ioc: str, ioc_type: str) -> bool:
        """Validate indicators of compromise."""
```

This architecture provides a solid foundation for extensibility while maintaining performance, security, and maintainability.
