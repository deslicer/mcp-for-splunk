#!/usr/bin/env python3
"""
Validation script to check if the environment is properly configured
for testing the Splunk Triage Agent.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check if required environment variables are set."""
    logger.info("🔍 Checking environment variables...")
    
    required_vars = {
        'OPENAI_API_KEY': 'OpenAI API key for the triage agent',
        'SPLUNK_HOST': 'Splunk server hostname',
        'SPLUNK_USERNAME': 'Splunk username',
        'SPLUNK_PASSWORD': 'Splunk password'
    }
    
    optional_vars = {
        'SPLUNK_PORT': 'Splunk port (default: 8089)',
        'OPENAI_MODEL': 'OpenAI model (default: gpt-4o)',
        'OPENAI_TEMPERATURE': 'OpenAI temperature (default: 0.7)',
        'MCP_SERVER_URL': 'MCP server URL (default: http://localhost:8000)'
    }
    
    missing_required = []
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var}: {'*' * min(len(value), 10)}... ({description})")
        else:
            logger.error(f"❌ {var}: Not set - {description}")
            missing_required.append(var)
    
    # Check optional variables
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var}: {value} ({description})")
        else:
            logger.info(f"ℹ️  {var}: Using default - {description}")
    
    if missing_required:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def check_python_dependencies():
    """Check if required Python packages are installed."""
    logger.info("🔍 Checking Python dependencies...")
    
    required_packages = [
        'fastmcp',
        'openai',
        'asyncio',
        'logging',
        'dataclasses'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✅ {package}: Installed")
        except ImportError:
            logger.error(f"❌ {package}: Not installed")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ Missing packages: {', '.join(missing_packages)}")
        logger.info("Install missing packages with: pip install " + " ".join(missing_packages))
        return False
    
    logger.info("✅ All required Python packages are installed")
    return True

def check_file_structure():
    """Check if required files exist."""
    logger.info("🔍 Checking file structure...")
    
    required_files = [
        'test_agent.py',
        'run_test.py',
        'TEST_README.md',
        'src/server.py',
        'src/tools/agents/splunk_triage_agent.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            logger.info(f"✅ {file_path}: Found")
        else:
            logger.error(f"❌ {file_path}: Not found")
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    
    logger.info("✅ All required files are present")
    return True

async def check_server_connection():
    """Check if the MCP server is running and accessible."""
    logger.info("🔍 Checking MCP server connection...")
    
    try:
        from fastmcp import Client
        
        server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8000')
        logger.info(f"Testing connection to: {server_url}")
        
        client = Client(server_url, timeout=10.0)
        
        async with client:
            # Test basic connection
            await client.ping()
            logger.info("✅ Server ping successful")
            
            # Check if tools are available
            tools = await client.list_tools()
            logger.info(f"✅ Found {len(tools)} tools")
            
            # Look for the triage tool
            triage_tool = None
            for tool in tools:
                if "splunk" in tool.name.lower() and ("triage" in tool.name.lower() or "missing_data" in tool.name.lower()):
                    triage_tool = tool
                    break
            
            if triage_tool:
                logger.info(f"✅ Found triage tool: {triage_tool.name}")
            else:
                logger.warning("⚠️  Triage tool not found in available tools")
                logger.info("Available tools:")
                for tool in tools[:10]:  # Show first 10 tools
                    logger.info(f"  - {tool.name}")
                if len(tools) > 10:
                    logger.info(f"  ... and {len(tools) - 10} more")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ FastMCP import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Server connection failed: {e}")
        logger.info("Make sure the MCP server is running:")
        logger.info("  python src/server.py")
        return False

def print_setup_instructions():
    """Print setup instructions."""
    logger.info("📋 Setup Instructions:")
    logger.info("")
    logger.info("1. Set required environment variables:")
    logger.info("   export OPENAI_API_KEY=your_openai_api_key")
    logger.info("   export SPLUNK_HOST=localhost")
    logger.info("   export SPLUNK_USERNAME=admin")
    logger.info("   export SPLUNK_PASSWORD=your_password")
    logger.info("")
    logger.info("2. Install required packages:")
    logger.info("   pip install fastmcp openai")
    logger.info("")
    logger.info("3. Start the MCP server:")
    logger.info("   python src/server.py")
    logger.info("")
    logger.info("4. Run the tests:")
    logger.info("   python test_agent.py")
    logger.info("   python run_test.py missing_data")
    logger.info("")

async def main():
    """Main validation function."""
    logger.info("="*80)
    logger.info("SPLUNK TRIAGE AGENT TEST ENVIRONMENT VALIDATION")
    logger.info("="*80)
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Python Dependencies", check_python_dependencies),
        ("File Structure", check_file_structure),
    ]
    
    results = []
    
    # Run synchronous checks
    for name, check_func in checks:
        logger.info(f"\n--- {name} ---")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"❌ {name} check failed: {e}")
            results.append((name, False))
    
    # Run async server check
    logger.info("\n--- Server Connection ---")
    try:
        server_result = await check_server_connection()
        results.append(("Server Connection", server_result))
    except Exception as e:
        logger.error(f"❌ Server connection check failed: {e}")
        results.append(("Server Connection", False))
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*80)
    
    passed = 0
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{name:20} {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        logger.info("🎉 Environment is ready for testing!")
        logger.info("\nYou can now run:")
        logger.info("  python test_agent.py")
        logger.info("  python run_test.py missing_data")
    else:
        logger.error(f"❌ {total - passed} checks failed")
        logger.info("\nPlease fix the issues above before running tests.")
        print_setup_instructions()
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Validation failed: {e}")
        sys.exit(1) 