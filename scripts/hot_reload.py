#!/usr/bin/env python3
"""
Hot reload script for MCP Server development.

This script triggers a hot reload of all MCP components via the debug API.
Useful during development when you make changes to tool descriptions.
"""

import json
import sys
import time
import urllib.request
import urllib.error


def trigger_hot_reload_via_mcp(base_url: str = "http://localhost:8001") -> bool:
    """
    Trigger hot reload via MCP JSON-RPC protocol.
    
    Args:
        base_url: Base URL of the MCP server
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # First, try to read the debug resource via MCP protocol
        url = f"{base_url}/mcp/"
        
        # Prepare the MCP JSON-RPC request to read the debug resource
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "debug://reload"
            }
        }
        
        # Prepare the request with proper headers for MCP Streamable HTTP
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
        }
        
        print(f"Triggering hot reload via MCP at: {url}")
        print(f"Reading resource: debug://reload")
        
        # Create the request
        data = json.dumps(mcp_request).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                print(f"❌ HTTP {response.status}: {response.reason}")
                return False
                
            response_data = response.read().decode('utf-8')
            
            # Handle potential Server-Sent Events format
            if response_data.startswith('data: '):
                # Parse SSE format
                lines = response_data.strip().split('\n')
                json_line = None
                for line in lines:
                    if line.startswith('data: '):
                        json_line = line[6:]  # Remove 'data: ' prefix
                        break
                if json_line:
                    response_data = json_line
            
            result = json.loads(response_data)
        
        print(f"MCP Response: {json.dumps(result, indent=2)}")
        
        # Check if the MCP call was successful
        if 'result' in result:
            # Parse the actual resource content (which should be JSON)
            resource_content = result['result']['contents'][0]['text']
            reload_result = json.loads(resource_content)
            
            if reload_result.get("status") == "success":
                print("✅ Hot reload completed successfully!")
                print(f"Reloaded components: {reload_result.get('results', {})}")
                return True
            else:
                print(f"❌ Hot reload failed: {reload_result.get('message', 'Unknown error')}")
                return False
        elif 'error' in result:
            print(f"❌ MCP Error: {result['error']}")
            return False
        else:
            print(f"❌ Unexpected response format")
            return False
            
    except urllib.error.URLError as e:
        print(f"❌ Failed to connect to MCP server: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        print(f"Raw response: {response_data}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def trigger_hot_reload_direct(base_url: str = "http://localhost:8002") -> bool:
    """
    Fallback: Try direct HTTP GET to the resource endpoint.
    
    Args:
        base_url: Base URL of the MCP server
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Try direct access to the debug endpoint
        url = f"{base_url}/debug/reload"
        
        print(f"Trying direct access at: {url}")
        
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status != 200:
                print(f"❌ HTTP {response.status}: {response.reason}")
                return False
                
            data = response.read().decode('utf-8')
            result = json.loads(data)
        
        print(f"Direct response: {json.dumps(result, indent=2)}")
        
        if result.get("status") == "success":
            print("✅ Hot reload completed successfully!")
            return True
        else:
            print(f"❌ Hot reload failed: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Direct access failed: {e}")
        return False


def main():
    """Main function"""
    # Allow custom base URL as command line argument
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002"
    
    print("🔄 MCP Server Hot Reload Tool")
    print(f"Server: {base_url}")
    print("-" * 40)
    
    # Try MCP protocol first
    success = trigger_hot_reload_via_mcp(base_url)
    
    if not success:
        print("\n🔄 Trying fallback method...")
        success = trigger_hot_reload_direct(base_url)
    
    if success:
        print("\n🎉 Tool descriptions should now be updated!")
        print("You can now test the updated tools via MCP Inspector or client.")
    else:
        print("\n🚨 Hot reload failed. Check server logs for details.")
        print("Make sure MCP_HOT_RELOAD=true is set in the server environment.")
        sys.exit(1)


if __name__ == "__main__":
    main() 