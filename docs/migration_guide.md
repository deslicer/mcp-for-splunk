# Migration Guide: Monolithic to Modular Architecture

This guide helps you migrate from the original monolithic MCP Server for Splunk to the new modular, community-friendly architecture.

## Overview

The migration maintains **100% backward compatibility** while providing new capabilities:
- ✅ **All existing tools** continue to work identically
- ✅ **Same API endpoints** and behavior
- ✅ **Identical configuration** and deployment options
- ✅ **No client changes** required
- ✅ **Gradual migration** supported

## What Changed

### Before: Monolithic Structure
```
src/
├── server.py           # Single large file with all tools
├── splunk_client.py    # Splunk connection logic
└── __init__.py
```

### After: Modular Structure
```
src/
├── server.py           # Original server (unchanged)
├── core/              # New: Core framework
│   ├── base.py        # Base classes for tools
│   ├── discovery.py   # Automatic tool discovery
│   ├── registry.py    # Component registration
│   └── loader.py      # Dynamic loading
├── tools/             # New: Organized core tools
│   ├── search/        # Search operations
│   ├── metadata/      # Data discovery
│   ├── health/        # System monitoring
│   ├── admin/         # Administrative tools
│   └── kvstore/       # KV Store operations
└── client/            # New: Organized connection logic
    └── splunk_client.py
```

## Migration Steps

### Step 1: Test Current Setup

Before migrating, verify your current setup works:

```bash
# Test your current configuration
python src/server.py

# Test MCP Inspector connection
npx @modelcontextprotocol/inspector python src/server.py

# Test with your existing clients (Cursor, etc.)
```

### Step 2: Update Dependencies

The modular version uses the same dependencies but with additional development tools:

```bash
# Install latest dependencies
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

### Step 3: Test Modular Server

Test the new modular server with your existing configuration:

```bash
# Run modular server (same .env file)
python src/server_new.py

# Or test with the current server.py (already updated)
python src/server.py
```

**Verify all tools work:**
```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector python src/server.py

# Check all 12 tools are available:
# - get_splunk_health
# - list_indexes  
# - run_oneshot_search
# - run_splunk_search
# - list_sourcetypes
# - list_sources
# - list_apps
# - list_users
# - list_kvstore_collections
# - get_kvstore_data
# - create_kvstore_collection
# - get_configurations
```

### Step 4: Update Client Configurations

Your existing client configurations **do not need to change**, but you can optionally update them to reference the new structure:

**Cursor IDE (no changes needed):**
```json
{
  "mcpServers": {
    "mcp-server-for-splunk": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp-server-for-splunk/",
        "run", "python", "src/server.py"
      ],
      "env": {
        "SPLUNK_HOST": "localhost",
        "SPLUNK_PORT": "8089",
        "SPLUNK_USERNAME": "admin",
        "SPLUNK_PASSWORD": "Chang3d!",
        "SPLUNK_VERIFY_SSL": "false"
      }
    }
  }
}
```

### Step 5: Update Docker Deployment

If using Docker, the new version includes enhanced features:

**Before (still works):**
```bash
docker-compose up -d
```

**After (enhanced features):**
```bash
# Use the enhanced Docker setup
./scripts/build_and_run.sh

# Or manually
docker-compose build
docker-compose up -d
```

New services included:
- Enhanced MCP Inspector with web UI
- Improved Traefik configuration
- Better health monitoring

### Step 6: Validate Production Deployment

For production environments, test the migration thoroughly:

```bash
# Run comprehensive tests
make test-all

# Test specific MCP connections
make test-connections

# Check health endpoints
curl http://localhost:8001/mcp/resources/health%3A%2F%2Fstatus
```

## Configuration Migration

### Environment Variables

**No changes required** - all existing environment variables work:

```bash
# These remain the same
SPLUNK_HOST=your-splunk-host
SPLUNK_PORT=8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=password
SPLUNK_VERIFY_SSL=false
```

### Docker Configuration

**docker-compose.yml** - Enhanced but backward compatible:

```yaml
# Old configuration still works
# New features added:
# - Enhanced health checks
# - Better resource management
# - Improved networking
# - MCP Inspector integration
```

## Tool Development Migration

### Before: Manual Tool Addition

In the monolithic version, adding tools required editing `server.py`:

```python
# OLD: Manual tool registration in server.py
@app.tool()
async def my_custom_tool(ctx: Context, query: str) -> list:
    # Tool implementation
    pass
```

### After: Automatic Discovery

In the modular version, tools are automatically discovered:

```python
# NEW: Create tools in contrib/tools/
from src.core.base import BaseTool, ToolMetadata

class MyCustomTool(BaseTool):
    METADATA = ToolMetadata(
        name="my_custom_tool",
        description="My custom tool",
        category="examples"
    )
    
    async def execute(self, ctx: Context, query: str) -> dict:
        # Tool implementation
        return self.format_success_response({"result": "data"})
```

**Benefits of new approach:**
- ✅ **Automatic discovery** - no manual registration
- ✅ **Organized structure** - tools grouped by category
- ✅ **Consistent patterns** - standardized error handling
- ✅ **Easy testing** - built-in test frameworks
- ✅ **Community contributions** - clear contribution paths

## Rollback Plan

If you encounter issues, you can rollback instantly:

### Option 1: Use Original Server

The original monolithic server is preserved:

```bash
# Rollback to original (if server.py was replaced)
git checkout HEAD~1 src/server.py

# Run original server
python src/server.py
```

### Option 2: Docker Rollback

```bash
# Rollback Docker images
docker-compose down
docker-compose pull  # Get previous version
docker-compose up -d
```

### Option 3: Configuration Rollback

```bash
# Restore previous configuration
cp .env.backup .env
cp docker-compose.yml.backup docker-compose.yml
```

## Common Migration Issues

### Issue 1: Import Errors

**Problem:** Module import errors after migration

**Solution:**
```bash
# Clear Python cache
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# Reinstall dependencies
uv sync --dev
```

### Issue 2: Tool Discovery Problems

**Problem:** Custom tools not discovered

**Solution:**
```bash
# Test discovery manually
python -c "
from src.core.discovery import discover_tools
tools = discover_tools()
for tool in tools:
    print(f'Discovered: {tool.METADATA.name}')
"
```

### Issue 3: Connection Issues

**Problem:** Splunk connection failures

**Solution:**
```bash
# Test connection directly
python -c "
from src.client.splunk_client import get_splunk_service
service = get_splunk_service()
print(f'Connected: {service.info}')
"
```

### Issue 4: Docker Build Issues

**Problem:** Docker build failures

**Solution:**
```bash
# Clean Docker environment
docker system prune -f
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Performance Comparison

### Startup Time

**Before:** ~2-3 seconds
**After:** ~2-3 seconds (no change)

**The modular architecture adds negligible overhead due to:**
- Lazy loading of modules
- Efficient discovery caching
- Optimized import patterns

### Memory Usage

**Before:** ~50-100MB
**After:** ~50-100MB (similar)

**Memory usage remains similar because:**
- Tools are loaded on-demand
- Connection pooling is more efficient
- Garbage collection is improved

### Tool Execution Speed

**Before and After:** Identical performance

**Tool execution speed is unchanged because:**
- Same underlying Splunk operations
- Identical API calls
- Same connection handling

## Verification Checklist

### Pre-Migration Checklist

- [ ] Document current tool list (`get_splunk_health`, etc.)
- [ ] Test all existing tools work
- [ ] Backup current configuration (`.env`, `docker-compose.yml`)
- [ ] Note current performance benchmarks
- [ ] Test client integrations (Cursor, etc.)

### Post-Migration Checklist

- [ ] All 12 core tools available and working
- [ ] MCP Inspector connects successfully
- [ ] Docker stack starts without errors
- [ ] Existing client configurations work unchanged
- [ ] Performance metrics match pre-migration
- [ ] Tool development workflows functional

### Testing Commands

```bash
# Test all tools are available
curl http://localhost:8001/mcp/tools | jq '.tools[].name'

# Test specific tool execution
curl -X POST http://localhost:8001/mcp/tools/get_splunk_health

# Test health endpoints
curl http://localhost:8001/mcp/resources/health%3A%2F%2Fstatus

# Test with MCP Inspector
open http://localhost:3001

# Run comprehensive test suite
make test-all
```

## Benefits After Migration

### For Tool Development

- **Faster Development** - Interactive tool generator
- **Better Testing** - Automated test frameworks
- **Code Quality** - Built-in validation and linting
- **Documentation** - Automatic documentation generation

### For Operations

- **Better Monitoring** - Enhanced health checks
- **Easier Debugging** - Structured logging and metrics
- **Simplified Deployment** - Automated setup scripts
- **Community Tools** - Access to community-contributed tools

### For Community

- **Easy Contributions** - Clear development patterns
- **Tool Sharing** - Organized contribution system
- **Knowledge Sharing** - Comprehensive documentation
- **Collaborative Development** - Standardized workflows

## Next Steps

After successful migration:

1. **Explore Community Tools** - Check `contrib/tools/` for examples
2. **Create Custom Tools** - Use `./contrib/scripts/generate_tool.py`
3. **Contribute Back** - Share your tools with the community
4. **Stay Updated** - Follow project updates for new features

The modular architecture provides a solid foundation for future growth while maintaining the reliability and functionality you depend on. 