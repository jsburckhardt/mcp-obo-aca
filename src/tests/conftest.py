"""
Test configuration for Demo MCP Server tests.

Provides shared fixtures for:
- RSA key pairs for signing test JWTs
- Mock JWKS responses
- Test token generation
- Mock Azure AD/Graph API responses
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple
from unittest.mock import AsyncMock, Mock

import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# =============================================================================
# Pre-collection environment setup (runs BEFORE test modules are imported)
# =============================================================================


def pytest_configure(config):
    """Set required environment variables before test collection.

    This hook runs before pytest collects tests, ensuring that imports
    of modules like config.settings don't fail due to missing env vars.
    """
    # Disable auth by default for tests
    os.environ.setdefault("ENABLE_AUTH", "false")


# Add the demo MCP server to path
demo_mcp_server_path = Path(__file__).parent.parent
sys.path.insert(0, str(demo_mcp_server_path))


# =============================================================================
# Test Constants
# =============================================================================

TEST_TENANT_ID = "test-tenant-12345"
TEST_CLIENT_ID = "test-client-67890"
TEST_CLIENT_SECRET = "test-secret-abcdef"
TEST_KID = "test-key-id-001"


# =============================================================================
# Auto-use fixture to prevent .env file loading
# =============================================================================


@pytest.fixture(autouse=True)
def prevent_dotenv_loading(monkeypatch, tmp_path):
    """Prevent Pydantic settings from reading .env file during tests.

    This fixture runs automatically before each test to ensure
    environment isolation from the development .env file.
    """
    # Change to temp directory so Pydantic can't find .env
    original_cwd = os.getcwd()

    # Create empty .env file in temp directory
    empty_env = tmp_path / ".env"
    empty_env.write_text("")

    # Change to temp directory
    os.chdir(tmp_path)

    yield

    # Restore original directory
    os.chdir(original_cwd)


# =============================================================================
# RSA Key Pair Fixtures (for JWT signing)
# =============================================================================


@pytest.fixture(scope="session")
def rsa_key_pair() -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Generate RSA key pair for test token signing.

    Session-scoped for performance - same keys used across all tests.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(scope="session")
def private_key_pem(rsa_key_pair) -> bytes:
    """Get PEM-encoded private key for JWT signing."""
    private_key, _ = rsa_key_pair
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture(scope="session")
def public_key_pem(rsa_key_pair) -> bytes:
    """Get PEM-encoded public key."""
    _, public_key = rsa_key_pair
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


# =============================================================================
# JWKS Fixtures
# =============================================================================


def _int_to_base64url(n: int) -> str:
    """Convert integer to base64url-encoded string (for JWKS)."""
    byte_length = (n.bit_length() + 7) // 8
    n_bytes = n.to_bytes(byte_length, byteorder="big")
    return base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode("ascii")


@pytest.fixture(scope="session")
def test_jwks(rsa_key_pair) -> Dict[str, Any]:
    """Generate JWKS containing the test public key.

    This mimics the response from Azure AD's JWKS endpoint.
    """
    _, public_key = rsa_key_pair
    public_numbers = public_key.public_numbers()

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": TEST_KID,
                "n": _int_to_base64url(public_numbers.n),
                "e": _int_to_base64url(public_numbers.e),
                "alg": "RS256",
            }
        ]
    }


# =============================================================================
# Token Generation Fixtures
# =============================================================================


@pytest.fixture
def create_test_token(private_key_pem):
    """Factory fixture to create signed test JWTs.

    Usage:
        token = create_test_token({"sub": "user123", "aud": "client-id"})
    """

    def _create_token(
        claims: Dict[str, Any],
        kid: str = TEST_KID,
        algorithm: str = "RS256",
        expires_in: int = 3600,
    ) -> str:
        # Set default claims
        now = int(time.time())
        default_claims = {
            "iss": f"https://login.microsoftonline.com/{TEST_TENANT_ID}/v2.0",
            "aud": TEST_CLIENT_ID,
            "iat": now,
            "nbf": now,
            "exp": now + expires_in,
            "sub": "test-user-subject",
        }
        # Merge with provided claims
        default_claims.update(claims)

        # Create token with kid in header
        return jwt.encode(
            default_claims, private_key_pem, algorithm=algorithm, headers={"kid": kid}
        )

    return _create_token


@pytest.fixture
def valid_test_token(create_test_token) -> str:
    """Create a valid test token with standard claims."""
    return create_test_token(
        {
            "sub": "test-user-12345",
            "oid": "test-oid-67890",
            "scp": "User.Read profile",
            "name": "Test User",
            "email": "testuser@example.com",
        }
    )


@pytest.fixture
def expired_test_token(create_test_token) -> str:
    """Create an expired test token."""
    return create_test_token(
        {"sub": "expired-user"},
        expires_in=-3600,  # Expired 1 hour ago
    )


@pytest.fixture
def expiring_soon_token(create_test_token) -> str:
    """Create a token expiring in 2 minutes (< 5 minute buffer)."""
    return create_test_token(
        {"sub": "expiring-user"},
        expires_in=120,  # 2 minutes
    )


@pytest.fixture
def token_with_roles(create_test_token) -> str:
    """Create a token with 'roles' claim instead of 'scp'."""
    return create_test_token(
        {"sub": "app-user", "roles": ["Admin", "Reader", "Writer"]}
    )


@pytest.fixture
def token_wrong_audience(private_key_pem) -> str:
    """Create a token with wrong audience."""
    now = int(time.time())
    return jwt.encode(
        {
            "iss": f"https://login.microsoftonline.com/{TEST_TENANT_ID}/v2.0",
            "aud": "wrong-client-id",
            "iat": now,
            "exp": now + 3600,
            "sub": "wrong-aud-user",
        },
        private_key_pem,
        algorithm="RS256",
        headers={"kid": TEST_KID},
    )


@pytest.fixture
def token_no_kid(private_key_pem) -> str:
    """Create a token without 'kid' in header."""
    now = int(time.time())
    return jwt.encode(
        {
            "iss": f"https://login.microsoftonline.com/{TEST_TENANT_ID}/v2.0",
            "aud": TEST_CLIENT_ID,
            "iat": now,
            "exp": now + 3600,
            "sub": "no-kid-user",
        },
        private_key_pem,
        algorithm="RS256",
        # No headers with kid
    )


# =============================================================================
# Mock HTTP Response Fixtures
# =============================================================================


@pytest.fixture
def mock_jwks_response(test_jwks):
    """Create a mock aiohttp response for JWKS endpoint."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=test_jwks)
    mock_response.text = AsyncMock(return_value=json.dumps(test_jwks))
    return mock_response


@pytest.fixture
def mock_obo_success_response():
    """Create a mock successful OBO token response."""
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
    return mock_response


@pytest.fixture
def mock_obo_error_response():
    """Create a mock OBO error response."""
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.json = AsyncMock(
        return_value={
            "error": "invalid_grant",
            "error_description": "AADSTS50013: Assertion is not within its valid time range.",
        }
    )
    return mock_response


@pytest.fixture
def mock_graph_me_response():
    """Create a mock Graph API /me response."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={
            "displayName": "Test User",
            "mail": "testuser@example.com",
            "givenName": "Test",
            "surname": "User",
            "userPrincipalName": "testuser@example.com",
            "id": "user-graph-id-12345",
        }
    )
    return mock_response


# =============================================================================
# Environment Variable Fixtures
# =============================================================================


def _clear_auth_env(monkeypatch):
    """Helper to clear any existing auth environment variables."""
    for var in [
        "TENANT_ID",
        "CLIENT_ID",
        "CLIENT_SECRET",
        "ENABLE_AUTH",
        "GRAPH_SCOPE",
        "JWKS_URI",
        "ISSUER",
        "AUDIENCE",
        "RESOURCE_SERVER_URL",
        "AUTHORIZATION_SERVER_URL",
    ]:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def mock_env_full_auth(monkeypatch):
    """Set all required environment variables for full auth config."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setenv("CLIENT_ID", TEST_CLIENT_ID)
    monkeypatch.setenv("CLIENT_SECRET", TEST_CLIENT_SECRET)
    monkeypatch.setenv("GRAPH_SCOPE", "User.Read")
    monkeypatch.setenv(
        "JWKS_URI",
        f"https://login.microsoftonline.com/{TEST_TENANT_ID}/discovery/v2.0/keys",
    )
    monkeypatch.setenv(
        "ISSUER", f"https://login.microsoftonline.com/{TEST_TENANT_ID}/v2.0"
    )
    monkeypatch.setenv("AUDIENCE", TEST_CLIENT_ID)


@pytest.fixture
def mock_env_auth_disabled(monkeypatch):
    """Set environment variables with auth disabled."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENABLE_AUTH", "false")


@pytest.fixture
def mock_env_missing_secret(monkeypatch):
    """Set environment variables with auth enabled but missing CLIENT_SECRET."""
    _clear_auth_env(monkeypatch)
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("TENANT_ID", TEST_TENANT_ID)
    monkeypatch.setenv("CLIENT_ID", TEST_CLIENT_ID)
    # CLIENT_SECRET intentionally not set


# =============================================================================
# Verifier Fixtures
# =============================================================================


@pytest.fixture
def entra_verifier():
    """Create an EntraIdTokenVerifier instance for testing."""
    from auth.verifier import EntraIdTokenVerifier

    return EntraIdTokenVerifier(tenant_id=TEST_TENANT_ID, client_id=TEST_CLIENT_ID)


# =============================================================================
# Mock Context Fixtures (for auth_utils tests)
# =============================================================================


def create_mock_context(token: str | None = None):
    """Create a mock FastMCP Context with an authorization header."""
    ctx = Mock()
    ctx.request_context = Mock()
    ctx.request_context.request = Mock()

    if token:
        ctx.request_context.request.headers = {"Authorization": f"Bearer {token}"}
    else:
        ctx.request_context.request.headers = {}

    return ctx


@pytest.fixture
def mock_context_factory():
    """Factory for creating mock contexts."""
    return create_mock_context


# =============================================================================
# MCP Server Fixtures
# =============================================================================


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing."""

    class MockMCP:
        def __init__(self):
            self.tools = []

        def tool(self, tags=None):
            def decorator(func):
                self.tools.append({"func": func, "tags": tags or []})
                return func

            return decorator

    return MockMCP()


@pytest.fixture
def general_service():
    """General service fixture."""
    from services.general_service import GeneralService

    return GeneralService()
