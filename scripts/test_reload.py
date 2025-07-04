#!/usr/bin/env python3
"""
Simple test script to verify hot reload functionality
"""

import subprocess
import sys
import time
import json

def check_tool_descriptions():
    """Check current tool descriptions via docker exec"""
    try:
        # Execute a command inside the container to check tool descriptions
        result = subprocess.run([
            'docker-compose', '-f', 'docker-compose-dev.yml', 'exec', '-T', 'mcp-server-dev',
            'python', '-c', '''
import sys
sys.path.append("/app")
from src.core.registry import tool_registry
from src.core.discovery import discover_tools

# Discover tools to populate registry
discover_tools()

# Find the health tool
tools = tool_registry.list_tools()
for tool in tools:
    if tool.name == "get_splunk_health":
        print(f"Description: {tool.description}")
        print(f"Tags: {tool.tags}")
        break
else:
    print("Tool not found")
'''
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("Current tool descriptions:")
            print(result.stdout.strip())
            return True
        else:
            print(f"Error checking tools: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Timeout waiting for container response")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def trigger_reload():
    """Trigger reload by calling the reload method inside container"""
    try:
        # Execute the reload command inside the container
        result = subprocess.run([
            'docker-compose', '-f', 'docker-compose-dev.yml', 'exec', '-T', 'mcp-server-dev',
            'python', '-c', '''
import sys
sys.path.append("/app")
from src.core.loader import ToolLoader
from fastmcp import FastMCP

# Create a mock MCP server for testing
mcp = FastMCP("test")
tool_loader = ToolLoader(mcp)

# Trigger reload
print("Triggering hot reload...")
count = tool_loader.reload_tools()
print(f"Reloaded {count} tools")
'''
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            print("Hot reload result:")
            print(result.stdout.strip())
            return True
        else:
            print(f"Error during reload: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Timeout during reload")
        return False
    except Exception as e:
        print(f"Error during reload: {e}")
        return False

def main():
    print("🔄 Testing Hot Reload Functionality")
    print("=" * 50)
    
    print("\n1. Checking current tool descriptions...")
    check_tool_descriptions()
    
    print("\n2. Triggering hot reload...")
    if trigger_reload():
        print("✅ Hot reload completed")
    else:
        print("❌ Hot reload failed")
        sys.exit(1)
    
    print("\n3. Checking updated tool descriptions...")
    time.sleep(2)  # Give a moment for changes to take effect
    check_tool_descriptions()
    
    print("\n🎉 Hot reload test completed!")

if __name__ == "__main__":
    main() 