# Hot Reload Development Guide

This guide explains how to use the enhanced Docker Compose setup with hot reload functionality to iterate quickly on tool descriptions and MCP server code.

## Quick Start

### 1. Start Development Environment

Use the development-specific Docker Compose file:

```bash
# Start with enhanced hot reload
docker-compose -f docker-compose-dev.yml up --build --watch

# Or use the updated main compose with watch
docker-compose up --build --watch
```

### 2. Verify Hot Reload is Active

Check the server logs to confirm hot reload is enabled:

```bash
# Check logs
docker-compose -f docker-compose-dev.yml logs -f mcp-server-dev
```

You should see:
```
Starting with enhanced hot reload...
MCP_HOT_RELOAD=true
MCP_RELOAD_MODULES=true
```

### 3. Test Hot Reload

#### Option A: Automatic File Watch
1. Edit any tool description in `src/tools/`
2. Save the file
3. Docker watch will sync the file to the container
4. Use the manual reload to refresh descriptions

#### Option B: Manual Hot Reload
Trigger hot reload via API:

```bash
# Using the provided script
./scripts/hot_reload.py

# Or manually via curl
curl http://localhost:8002/mcp/resources/debug://reload
```

#### Option C: Via MCP Inspector
1. Open MCP Inspector: http://localhost:3001
2. Add resource: `debug://reload`
3. Execute to trigger hot reload

## How It Works

### File Watching
The Docker Compose watch feature monitors these paths:
- `./src/tools/` - Tool definitions and descriptions
- `./src/core/` - Core framework files
- `./contrib/` - Community contributions
- `./src/client/` - Client modules
- `./src/server.py` - Main server file

### Module Reloading
When hot reload is triggered:
1. Python modules are reloaded using `importlib.reload()`
2. Tool registry is cleared and repopulated
3. New tool descriptions are discovered and registered
4. FastMCP updates its tool definitions

### Debug Endpoint
The `debug://reload` resource endpoint:
- Only works when `MCP_HOT_RELOAD=true`
- Triggers complete component reload
- Returns status and reload statistics

## Development Workflow

### 1. Updating Tool Descriptions

1. Edit tool metadata in any tool file:
   ```python
   METADATA = ToolMetadata(
       name="tool_name",
       description="Your enhanced description here...",
       category="category",
       tags=["tag1", "tag2"],
       requires_connection=True,
   )
   ```

2. Save the file (Docker watch syncs automatically)

3. Trigger hot reload:
   ```bash
   ./scripts/hot_reload.py
   ```

4. Test the updated description:
   - Via MCP Inspector: http://localhost:3001
   - Via tools list API: http://localhost:8002/mcp/tools/list
   - Via your MCP client

### 2. Adding New Tools

1. Create new tool file in appropriate category
2. Define tool class with METADATA
3. Save file (syncs automatically)
4. Trigger hot reload to register new tool
5. Test new tool functionality

### 3. Framework Changes

For changes to core framework files:
1. Edit files in `src/core/`
2. Save (syncs automatically)
3. Since core changes affect structure, restart may be needed:
   ```bash
   docker-compose -f docker-compose-dev.yml restart mcp-server-dev
   ```

## Environment Variables

### Hot Reload Configuration
- `MCP_HOT_RELOAD=true` - Enables hot reload functionality
- `MCP_RELOAD_MODULES=true` - Enables Python module reloading
- `PYTHONPATH=/app` - Ensures proper import paths
- `PYTHONUNBUFFERED=1` - Real-time log output

### File Watching
Docker Compose watch is configured with:
- Fine-grained path watching for faster sync
- Ignore patterns for cache/compiled files
- Automatic rebuild on configuration changes

## Troubleshooting

### Hot Reload Not Working
1. Check environment variables:
   ```bash
   docker-compose -f docker-compose-dev.yml exec mcp-server-dev env | grep MCP
   ```

2. Check server logs:
   ```bash
   docker-compose -f docker-compose-dev.yml logs mcp-server-dev
   ```

3. Verify debug endpoint is accessible:
   ```bash
   curl http://localhost:8002/mcp/resources/debug://reload
   ```

### File Changes Not Syncing
1. Check Docker watch status:
   ```bash
   docker-compose -f docker-compose-dev.yml alpha watch
   ```

2. Verify file permissions and paths
3. Restart with fresh build:
   ```bash
   docker-compose -f docker-compose-dev.yml down
   docker-compose -f docker-compose-dev.yml up --build --watch
   ```

### Module Import Errors
1. Check Python path and imports
2. Verify all required modules are installed
3. Check for circular imports or syntax errors

## Performance Notes

- Hot reload adds development overhead but is disabled in production
- File watching is efficient but monitors many paths
- Module reloading preserves server state and connections
- Use sparingly in production environments

## Production Deployment

For production, use the standard compose file without hot reload:
```bash
# Production mode (no hot reload)
docker-compose up --build
```

The production setup:
- `MCP_HOT_RELOAD=false` (default)
- No module reloading overhead
- No debug endpoints
- Optimized for performance and stability

## Quick Reference

| Action | Command |
|--------|---------|
| Start dev environment | `docker-compose -f docker-compose-dev.yml up --watch` |
| Trigger hot reload | `./scripts/hot_reload.py` |
| Check server logs | `docker-compose -f docker-compose-dev.yml logs -f mcp-server-dev` |
| Access MCP Inspector | http://localhost:3001 |
| Test tools API | http://localhost:8002/mcp/tools/list |
| Debug reload endpoint | http://localhost:8002/mcp/resources/debug://reload |
| Restart server only | `docker-compose -f docker-compose-dev.yml restart mcp-server-dev` |

## Integration with IDEs

### VS Code
1. Install Docker extension
2. Use integrated terminal for commands
3. Configure file watcher for auto-reload trigger

### PyCharm
1. Configure Docker Compose run configuration
2. Use remote interpreter for debugging
3. Set up file watchers for automated reload

This setup enables rapid iteration on tool descriptions and MCP server functionality while maintaining the full containerized environment. 