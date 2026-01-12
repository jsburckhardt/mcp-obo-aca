"""
Custom Entra ID token verifier with JWKS caching.

This module implements Azure AD-specific JWT token verification with:
- JWKS fetching and caching (1-hour TTL)
- Token signature verification using Azure AD public keys
- Scope extraction from both 'scp' and 'roles' claims
- Comprehensive error handling with descriptive logging
- FastMCP TokenVerifier compatibility for middleware integration
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import aiohttp
import jwt
from fastmcp.server.auth import AccessToken, TokenVerifier
from jwt.algorithms import RSAAlgorithm
from pydantic import AnyHttpUrl

logger = logging.getLogger(__name__)


class EntraIdTokenVerifier(TokenVerifier):
    """JWT token verifier for Microsoft Entra ID (Azure AD).

    Extends FastMCP's TokenVerifier to provide Azure AD-specific token verification
    with JWKS caching for performance. Supports both 'scp' (space-separated string)
    and 'roles' (array) claim formats.

    Inherits get_middleware() and other required methods from TokenVerifier base class.

    Supports custom JWKS URI and issuer for:
    - Azure AD B2C
    - Sovereign clouds (Azure Government, Azure China, etc.)
    - Custom identity providers
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        jwks_uri: Optional[str] = None,
        issuer: Optional[str] = None,
        base_url: AnyHttpUrl | str | None = None,
        required_scopes: list[str] | None = None,
    ) -> None:
        """Initialize verifier with Azure AD tenant and client IDs.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Application (client) ID
            jwks_uri: Optional custom JWKS URI. If not provided, uses standard Azure AD endpoint.
                      Useful for B2C, sovereign clouds, or custom identity providers.
            issuer: Optional custom issuer. If not provided, uses standard Azure AD issuer.
                    Useful for B2C, sovereign clouds, or custom identity providers.
            base_url: Optional base URL for OAuth metadata endpoints
            required_scopes: Optional list of scopes required for all requests
        """
        # Initialize the parent TokenVerifier class
        super().__init__(base_url=base_url, required_scopes=required_scopes)

        self.tenant_id = tenant_id
        self.client_id = client_id

        # Use custom URLs if provided, otherwise default to standard Azure AD endpoints
        self.jwks_uri = (
            jwks_uri
            or f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        )
        self.issuer = issuer or f"https://login.microsoftonline.com/{tenant_id}/v2.0"

        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._cache_expiry: Optional[datetime] = None

        logger.info(f"EntraIdTokenVerifier initialized for tenant {tenant_id}")

    async def _get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Azure AD with 1-hour caching.

        Implements JWKS caching to reduce calls to Azure AD and prevent rate limiting.

        Returns:
            JWKS dictionary with 'keys' array

        Raises:
            RuntimeError: If JWKS fetch fails
        """
        now = datetime.now(timezone.utc)

        # Return cached if still valid
        if self._jwks_cache and self._cache_expiry and now < self._cache_expiry:
            logger.debug("Using cached JWKS")
            return self._jwks_cache

        # Fetch fresh JWKS
        logger.info(f"Fetching JWKS from {self.jwks_uri}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.jwks_uri, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"JWKS fetch failed with status {response.status}: {error_text}"
                        )

                    self._jwks_cache = await response.json()
                    # Cache for 1 hour
                    self._cache_expiry = now + timedelta(hours=1)
                    logger.info(f"JWKS cached until {self._cache_expiry.isoformat()}")
                    return self._jwks_cache
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch JWKS (network error): {e}")
            raise RuntimeError(f"JWKS fetch failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """Verify JWT token from Entra ID.

        Implements token verification with:
        - Signature verification using JWKS
        - Expiration check
        - Audience validation
        - Issuer validation
        - Scope extraction

        Args:
            token: JWT access token from Azure AD

        Returns:
            AccessToken object if valid, None if invalid

        Note:
            Returns None on any validation failure. Check logs for specific error.
        """
        try:
            # Get unverified header to find kid
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if not kid:
                logger.error("Token missing 'kid' in header")
                return None

            # Fetch JWKS and find signing key
            jwks = await self._get_jwks()
            signing_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    signing_key = RSAAlgorithm.from_jwk(key)
                    break

            if not signing_key:
                available_kids = [k.get("kid") for k in jwks.get("keys", [])]
                logger.error(
                    f"Signing key not found. Kid: {kid}, Available: {available_kids}"
                )
                return None

            # Verify token with all checks enabled
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            # Extract scopes (handle both scp and roles claims)
            raw_scopes = payload.get("scp", "").split() or payload.get("roles", [])
            scopes = [
                f"api://{self.client_id}/{scope}" for scope in raw_scopes if scope
            ]

            # Extract client ID (azp = authorized party, or fall back to sub)
            client_id = payload.get("azp") or payload.get("sub") or "unknown"

            # Extract expiration
            expires_at = payload.get("exp")

            logger.info(
                f"Token verified successfully. Subject: {payload.get('sub')}, Scopes: {scopes}"
            )

            return AccessToken(
                token=token,
                client_id=str(client_id),
                scopes=scopes,
                expires_at=int(expires_at) if expires_at else None,
                claims=payload,
            )

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidAudienceError:
            logger.error(f"Invalid audience. Expected: {self.client_id}")
            return None
        except jwt.InvalidIssuerError:
            logger.error(f"Invalid issuer. Expected: {self.issuer}")
            return None
        except jwt.DecodeError as e:
            logger.error(f"Token decode failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None
