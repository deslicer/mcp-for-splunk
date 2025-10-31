import importlib


def test_plugins_disabled_returns_zero(monkeypatch):
    # Ensure disabled
    monkeypatch.setenv("MCP_DISABLE_PLUGINS", "true")
    # Import lazily to pick up env
    server = importlib.import_module("src.server")
    count = server.load_plugins(server.mcp)
    assert count == 0


def test_load_plugins_invokes_setup(monkeypatch):
    # Enable plugins
    monkeypatch.delenv("MCP_DISABLE_PLUGINS", raising=False)
    # Use default group
    monkeypatch.delenv("MCP_PLUGIN_GROUP", raising=False)

    called = []

    def setup_fn(*, mcp=None, root_app=None):
        called.append((mcp, root_app))

    class FakeEntryPoint:
        name = "fake_auth"

        @staticmethod
        def load():
            return setup_fn

    class FakeEntryPoints:
        def select(self, group):
            # Only respond to the expected group
            if group == "mcp_splunk.plugins":
                return [FakeEntryPoint()]
            return []

    # Import server and patch its imported symbol directly
    server = importlib.import_module("src.server")
    monkeypatch.setattr(server, "entry_points", lambda: FakeEntryPoints(), raising=True)
    # Call MCP stage
    count1 = server.load_plugins(server.mcp)
    # Call HTTP stage (root_app None for test)
    count2 = server.load_plugins(server.mcp, None)

    assert count1 == 1
    assert count2 == 1
    # Two calls total
    assert len(called) == 2
