"""
Tests for OBO (On-Behalf-Of) token exchange.

Tests validate:
- Token expiring soon (< 5 min)
- Missing credentials
- Client secret flow
- Consent error handling
"""

import importlib
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# Add demo MCP server to path
demo_mcp_server_path = Path(__file__).parent.parent
sys.path.insert(0, str(demo_mcp_server_path))

# Test constants
TEST_TENANT_ID = "test-tenant-12345"
TEST_CLIENT_ID = "test-client-67890"
TEST_CLIENT_SECRET = "test-secret-abcdef"


def create_mock_session(mock_response):
    """Create a properly mocked aiohttp.ClientSession with async context managers."""

    @asynccontextmanager
    async def mock_post(*args, **kwargs):
        yield mock_response

    mock_session = MagicMock()
    mock_session.post = mock_post

    @asynccontextmanager
    async def mock_session_cm():
        yield mock_session

    mock_client = MagicMock()
    mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

    return mock_client, mock_session


def create_mock_session_with_capture(mock_response, captured_data):
    """Create a mock session that captures POST data."""

    @asynccontextmanager
    async def mock_post(*args, **kwargs):
        captured_data.update(kwargs.get("data", {}))
        yield mock_response

    mock_session = MagicMock()
    mock_session.post = mock_post

    mock_client = MagicMock()
    mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

    return mock_client


class TestOBOMissingCredentials:
    """Missing credentials tests."""

    @pytest.mark.asyncio
    async def test_obo_missing_all_credentials_raises(
        self, mock_env_missing_secret, create_test_token
    ):
        """Verify RuntimeError is raised when neither FEDERATED_CREDENTIAL_OID nor CLIENT_SECRET is configured."""
        # Reload config to pick up environment changes
        import config.settings

        importlib.reload(config.settings)

        # Verify both credentials are not set
        assert config.settings.get_mcp_config().client_secret is None
        assert config.settings.get_mcp_config().federated_credential_oid is None

        # Reload obo module to get updated config
        import auth.obo

        importlib.reload(auth.obo)

        from auth.obo import get_graph_token_obo

        token = create_test_token({"sub": "test-user"})

        with pytest.raises(RuntimeError, match="OBO flow not configured"):
            await get_graph_token_obo(token)


class TestOBOTokenExpiry:
    """Token expiring soon tests."""

    @pytest.mark.asyncio
    async def test_obo_rejects_expiring_token(
        self, mock_env_full_auth, expiring_soon_token
    ):
        """Verify RuntimeError is raised for token expiring in < 5 minutes."""
        # Reload config to pick up environment changes
        import config.settings

        importlib.reload(config.settings)

        import auth.obo

        importlib.reload(auth.obo)

        from auth.obo import get_graph_token_obo

        with pytest.raises(RuntimeError, match="expiring soon"):
            await get_graph_token_obo(expiring_soon_token)


class TestOBOClientSecret:
    """Tests for client secret OBO flow."""

    @pytest.mark.asyncio
    async def test_obo_client_secret_success(
        self, mock_env_full_auth, valid_test_token
    ):
        """Verify successful OBO exchange using client secret."""
        import config.settings

        importlib.reload(config.settings)

        # Ensure federated credential is not set (to use client secret path)
        object.__setattr__(
            config.settings.get_mcp_config(), "federated_credential_oid", None
        )

        import auth.obo

        importlib.reload(auth.obo)

        from auth.obo import get_graph_token_obo

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "token_type": "Bearer",
                "access_token": "mock-graph-access-token-xyz",
                "expires_in": 3600,
                "scope": "User.Read",
            }
        )

        mock_client, _ = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", mock_client):
            result = await get_graph_token_obo(valid_test_token)

        assert result == "mock-graph-access-token-xyz"

    @pytest.mark.asyncio
    async def test_obo_client_secret_network_error_handling(
        self, mock_env_full_auth, valid_test_token
    ):
        """Verify OBO handles network errors correctly."""

        import config.settings

        importlib.reload(config.settings)

        # Ensure federated credential is not set
        object.__setattr__(
            config.settings.get_mcp_config(), "federated_credential_oid", None
        )

        import auth.obo

        importlib.reload(auth.obo)

        from auth.obo import get_graph_token_obo

        mock_client = MagicMock()
        mock_client.return_value.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientError("Network error")
        )

        with patch("aiohttp.ClientSession", mock_client):
            with pytest.raises(RuntimeError, match="OBO network error"):
                await get_graph_token_obo(valid_test_token)


class TestOBOConsentErrors:
    """Tests for consent-related OBO errors."""

    @pytest.mark.asyncio
    async def test_obo_consent_required_error(
        self, mock_env_full_auth, valid_test_token
    ):
        """Verify OBO handles AADSTS65001 (consent required) error."""
        import config.settings

        importlib.reload(config.settings)

        # Ensure federated credential is not set
        object.__setattr__(
            config.settings.get_mcp_config(), "federated_credential_oid", None
        )

        import auth.obo

        importlib.reload(auth.obo)

        from auth.obo import get_graph_token_obo

        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(
            return_value={
                "error": "invalid_grant",
                "error_description": "AADSTS65001: The user or administrator has not consented to use the application.",
            }
        )

        mock_client, _ = create_mock_session(mock_response)

        with patch("aiohttp.ClientSession", mock_client):
            with pytest.raises(RuntimeError, match="consent required"):
                await get_graph_token_obo(valid_test_token)


class TestOBORequestPayload:
    """Tests for OBO request payload construction."""

    @pytest.mark.asyncio
    async def test_obo_request_contains_correct_grant_type(
        self, mock_env_full_auth, valid_test_token
    ):
        """Verify OBO request uses correct grant type."""
        import config.settings

        importlib.reload(config.settings)

        # Ensure federated credential is not set
        object.__setattr__(
            config.settings.get_mcp_config(), "federated_credential_oid", None
        )

        import auth.obo

        importlib.reload(auth.obo)

        from auth.obo import get_graph_token_obo

        captured_data = {}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"access_token": "mock-token", "expires_in": 3600}
        )

        mock_client = create_mock_session_with_capture(mock_response, captured_data)

        with patch("aiohttp.ClientSession", mock_client):
            await get_graph_token_obo(valid_test_token)

        assert (
            captured_data.get("grant_type")
            == "urn:ietf:params:oauth:grant-type:jwt-bearer"
        )
        assert captured_data.get("requested_token_use") == "on_behalf_of"

    @pytest.mark.asyncio
    async def test_obo_request_contains_assertion(
        self, mock_env_full_auth, valid_test_token
    ):
        """Verify OBO request contains the assertion token."""
        import config.settings

        importlib.reload(config.settings)

        # Ensure federated credential is not set
        object.__setattr__(
            config.settings.get_mcp_config(), "federated_credential_oid", None
        )

        import auth.obo

        importlib.reload(auth.obo)

        from auth.obo import get_graph_token_obo

        captured_data = {}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"access_token": "mock-token", "expires_in": 3600}
        )

        mock_client = create_mock_session_with_capture(mock_response, captured_data)

        with patch("aiohttp.ClientSession", mock_client):
            await get_graph_token_obo(valid_test_token)

        assert captured_data.get("assertion") == valid_test_token
