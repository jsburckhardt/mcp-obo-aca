"""
Integration tests for the Demo MCP Server authentication flow.

These tests validate the complete authentication flow including:
- Server startup with and without authentication
- OAuth metadata endpoints
- Health check endpoint
"""

import sys
from pathlib import Path

import pytest

# Add demo MCP server to path at the BEGINNING of sys.path
demo_mcp_server_path = Path(__file__).parent.parent
sys.path.insert(0, str(demo_mcp_server_path))


class TestServerCreation:
    """Tests for MCP server creation."""

    def test_create_server_without_auth(self, mock_env_auth_disabled):
        """Verify server can be created with auth disabled."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from server import create_fastmcp_server

        # Should not raise any errors
        server = create_fastmcp_server()
        assert server is not None

    def test_create_factory(self, mock_env_auth_disabled):
        """Verify factory can be created with default services."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from server import create_factory

        factory = create_factory()
        summary = factory.get_tool_summary()

        assert summary["total_services"] == 1
        assert summary["total_tools"] == 3
        assert "general" in summary["services"]


class TestOAuthMetadataBuilders:
    """Tests for OAuth metadata builders."""

    def test_build_api_scopes_with_client_id(self, mock_env_auth_disabled):
        """Verify API scopes are built correctly."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from server import build_api_scopes

        scopes = build_api_scopes("test-client-id")

        assert len(scopes) == 5
        assert "api://test-client-id/access_as_user" in scopes
        assert "api://test-client-id/MCP.Tools" in scopes

    def test_build_api_scopes_without_client_id(self, mock_env_auth_disabled):
        """Verify empty list when no client ID."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from server import build_api_scopes

        scopes = build_api_scopes(None)
        assert scopes == []

    def test_build_protected_resource_metadata(self, mock_env_full_auth):
        """Verify protected resource metadata is built correctly."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from server import build_protected_resource_metadata

        config_obj = config.settings.get_mcp_config()
        metadata = build_protected_resource_metadata(config_obj)

        assert "resource" in metadata
        assert "bearer_methods_supported" in metadata
        assert metadata["bearer_methods_supported"] == ["header"]


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_validate_auth_config_disabled(self, mock_env_auth_disabled):
        """Verify validation passes when auth is disabled."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from server import validate_auth_config

        config_obj = config.settings.get_mcp_config()
        # Should not raise
        validate_auth_config(config_obj)

    def test_validate_auth_config_missing_required(self, mock_env_missing_secret):
        """Verify validation fails when auth enabled but missing config."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from core.exceptions import ConfigurationError
        from server import validate_auth_config

        # Create config with auth enabled but missing fields
        config_obj = config.settings.get_mcp_config()
        # Force enable_auth to True
        config_obj = config_obj.model_copy(update={"enable_auth": True})

        with pytest.raises(ConfigurationError):
            validate_auth_config(config_obj)


class TestResourceServerURL:
    """Tests for resource server URL generation."""

    def test_get_resource_server_url_default(self, mock_env_auth_disabled):
        """Verify default resource server URL is constructed."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from config.settings import get_resource_server_url

        url = get_resource_server_url()

        # Default should be http://localhost:9000
        assert "localhost" in url or "127.0.0.1" in url

    def test_get_authorization_server_url_from_tenant(self, mock_env_full_auth):
        """Verify authorization server URL is constructed from tenant."""
        import importlib

        import config.settings

        importlib.reload(config.settings)

        from config.settings import get_authorization_server_url

        url = get_authorization_server_url()

        assert url is not None
        assert "login.microsoftonline.com" in url
        assert "test-tenant-12345" in url
