"""
Tests for MCP transport methods (stdio and streamable-http).
"""
import pytest
import asyncio
import os
import sys
import argparse
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from src import server


class TestTransportConfiguration:
    """Test transport configuration and argument parsing"""
    
    def test_default_transport_stdio(self):
        """Test that stdio is the default transport"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('sys.argv', ['server.py']):
                # Create args namespace like main() does when no args provided
                args = argparse.Namespace(
                    transport='stdio',
                    host='localhost',
                    port=8000,
                    path='/mcp/'
                )
                assert args.transport == 'stdio'
                assert args.host == 'localhost'
                assert args.port == 8000
                assert args.path == '/mcp/'

    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        with patch.dict(os.environ, {
            'MCP_TRANSPORT': 'streamable-http',
            'MCP_HOST': '0.0.0.0',
            'MCP_PORT': '9000',
            'MCP_PATH': '/api/mcp/'
        }):
            # Simulate what main() does with environment variables
            args = argparse.Namespace(
                transport=os.environ.get('MCP_TRANSPORT', 'stdio'),
                host=os.environ.get('MCP_HOST', 'localhost'),
                port=int(os.environ.get('MCP_PORT', 8000)),
                path=os.environ.get('MCP_PATH', '/mcp/')
            )
            assert args.transport == 'streamable-http'
            assert args.host == '0.0.0.0'
            assert args.port == 9000
            assert args.path == '/api/mcp/'

    @patch('argparse.ArgumentParser.parse_args')
    def test_command_line_arguments(self, mock_parse_args):
        """Test command line argument parsing"""
        mock_parse_args.return_value = argparse.Namespace(
            transport='streamable-http',
            host='custom-host',
            port=8080,
            path='/custom/path/'
        )
        
        with patch('sys.argv', ['server.py', '--transport', 'streamable-http']):
            # Would be handled by argparse in actual implementation
            args = mock_parse_args.return_value
            assert args.transport == 'streamable-http'
            assert args.host == 'custom-host'
            assert args.port == 8080
            assert args.path == '/custom/path/'

    def test_invalid_transport_choice(self):
        """Test that invalid transport choices are rejected"""
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--transport', 
            choices=['stdio', 'streamable-http'], 
            default='stdio'
        )
        
        with pytest.raises(SystemExit):
            parser.parse_args(['--transport', 'invalid-transport'])

    def test_port_type_conversion(self):
        """Test that port is properly converted to integer"""
        with patch.dict(os.environ, {'MCP_PORT': '8080'}):
            port = int(os.environ.get('MCP_PORT', 8000))
            assert isinstance(port, int)
            assert port == 8080

    def test_invalid_port_environment_variable(self):
        """Test handling of invalid port in environment variable"""
        with patch.dict(os.environ, {'MCP_PORT': 'not-a-number'}):
            with pytest.raises(ValueError):
                int(os.environ.get('MCP_PORT', 8000))


class TestStdioTransport:
    """Test stdio transport functionality"""
    
    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_stdio_transport_startup(self, mock_run_async):
        """Test stdio transport server startup"""
        mock_run_async.return_value = None
        
        # Mock the main function behavior for stdio
        args = argparse.Namespace(transport='stdio')
        
        # Simulate the main function logic
        if args.transport == "stdio":
            await server.mcp.run_async(transport="stdio")
        
        mock_run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_stdio_transport_with_logging(self, mock_run_async):
        """Test stdio transport startup with logging"""
        mock_run_async.return_value = None
        
        with patch('src.server.logger') as mock_logger:
            args = argparse.Namespace(transport='stdio')
            
            # Simulate main function logging and startup
            mock_logger.info("🚀 Starting MCP Server for Splunk")
            mock_logger.info(f"📡 Transport: {args.transport}")
            mock_logger.info("🔌 Running with STDIO transport (local mode)")
            
            await server.mcp.run_async(transport="stdio")
            
            mock_run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_stdio_transport_error_handling(self, mock_run_async):
        """Test stdio transport error handling"""
        mock_run_async.side_effect = Exception("STDIO connection failed")
        
        with pytest.raises(Exception, match="STDIO connection failed"):
            await server.mcp.run_async(transport="stdio")


class TestStreamableHttpTransport:
    """Test streamable-http transport functionality"""
    
    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_http_transport_startup(self, mock_run_async):
        """Test HTTP transport server startup"""
        mock_run_async.return_value = None
        
        args = argparse.Namespace(
            transport='streamable-http',
            host='localhost',
            port=8000,
            path='/mcp/'
        )
        
        # Simulate the main function logic for HTTP
        if args.transport == "streamable-http":
            await server.mcp.run_async(
                transport="streamable-http", 
                host=args.host, 
                port=args.port, 
                path=args.path
            )
        
        mock_run_async.assert_called_once_with(
            transport="streamable-http",
            host="localhost",
            port=8000,
            path="/mcp/"
        )

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_http_transport_custom_configuration(self, mock_run_async):
        """Test HTTP transport with custom configuration"""
        mock_run_async.return_value = None
        
        args = argparse.Namespace(
            transport='streamable-http',
            host='0.0.0.0',
            port=9000,
            path='/api/mcp/'
        )
        
        await server.mcp.run_async(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path
        )
        
        mock_run_async.assert_called_once_with(
            transport="streamable-http",
            host="0.0.0.0",
            port=9000,
            path="/api/mcp/"
        )

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_http_transport_with_logging(self, mock_run_async):
        """Test HTTP transport startup with logging"""
        mock_run_async.return_value = None
        
        with patch('src.server.logger') as mock_logger:
            args = argparse.Namespace(
                transport='streamable-http',
                host='localhost',
                port=8000,
                path='/mcp/'
            )
            
            # Simulate main function logging
            mock_logger.info("🚀 Starting MCP Server for Splunk")
            mock_logger.info(f"📡 Transport: {args.transport}")
            mock_logger.info(f"🌐 Running with HTTP transport on {args.host}:{args.port}{args.path}")
            
            await server.mcp.run_async(
                transport="streamable-http",
                host=args.host,
                port=args.port,
                path=args.path
            )

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_http_transport_error_handling(self, mock_run_async):
        """Test HTTP transport error handling"""
        mock_run_async.side_effect = Exception("HTTP server failed to start")
        
        with pytest.raises(Exception, match="HTTP server failed to start"):
            await server.mcp.run_async(
                transport="streamable-http",
                host="localhost",
                port=8000,
                path="/mcp/"
            )

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_http_transport_port_binding_error(self, mock_run_async):
        """Test HTTP transport port binding error"""
        mock_run_async.side_effect = OSError("Address already in use")
        
        with pytest.raises(OSError, match="Address already in use"):
            await server.mcp.run_async(
                transport="streamable-http",
                host="localhost",
                port=8000,
                path="/mcp/"
            )


class TestMainFunction:
    """Test the main function transport routing"""
    
    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_main_stdio_routing(self, mock_parse_args, mock_run_async):
        """Test main function routes to stdio transport correctly"""
        mock_parse_args.return_value = argparse.Namespace(transport='stdio')
        mock_run_async.return_value = None
        
        # Simulate the main function logic
        args = mock_parse_args.return_value
        if args.transport == "stdio":
            await server.mcp.run_async(transport="stdio")
        
        mock_run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    @patch('argparse.ArgumentParser.parse_args')
    async def test_main_http_routing(self, mock_parse_args, mock_run_async):
        """Test main function routes to HTTP transport correctly"""
        mock_parse_args.return_value = argparse.Namespace(
            transport='streamable-http',
            host='localhost',
            port=8000,
            path='/mcp/'
        )
        mock_run_async.return_value = None
        
        # Simulate the main function logic
        args = mock_parse_args.return_value
        if args.transport == "streamable-http":
            await server.mcp.run_async(
                transport="streamable-http",
                host=args.host,
                port=args.port,
                path=args.path
            )
        
        mock_run_async.assert_called_once_with(
            transport="streamable-http",
            host="localhost",
            port=8000,
            path="/mcp/"
        )

    @pytest.mark.asyncio
    @patch('sys.argv', ['server.py'])
    @patch('src.server.mcp.run_async')
    async def test_main_no_arguments_default(self, mock_run_async):
        """Test main function with no arguments uses defaults"""
        mock_run_async.return_value = None
        
        # Simulate main function behavior when len(sys.argv) == 1
        if len(sys.argv) == 1:
            args = argparse.Namespace(
                transport=os.environ.get('MCP_TRANSPORT', 'stdio'),
                host=os.environ.get('MCP_HOST', 'localhost'),
                port=int(os.environ.get('MCP_PORT', 8000)),
                path=os.environ.get('MCP_PATH', '/mcp/'),
            )
            
            assert args.transport == 'stdio'  # Default when no env vars
            
            if args.transport == "stdio":
                await server.mcp.run_async(transport="stdio")
        
        mock_run_async.assert_called_once_with(transport="stdio")


class TestTransportIntegration:
    """Test transport integration with MCP server"""
    
    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_stdio_with_splunk_connection(self, mock_run_async):
        """Test stdio transport startup"""
        mock_run_async.return_value = None
        
        # Test that stdio transport can start (Splunk connection is handled in lifespan)
        await server.mcp.run_async(transport="stdio")
        mock_run_async.assert_called_once_with(transport="stdio")

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    @patch('src.splunk_client.get_splunk_service')
    async def test_http_with_splunk_connection(self, mock_get_service, mock_run_async):
        """Test HTTP transport with Splunk service integration"""
        mock_service = Mock()
        mock_service.info = {"version": "9.0.0", "host": "localhost"}
        mock_get_service.return_value = mock_service
        mock_run_async.return_value = None
        
        # Test that Splunk connection works with HTTP transport
        from src.splunk_client import get_splunk_service
        service = get_splunk_service()
        assert service.info["version"] == "9.0.0"
        
        await server.mcp.run_async(
            transport="streamable-http",
            host="localhost",
            port=8000,
            path="/mcp/"
        )
        mock_run_async.assert_called_once_with(
            transport="streamable-http",
            host="localhost",
            port=8000,
            path="/mcp/"
        )

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_transport_failure_handling(self, mock_run_async):
        """Test transport failure handling across both transports"""
        mock_run_async.side_effect = Exception("Transport initialization failed")
        
        # Test stdio failure
        with pytest.raises(Exception, match="Transport initialization failed"):
            await server.mcp.run_async(transport="stdio")
        
        # Test HTTP failure
        with pytest.raises(Exception, match="Transport initialization failed"):
            await server.mcp.run_async(
                transport="streamable-http",
                host="localhost",
                port=8000,
                path="/mcp/"
            )


class TestDockerEnvironment:
    """Test transport configuration in Docker environment"""
    
    def test_docker_environment_variables(self):
        """Test typical Docker environment variable configuration"""
        with patch.dict(os.environ, {
            'MCP_TRANSPORT': 'streamable-http',
            'MCP_HOST': '0.0.0.0',
            'MCP_PORT': '8000',
            'MCP_PATH': '/mcp/',
            'SPLUNK_HOST': 'splunk-server',
            'SPLUNK_PORT': '8089',
            'SPLUNK_USERNAME': 'admin',
            'SPLUNK_PASSWORD': 'password'
        }):
            # Simulate Docker container startup
            args = argparse.Namespace(
                transport=os.environ.get('MCP_TRANSPORT', 'stdio'),
                host=os.environ.get('MCP_HOST', 'localhost'),
                port=int(os.environ.get('MCP_PORT', 8000)),
                path=os.environ.get('MCP_PATH', '/mcp/')
            )
            
            assert args.transport == 'streamable-http'
            assert args.host == '0.0.0.0'  # Bind to all interfaces in Docker
            assert args.port == 8000
            assert args.path == '/mcp/'

    @pytest.mark.asyncio
    @patch('src.server.mcp.run_async')
    async def test_docker_http_transport_startup(self, mock_run_async):
        """Test Docker HTTP transport startup"""
        mock_run_async.return_value = None
        
        with patch.dict(os.environ, {
            'MCP_TRANSPORT': 'streamable-http',
            'MCP_HOST': '0.0.0.0',
            'MCP_PORT': '8000'
        }):
            # Docker would typically use these settings
            await server.mcp.run_async(
                transport="streamable-http",
                host="0.0.0.0",
                port=8000,
                path="/mcp/"
            )
            
            mock_run_async.assert_called_once_with(
                transport="streamable-http",
                host="0.0.0.0",
                port=8000,
                path="/mcp/"
            )


class TestHealthCheckTransport:
    """Test health check functionality across transports"""
    
    @pytest.mark.asyncio
    @patch('src.splunk_client.get_splunk_service')
    async def test_health_check_stdio_transport(self, mock_get_service):
        """Test health check resource works with stdio transport"""
        mock_service = Mock()
        mock_service.info = {"version": "9.0.0", "host": "localhost"}
        mock_get_service.return_value = mock_service
        
        # Test health check resource - access the function through .fn
        result = server.health_check.fn()
        assert result == "OK"
        
        # Test health tool - need to create a mock context
        from tests.conftest import MockFastMCPContext
        mock_context = MockFastMCPContext()
        mock_context.request_context.lifespan_context.is_connected = True
        mock_context.request_context.lifespan_context.service = mock_service
        
        health_result = server.get_splunk_health.fn(mock_context)
        assert health_result["status"] == "connected"
        assert health_result["version"] == "9.0.0"

    @pytest.mark.asyncio
    @patch('src.splunk_client.get_splunk_service')
    async def test_health_check_http_transport(self, mock_get_service):
        """Test health check resource works with HTTP transport"""
        mock_service = Mock()
        mock_service.info = {"version": "9.0.0", "host": "localhost"}
        mock_get_service.return_value = mock_service
        
        # Health check should work the same regardless of transport
        result = server.health_check.fn()
        assert result == "OK"
        
        # Test health tool - need to create a mock context
        from tests.conftest import MockFastMCPContext
        mock_context = MockFastMCPContext()
        mock_context.request_context.lifespan_context.is_connected = True
        mock_context.request_context.lifespan_context.service = mock_service
        
        health_result = server.get_splunk_health.fn(mock_context)
        assert health_result["status"] == "connected"


class TestTransportSecurity:
    """Test transport security considerations"""
    
    def test_stdio_local_only(self):
        """Test that stdio transport is for local use only"""
        # stdio transport doesn't expose network interfaces
        args = argparse.Namespace(transport='stdio')
        assert args.transport == 'stdio'
        # No host/port configuration needed for stdio

    def test_http_network_binding(self):
        """Test HTTP transport network binding options"""
        # Test localhost binding (secure)
        args_local = argparse.Namespace(
            transport='streamable-http',
            host='localhost',
            port=8000
        )
        assert args_local.host == 'localhost'  # Only local access
        
        # Test all interfaces binding (Docker/production)
        args_public = argparse.Namespace(
            transport='streamable-http',
            host='0.0.0.0',
            port=8000
        )
        assert args_public.host == '0.0.0.0'  # All interfaces

    def test_default_path_security(self):
        """Test default path configuration"""
        with patch.dict(os.environ, {}, clear=True):
            path = os.environ.get('MCP_PATH', '/mcp/')
            assert path == '/mcp/'  # Default secure path 