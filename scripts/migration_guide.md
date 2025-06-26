# Migration Guide: From Monolithic to Modular MCP Server

This guide walks you through testing and migrating to the new modular MCP server architecture.

## 🎯 Quick Start

### 1. **Test Locally (Recommended First Step)**

```bash
# Test the new modular server locally
python scripts/test_modular_server.py

# Run the modular server locally
python src/server_new.py --transport http --port 8000
```

### 2. **Test with Docker (Original Setup)**

Update your original `docker-compose.yml` to use the new server:

```bash
# Update the environment variable to use the new server
export MCP_SERVER_VERSION=new

# Start with the original docker-compose
docker-compose up --build

# OR: Use the dedicated modular docker-compose
docker-compose -f docker-compose-modular.yml up --build
```

### 3. **Test with MCP Inspector**

Once the server is running:
- **MCP Inspector**: http://localhost:3001
- **MCP Server**: http://localhost:8001/mcp/
- **Traefik Dashboard**: http://localhost:8080

## 🔍 Testing Strategy

### Phase 1: Local Testing

```bash
# 1. Install dependencies (if needed)
uv sync

# 2. Test the modular server
python scripts/test_modular_server.py

# 3. Compare with original server
python src/server.py &            # Start original server
python src/server_new.py &        # Start modular server (different port)

# Test both with MCP Inspector or your client
```

### Phase 2: Docker Testing

```bash
# Test modular server in Docker
docker-compose -f docker-compose-modular.yml up --build

# Check logs
docker logs mcp-server-modular

# Test functionality
curl http://localhost:8002/mcp/health
```

### Phase 3: Integration Testing

```bash
# Test with MCP Inspector
# 1. Open http://localhost:3001
# 2. Connect to: http://localhost:8001/mcp/
# 3. Verify all tools are available
# 4. Test a few key tools (search, health, metadata)
```

## 🔧 Environment Variables

### Server Selection

```bash
# Use new modular server (default)
MCP_SERVER_VERSION=new

# Use original monolithic server (fallback)
MCP_SERVER_VERSION=old
```

### Development Mode

```bash
# Enable hot reload in Docker
MCP_HOT_RELOAD=true

# Standard production mode
MCP_HOT_RELOAD=false
```

## 📋 Validation Checklist

### ✅ Pre-Migration Checklist

- [ ] Local testing passes: `python scripts/test_modular_server.py`
- [ ] All expected tools discovered
- [ ] Hello world tool works
- [ ] Health tool works
- [ ] Docker build succeeds
- [ ] Docker container starts without errors
- [ ] MCP Inspector can connect
- [ ] Basic search functionality works

### ✅ Post-Migration Checklist

- [ ] All existing tools work as expected
- [ ] Performance is equivalent or better
- [ ] Logs show successful component loading
- [ ] MCP Inspector shows all tools
- [ ] Splunk connection works
- [ ] Search tools return expected results
- [ ] Metadata tools work correctly

## 🚨 Troubleshooting

### Common Issues

#### 1. Import Errors
```
ModuleNotFoundError: No module named 'src.core'
```

**Solution**: Check your PYTHONPATH and ensure you're running from the project root:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python src/server_new.py
```

#### 2. Tool Discovery Issues
```
WARNING: No tools discovered
```

**Solution**: Verify the modular structure exists:
```bash
ls -la src/tools/
ls -la contrib/tools/
```

#### 3. Docker Import Issues
```
ImportError: cannot import name 'get_splunk_service_safe'
```

**Solution**: Rebuild the Docker image:
```bash
docker-compose build --no-cache mcp-server-modular
```

#### 4. Splunk Connection Issues
```
Failed to connect to Splunk
```

**Solution**: Check environment variables and Splunk status:
```bash
# Check Splunk is running
docker ps | grep splunk

# Check environment variables
echo $SPLUNK_HOST $SPLUNK_USERNAME $SPLUNK_PASSWORD
```

### Debugging Commands

```bash
# Check tool discovery manually
python -c "
import sys, os
sys.path.insert(0, os.getcwd())
from src.core.discovery import discover_tools
print(f'Discovered {discover_tools()} tools')
"

# Test individual tool
python -c "
import sys, os, asyncio
sys.path.insert(0, os.getcwd())
from src.tools.health.status import GetSplunkHealth
from src.core.base import ToolMetadata
tool = GetSplunkHealth('test', 'test')
print(f'Tool metadata: {tool.METADATA}')
"

# Check Docker logs
docker logs mcp-server-modular --follow
```

## 🔄 Rollback Plan

If you encounter issues, you can quickly rollback:

### Option 1: Environment Variable
```bash
# In docker-compose.yml, change:
- MCP_SERVER_VERSION=new
+ MCP_SERVER_VERSION=old
```

### Option 2: Use Original Docker Compose
```bash
# Stop modular version
docker-compose -f docker-compose-modular.yml down

# Start original version
docker-compose up
```

### Option 3: Manual Fallback
```bash
# Edit Dockerfile CMD to use old server
- python src/server_new.py
+ python src/server.py
```

## 📈 Performance Comparison

### Metrics to Monitor

- **Startup Time**: How long the server takes to start
- **Tool Count**: Number of tools discovered and loaded
- **Memory Usage**: Compare Docker memory consumption
- **Response Time**: Time for health checks and simple tools

### Benchmarking Commands

```bash
# Measure startup time
time python src/server_new.py --help

# Count tools
python scripts/test_modular_server.py | grep "Discovered"

# Test response time
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8002/mcp/health
```

## 🎉 Success Criteria

Migration is successful when:

1. **All tests pass**: `python scripts/test_modular_server.py`
2. **Tool count matches**: Same number of tools as original server
3. **Functionality works**: Key tools (search, metadata, health) work correctly
4. **Performance is acceptable**: No significant degradation
5. **MCP Inspector connects**: Can browse and test tools
6. **Logs are clean**: No errors during startup or operation

## 🔧 Next Steps After Migration

1. **Update Documentation**: Point to new server in README
2. **Create Contribution Guide**: Share with team/community
3. **Add Custom Tools**: Try creating tools in `contrib/`
4. **Set up CI/CD**: Automate testing of contributions
5. **Monitor Performance**: Track metrics over time

## 📞 Getting Help

If you encounter issues:

1. **Check Logs**: Both application and Docker logs
2. **Run Tests**: Use the test script to identify specific issues
3. **Compare Outputs**: Test both old and new servers side-by-side
4. **Environment**: Verify all environment variables are set correctly
5. **Dependencies**: Ensure all Python packages are installed

The modular architecture is designed to be a drop-in replacement, so most issues are related to configuration or environment setup rather than fundamental problems. 