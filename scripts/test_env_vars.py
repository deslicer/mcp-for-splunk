#!/usr/bin/env python3
"""
Test script to verify environment variables are properly loaded.

This script checks if all required environment variables for the OpenAI agent
and Splunk connection are available in the container environment.
"""

import os
import sys


def test_env_vars():
    """Test if environment variables are properly loaded."""
    print("🔍 Testing Environment Variables")
    print("=" * 50)
    
    # Define required and optional environment variables
    required_vars = {
        "SPLUNK_HOST": "Splunk server hostname",
        "SPLUNK_USERNAME": "Splunk username", 
        "SPLUNK_PASSWORD": "Splunk password"
    }
    
    optional_vars = {
        "SPLUNK_PORT": "Splunk management port (default: 8089)",
        "SPLUNK_VERIFY_SSL": "Verify SSL certificates (default: false)",
        "OPENAI_API_KEY": "OpenAI API key for agent functionality",
        "OPENAI_MODEL": "OpenAI model (default: gpt-4o)",
        "OPENAI_TEMPERATURE": "OpenAI temperature (default: 0.7)",
        "OPENAI_MAX_TOKENS": "OpenAI max tokens (default: 4000)",
        "MCP_HOT_RELOAD": "Enable hot reload (development)",
        "MCP_SERVER_MODE": "Server mode (docker/local)"
    }
    
    all_good = True
    
    # Check required variables
    print("📋 Required Variables:")
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            # Mask sensitive values
            if "PASSWORD" in var_name or "KEY" in var_name:
                display_value = f"***{value[-3:]}" if len(value) > 3 else "***"
            else:
                display_value = value
            print(f"  ✅ {var_name}: {display_value}")
        else:
            print(f"  ❌ {var_name}: NOT SET - {description}")
            all_good = False
    
    print("\n📋 Optional Variables:")
    for var_name, description in optional_vars.items():
        value = os.getenv(var_name)
        if value:
            # Mask sensitive values
            if "PASSWORD" in var_name or "KEY" in var_name:
                display_value = f"***{value[-3:]}" if len(value) > 3 else "***"
            else:
                display_value = value
            print(f"  ✅ {var_name}: {display_value}")
        else:
            print(f"  ⚪ {var_name}: Not set - {description}")
    
    # Test OpenAI agent configuration
    print("\n🤖 OpenAI Agent Configuration Test:")
    try:
        from src.tools.agents.openai_agent import OpenAIAgentTool
        
        # Try to create the agent tool (this will test config loading)
        agent = OpenAIAgentTool("test_agent", "agents")
        print(f"  ✅ Agent configuration loaded successfully")
        print(f"  📊 Model: {agent.config.model}")
        print(f"  🌡️  Temperature: {agent.config.temperature}")
        print(f"  📏 Max tokens: {agent.config.max_tokens}")
        print(f"  🔑 API key: {'***' + agent.config.api_key[-4:] if len(agent.config.api_key) > 4 else '***'}")
        
    except Exception as e:
        print(f"  ❌ Failed to load OpenAI agent configuration: {e}")
        all_good = False
    
    # Test Splunk client configuration
    print("\n🔌 Splunk Client Configuration Test:")
    try:
        from src.client.splunk_client import get_splunk_config
        
        config = get_splunk_config()
        print(f"  ✅ Splunk configuration loaded successfully")
        print(f"  🌐 Host: {config.get('host', 'Not set')}")
        print(f"  🔌 Port: {config.get('port', 'Not set')}")
        print(f"  👤 Username: {config.get('username', 'Not set')}")
        
        # Test password (masked)
        password = config.get('password')
        if password:
            print(f"  🔐 Password: ***{password[-3:] if len(password) > 3 else '***'}")
        else:
            print(f"  🔐 Password: Not set")
            
        print(f"  🔒 SSL Verify: {config.get('verify', 'Not set')}")
        
    except Exception as e:
        print(f"  ❌ Failed to load Splunk configuration: {e}")
        all_good = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 All required environment variables are properly configured!")
        return 0
    else:
        print("⚠️  Some required environment variables are missing.")
        print("💡 Make sure your .env file is properly configured and loaded.")
        return 1


if __name__ == "__main__":
    sys.exit(test_env_vars()) 