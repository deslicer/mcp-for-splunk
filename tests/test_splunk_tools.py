"""
Tests for Splunk tools functionality.
"""

from unittest.mock import Mock, patch

from src import server


class TestSplunkHealthTool:
    """Test the health check functionality"""

    def test_health_check_success(self, mock_context):
        """Test successful health check"""
        # Set up the mock context
        mock_context.request_context.lifespan_context.is_connected = True
        mock_context.request_context.lifespan_context.service = Mock()
        mock_context.request_context.lifespan_context.service.info = {
            "version": "9.0.0",
            "host": "localhost",
        }

        result = server.get_splunk_health.fn(mock_context)

        assert result["status"] == "connected"
        assert result["version"] == "9.0.0"
        assert result["server_name"] == "localhost"

    def test_health_check_failure(self, mock_context):
        """Test health check failure"""
        # Simulate disconnected state
        mock_context.request_context.lifespan_context.is_connected = False
        mock_context.request_context.lifespan_context.service = None

        result = server.get_splunk_health.fn(mock_context)

        assert result["status"] == "disconnected"
        assert "Splunk service is not available" in result["error"]

    def test_health_check_missing_host(self, mock_context):
        """Test health check with missing host information"""
        mock_context.request_context.lifespan_context.is_connected = True
        mock_context.request_context.lifespan_context.service = Mock()
        mock_context.request_context.lifespan_context.service.info = {
            "version": "9.0.0"  # Missing host
        }

        result = server.get_splunk_health.fn(mock_context)

        assert result["status"] == "connected"
        assert result["version"] == "9.0.0"
        assert result["server_name"] == "unknown"


class TestIndexTools:
    """Test index-related tools"""

    def test_list_indexes_success(self, mock_context):
        """Test successful index listing (excludes internal indexes)"""
        result = server.list_indexes.fn(mock_context)

        assert "indexes" in result
        assert "count" in result
        assert "total_count_including_internal" in result
        assert result["count"] == 3  # Only customer indexes
        assert result["total_count_including_internal"] == 4  # All indexes including internal
        expected_indexes = ["main", "security", "test"]  # Excludes _internal
        assert sorted(result["indexes"]) == expected_indexes


class TestMetadataTools:
    """Test metadata tools (sourcetypes and sources)"""

    def test_list_sourcetypes_success(self, mock_context, mock_results_reader):
        """Test successful sourcetype listing"""
        with patch("src.server.ResultsReader", mock_results_reader):
            # Mock the oneshot job
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()

            # Mock ResultsReader with sourcetype data
            sourcetype_results = [
                {"sourcetype": "access_combined"},
                {"sourcetype": "splunkd"},
                {"sourcetype": "web_service"},
            ]
            with patch("src.server.ResultsReader") as mock_reader:
                mock_reader.return_value = iter(sourcetype_results)

                result = server.list_sourcetypes.fn(mock_context)

                assert "sourcetypes" in result
                assert "count" in result
                assert result["count"] == 3
                expected_sourcetypes = ["access_combined", "splunkd", "web_service"]
                assert sorted(result["sourcetypes"]) == expected_sourcetypes

    def test_list_sources_success(self, mock_context):
        """Test successful source listing"""
        with patch("src.server.ResultsReader") as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()

            source_results = [{"source": "/var/log/system.log"}, {"source": "/var/log/app.log"}]
            mock_reader.return_value = iter(source_results)

            result = server.list_sources.fn(mock_context)

            assert "sources" in result
            assert "count" in result
            assert result["count"] == 2


class TestSearchTools:
    """Test search functionality"""

    def test_run_oneshot_search_basic(self, mock_context, mock_search_results):
        """Test basic oneshot search"""
        with patch("src.server.ResultsReader") as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)

            result = server.run_oneshot_search.fn(
                mock_context,
                query="index=main",
                earliest_time="-1h",
                latest_time="now",
                max_results=10,
            )

            assert "results" in result
            assert "results_count" in result
            assert "query_executed" in result
            assert result["results_count"] == 3
            assert "search index=main" in result["query_executed"]

    def test_run_oneshot_search_with_pipe(self, mock_context, mock_search_results):
        """Test oneshot search with pipe command (no prefix modification)"""
        with patch("src.server.ResultsReader") as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)

            result = server.run_oneshot_search.fn(mock_context, query="| stats count by log_level")

            assert result["query_executed"] == "| stats count by log_level"

    def test_run_oneshot_search_with_search_prefix(self, mock_context, mock_search_results):
        """Test oneshot search that already has search prefix"""
        with patch("src.server.ResultsReader") as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)

            result = server.run_oneshot_search.fn(mock_context, query="search index=main")

            assert result["query_executed"] == "search index=main"

    def test_run_oneshot_search_max_results_limit(self, mock_context):
        """Test oneshot search with max results limiting"""
        large_results = [{"result": i} for i in range(150)]

        with patch("src.server.ResultsReader") as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(large_results)

            result = server.run_oneshot_search.fn(mock_context, query="index=main", max_results=100)

            assert result["results_count"] == 100

    def test_run_oneshot_search_error(self, mock_context):
        """Test oneshot search error handling"""
        # Simulate disconnected state which causes error response instead of exception
        mock_context.request_context.lifespan_context.is_connected = False
        mock_context.request_context.lifespan_context.service = None

        result = server.run_oneshot_search.fn(mock_context, query="index=main")

        assert result["status"] == "error"
        assert "Splunk service is not available" in result["error"]


class TestAppAndUserTools:
    """Test app and user management tools"""

    def test_list_apps_success(self, mock_context):
        """Test successful app listing"""
        result = server.list_apps.fn(mock_context)

        assert "apps" in result
        assert "count" in result
        assert result["count"] == 3
        app_names = [app["name"] for app in result["apps"]]
        expected_apps = ["search", "splunk_monitoring_console", "learned"]
        assert sorted(app_names) == sorted(expected_apps)

    def test_list_users_success(self, mock_context):
        """Test successful user listing"""
        result = server.list_users.fn(mock_context)

        assert "users" in result
        assert "count" in result
        assert result["count"] == 2
        user_names = [user["username"] for user in result["users"]]
        expected_users = ["admin", "splunk-system-user"]
        assert sorted(user_names) == sorted(expected_users)


class TestKVStoreTools:
    """Test KV Store tools"""

    def test_list_kvstore_collections_specific_app(self, mock_context):
        """Test listing KV Store collections for specific app"""
        # Mock the kvstore structure
        mock_kvstore = Mock()
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_kvstore.__iter__ = Mock(return_value=iter([mock_collection]))
        mock_context.request_context.lifespan_context.service.kvstore = {"search": mock_kvstore}

        result = server.list_kvstore_collections.fn(mock_context, app="search")

        assert "collections" in result
        assert "count" in result

    def test_get_kvstore_data_success(self, mock_context, mock_kvstore_collection_data):
        """Test successful KV Store data retrieval"""
        # Mock the collection structure
        mock_collection = Mock()
        mock_collection.data.query.return_value = mock_kvstore_collection_data
        mock_kvstore = Mock()
        mock_kvstore.__getitem__ = Mock(return_value=mock_collection)
        mock_context.request_context.lifespan_context.service.kvstore = {"search": mock_kvstore}

        result = server.get_kvstore_data.fn(mock_context, collection="users", app="search")

        assert "documents" in result
        assert "count" in result


class TestConfigurationTools:
    """Test configuration management tools"""

    def test_get_configurations_all_stanzas(self, mock_context):
        """Test getting all configuration stanzas"""
        # Mock configuration data
        mock_stanza = Mock()
        mock_stanza.name = "stanza1"
        mock_stanza.content = {"setting1": "value1", "setting2": "value2"}
        mock_conf = Mock()
        mock_conf.__iter__ = Mock(return_value=iter([mock_stanza]))
        mock_context.request_context.lifespan_context.service.confs = {"props": mock_conf}

        result = server.get_configurations.fn(mock_context, conf_file="props")

        assert "file" in result
        assert "stanzas" in result
        assert result["file"] == "props"
        assert len(result["stanzas"]) == 1
        assert "stanza1" in result["stanzas"]

    def test_get_configurations_specific_stanza(self, mock_context):
        """Test getting specific configuration stanza"""
        # Mock specific stanza
        mock_conf = Mock()
        mock_stanza = Mock()
        mock_stanza.content = {"setting1": "value1"}
        mock_conf.__getitem__ = Mock(return_value=mock_stanza)
        mock_context.request_context.lifespan_context.service.confs = {"props": mock_conf}

        result = server.get_configurations.fn(mock_context, conf_file="props", stanza="default")

        assert "stanza" in result
        assert "settings" in result
        assert result["stanza"] == "default"
        assert result["settings"]["setting1"] == "value1"


class TestToolIntegration:
    """Test integration between multiple tools"""

    def test_health_check_before_operations(self, mock_context):
        """Test health check workflow before operations"""
        # First check health
        mock_context.request_context.lifespan_context.is_connected = True
        mock_context.request_context.lifespan_context.service = Mock()
        mock_context.request_context.lifespan_context.service.info = {
            "version": "9.0.0",
            "host": "localhost",
        }

        health_result = server.get_splunk_health.fn(mock_context)
        assert health_result["status"] == "connected"

        # Then perform operation
        indexes_result = server.list_indexes.fn(mock_context)
        assert "indexes" in indexes_result

    def test_search_workflow(self, mock_context, mock_search_results):
        """Test complete search workflow"""
        # First list indexes
        indexes_result = server.list_indexes.fn(mock_context)
        assert "indexes" in indexes_result

        # Then perform search
        with patch("src.server.ResultsReader") as mock_reader:
            mock_context.request_context.lifespan_context.service.jobs.oneshot.return_value = Mock()
            mock_reader.return_value = iter(mock_search_results)

            search_result = server.run_oneshot_search.fn(mock_context, query="index=main | head 5")

            assert "results" in search_result
            assert search_result["results_count"] > 0
