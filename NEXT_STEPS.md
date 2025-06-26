# Next Steps: Testing and Deploying the Modular MCP Server

## 🚀 Immediate Actions (Next 30 minutes)

### 1. **Test Locally First** ⭐ START HERE
```bash
# Test the modular server components
python scripts/test_modular_server.py
```

**Expected Output:**
- ✅ All tools discovered (13+ tools)
- ✅ Hello world tool works
- ✅ Health tool works
- ✅ Server startup successful

### 2. **Run Modular Server Locally**
```bash
# Start the new modular server
python src/server_new.py --transport http --port 8000
```

**Test it works:**
```bash
# In another terminal
curl http://localhost:8000/mcp/health
```

## 🐳 Docker Testing (Next 30 minutes)

### Option A: Update Existing Docker Setup
```bash
# Set environment variable for new server
export MCP_SERVER_VERSION=new

# Rebuild and start
docker-compose up --build
```

### Option B: Use Dedicated Modular Setup
```bash
# Use the new modular docker-compose
docker-compose -f docker-compose-modular.yml up --build
```

**Verify Docker works:**
- **Health Check**: `curl http://localhost:8002/mcp/health`
- **MCP Inspector**: http://localhost:3001
- **Traefik Dashboard**: http://localhost:8080

## 🔍 Validation Steps

### Core Functionality Tests
```bash
# 1. Check tools are discovered
docker logs mcp-server-modular | grep "Successfully loaded components"

# 2. Test via MCP Inspector
# Open http://localhost:3001
# Connect to: http://localhost:8001/mcp/
# Browse available tools

# 3. Test key tools
# In MCP Inspector, try:
# - get_splunk_health (should work without Splunk)
# - hello_world (should return greeting)
# - list_indexes (might fail without Splunk, but should handle gracefully)
```

## 📋 Pre-Production Checklist

Before switching to the modular server in production:

### ✅ Functionality Tests
- [ ] **All tools discovered**: Check logs for successful component loading
- [ ] **Health endpoint works**: `curl http://localhost:8002/mcp/health`
- [ ] **MCP Inspector connects**: Can browse tools via web interface
- [ ] **Splunk connection**: If available, test actual Splunk tools
- [ ] **Error handling**: Tools gracefully handle connection failures

### ✅ Performance Tests  
- [ ] **Startup time**: Should be similar to original server
- [ ] **Memory usage**: Monitor Docker container memory
- [ ] **Tool response time**: Test with actual Splunk queries if possible

### ✅ Integration Tests
- [ ] **Original workflows work**: Test your existing MCP client integrations
- [ ] **Inspector functionality**: All tools visible and testable
- [ ] **Docker compose**: Both modular and original configs work

## 🚨 Troubleshooting Quick Reference

### Common Issues & Solutions

#### Problem: "No tools discovered"
```bash
# Check if modules exist
ls -la src/tools/
ls -la contrib/tools/

# Test discovery manually
python -c "
import sys, os
sys.path.insert(0, os.getcwd())
from src.core.discovery import discover_tools
print(f'Discovered {discover_tools()} tools')
"
```

#### Problem: Import errors in Docker
```bash
# Rebuild without cache
docker-compose build --no-cache

# Check logs
docker logs mcp-server-modular
```

#### Problem: MCP Inspector can't connect
```bash
# Check server is running
curl http://localhost:8002/mcp/health

# Check CORS settings in docker-compose
# Should see: STREAMABLE_HTTP_DISABLE_CORS=true
```

#### Problem: Splunk connection fails
```bash
# Check Splunk container
docker ps | grep splunk

# Check environment variables
docker exec mcp-server-modular env | grep SPLUNK
```

## 🔄 Rollback Strategy

If issues arise, you can quickly rollback:

### Immediate Rollback (< 1 minute)
```bash
# Option 1: Change environment variable
export MCP_SERVER_VERSION=old
docker-compose restart mcp-server

# Option 2: Use original docker-compose
docker-compose -f docker-compose.yml up
```

### Full Rollback (< 5 minutes)
```bash
# Stop modular setup
docker-compose -f docker-compose-modular.yml down

# Start original setup  
docker-compose up
```

## 🎯 Success Criteria

Migration is ready for production when:

1. **✅ Local tests pass**: `python scripts/test_modular_server.py`
2. **✅ Docker startup clean**: No errors in `docker logs mcp-server-modular`
3. **✅ Tool count matches**: Same or more tools than original server
4. **✅ MCP Inspector works**: Can connect and test tools
5. **✅ Performance acceptable**: No significant slowdowns
6. **✅ Rollback tested**: Confirmed ability to quickly revert

## 📅 Implementation Timeline

### Week 1: Validation Phase
- [ ] **Day 1-2**: Local testing and validation
- [ ] **Day 3-4**: Docker testing and integration  
- [ ] **Day 5-7**: Performance testing and optimization

### Week 2: Deployment Phase  
- [ ] **Day 1-2**: Staging environment deployment
- [ ] **Day 3-4**: Production deployment with monitoring
- [ ] **Day 5-7**: Monitoring and optimization

### Week 3: Enhancement Phase
- [ ] **Day 1-3**: Community contribution setup
- [ ] **Day 4-5**: Documentation updates
- [ ] **Day 6-7**: Advanced features (if needed)

## 🔧 Development Workflow

### Adding New Tools (Post-Migration)
```bash
# 1. Create tool in appropriate directory
mkdir -p contrib/tools/my_category
cat > contrib/tools/my_category/my_tool.py << 'EOF'
from src.core.base import BaseTool, ToolMetadata

class MyTool(BaseTool):
    METADATA = ToolMetadata(
        name="my_tool", 
        description="My custom tool",
        category="my_category"
    )
    
    async def execute(self, ctx, **kwargs):
        return self.format_success_response({"result": "success"})
EOF

# 2. Test new tool
python scripts/test_modular_server.py

# 3. Restart server (automatic discovery)
docker-compose restart mcp-server-modular
```

## 📊 Monitoring & Metrics

### Key Metrics to Track
- **Startup time**: Time from container start to ready
- **Tool count**: Number of tools successfully loaded
- **Error rate**: Failed tool executions
- **Response time**: Time for health checks and simple tools
- **Memory usage**: Container memory consumption

### Monitoring Commands
```bash
# Monitor logs
docker logs mcp-server-modular --follow

# Check container stats
docker stats mcp-server-modular

# Test health endpoint
watch -n 5 'curl -s http://localhost:8002/mcp/health'
```

## 🎉 What You've Achieved

With the modular architecture, you now have:

✅ **Organized Codebase**: Tools logically separated by function  
✅ **Community Ready**: Clear contribution paths in `contrib/`  
✅ **Automatic Discovery**: New tools automatically loaded  
✅ **Zero Downtime Migration**: Both servers can run side-by-side  
✅ **Enhanced Maintainability**: Easier to update and extend  
✅ **Testing Framework**: Automated validation of changes  

The modular server provides the same functionality as your original server while opening the door for community contributions and easier maintenance. 

**Ready to start? Run: `python scripts/test_modular_server.py`** 🚀 