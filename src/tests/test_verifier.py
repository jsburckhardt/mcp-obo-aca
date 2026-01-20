"""
Tests for EntraIdTokenVerifier.

Tests validate:
- JWKS fetching and caching
- Valid token verification
- Expired token handling
- Invalid audience handling
- Missing kid error handling
- Scope extraction from scp and roles claims
"""

import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp.server.auth import AccessToken

# Add demo MCP server to path
demo_mcp_server_path = Path(__file__).parent.parent
sys.path.insert(0, str(demo_mcp_server_path))

# Test constants
TEST_TENANT_ID = "test-tenant-12345"
TEST_CLIENT_ID = "test-client-67890"
TEST_KID = "test-key-id-001"


def create_mock_get_session(mock_response):
    """Create a properly mocked aiohttp.ClientSession for GET requests."""

    @asynccontextmanager
    async def mock_get(*args, **kwargs):
        yield mock_response

    mock_session = MagicMock()
    mock_session.get = mock_get

    mock_client = MagicMock()
    mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

    return mock_client


class TestJWKSFetching:
    """JWKS fetching and caching tests."""

    @pytest.mark.asyncio
    async def test_jwks_fetch_success(self, entra_verifier, test_jwks):
        """Verify JWKS is fetched successfully from Azure AD."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            jwks = await entra_verifier._get_jwks()

            assert jwks is not None
            assert "keys" in jwks
            assert len(jwks["keys"]) > 0

    @pytest.mark.asyncio
    async def test_jwks_cache_reuse(self, entra_verifier, test_jwks):
        """Verify JWKS cache is reused on second fetch."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            # First fetch
            jwks1 = await entra_verifier._get_jwks()

            # Second fetch should use cache (no HTTP call)
            jwks2 = await entra_verifier._get_jwks()

            # Both should be the same cached instance
            assert jwks1 is jwks2

            # HTTP call should only happen once
            assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_jwks_cache_expiry(self, entra_verifier, test_jwks):
        """Verify JWKS cache expires after 1 hour."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            # First fetch
            await entra_verifier._get_jwks()

            # Simulate cache expiry by setting expiry to the past
            entra_verifier._cache_expiry = datetime.now(timezone.utc) - timedelta(
                hours=1
            )

            # Second fetch should make new HTTP call
            await entra_verifier._get_jwks()

            # HTTP call should happen twice
            assert mock_session.get.call_count == 2


class TestTokenVerification:
    """Token verification tests."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(
        self, entra_verifier, valid_test_token, test_jwks
    ):
        """Verify valid token is verified successfully."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await entra_verifier.verify_token(valid_test_token)

            assert result is not None
            assert isinstance(result, AccessToken)
            assert result.token == valid_test_token
            assert result.claims is not None
            assert result.claims.get("sub") == "test-user-12345"

    @pytest.mark.asyncio
    async def test_verify_expired_token_returns_none(
        self, entra_verifier, expired_test_token, test_jwks
    ):
        """Verify expired token returns None."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await entra_verifier.verify_token(expired_test_token)

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_invalid_audience_returns_none(
        self, entra_verifier, token_wrong_audience, test_jwks
    ):
        """Verify token with wrong audience returns None."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await entra_verifier.verify_token(token_wrong_audience)

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_missing_kid_returns_none(
        self, entra_verifier, token_no_kid, test_jwks
    ):
        """Verify token without 'kid' in header returns None."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await entra_verifier.verify_token(token_no_kid)

            assert result is None


class TestScopeExtraction:
    """Scope extraction tests."""

    @pytest.mark.asyncio
    async def test_scope_extraction_from_scp(
        self, entra_verifier, create_test_token, test_jwks
    ):
        """Verify scopes are extracted from 'scp' claim."""
        token = create_test_token(
            {"sub": "test-user", "scp": "User.Read profile email"}
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await entra_verifier.verify_token(token)

            assert result is not None
            assert result.scopes is not None
            # Scopes should be prefixed with api://client_id/
            expected_scopes = [
                f"api://{TEST_CLIENT_ID}/User.Read",
                f"api://{TEST_CLIENT_ID}/profile",
                f"api://{TEST_CLIENT_ID}/email",
            ]
            assert set(result.scopes) == set(expected_scopes)

    @pytest.mark.asyncio
    async def test_scope_extraction_from_roles(
        self, entra_verifier, token_with_roles, test_jwks
    ):
        """Verify scopes are extracted from 'roles' claim."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=test_jwks)

        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        with patch("aiohttp.ClientSession") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client.return_value.__aexit__ = AsyncMock()

            result = await entra_verifier.verify_token(token_with_roles)

            assert result is not None
            assert result.scopes is not None
            # Roles should be prefixed with api://client_id/
            expected_scopes = [
                f"api://{TEST_CLIENT_ID}/Admin",
                f"api://{TEST_CLIENT_ID}/Reader",
                f"api://{TEST_CLIENT_ID}/Writer",
            ]
            assert set(result.scopes) == set(expected_scopes)


class TestVerifierInitialization:
    """Tests for EntraIdTokenVerifier initialization."""

    def test_verifier_initialization(self):
        """Verify verifier initializes with correct JWKS URI and issuer."""
        from auth.verifier import EntraIdTokenVerifier

        verifier = EntraIdTokenVerifier(
            tenant_id="my-tenant-id", client_id="my-client-id"
        )

        assert verifier.tenant_id == "my-tenant-id"
        assert verifier.client_id == "my-client-id"
        assert (
            verifier.jwks_uri
            == "https://login.microsoftonline.com/my-tenant-id/discovery/v2.0/keys"
        )
        assert verifier.issuer == "https://login.microsoftonline.com/my-tenant-id/v2.0"

    def test_verifier_initialization_with_custom_urls(self):
        """Verify verifier accepts custom JWKS URI and issuer."""
        from auth.verifier import EntraIdTokenVerifier

        verifier = EntraIdTokenVerifier(
            tenant_id="my-tenant-id",
            client_id="my-client-id",
            jwks_uri="https://custom.issuer.com/jwks",
            issuer="https://custom.issuer.com",
        )

        assert verifier.jwks_uri == "https://custom.issuer.com/jwks"
        assert verifier.issuer == "https://custom.issuer.com"
