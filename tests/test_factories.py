from fastmcp import FastMCP
from starlette.applications import Starlette

from src.server import create_root_app, get_mcp


def test_get_mcp_returns_fastmcp():
    server = get_mcp()
    assert isinstance(server, FastMCP)


def test_create_root_app_returns_starlette_app():
    mcp = get_mcp()
    app = create_root_app(mcp)
    assert app is not None
    assert isinstance(app, Starlette)

