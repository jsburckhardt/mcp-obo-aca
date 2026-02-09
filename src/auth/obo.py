"""
On-Behalf-Of (OBO) token exchange for Microsoft Graph API.

This module implements the OAuth 2.0 On-Behalf-Of flow to exchange user access tokens
for Microsoft Graph API tokens. This allows the MCP server to call Graph API endpoints
(like /me) on behalf of the authenticated user.

Supports two authentication methods:
1. Client Secret (works locally and in Azure) - Traditional client secret authentication.
2. Federated Identity Credential (Azure-only, secretless) - Uses a managed identity token
   as a client assertion, eliminating the need for client secrets.
"""

import logging
from datetime import datetime, timezone

import jwt
from azure.identity.aio import ManagedIdentityCredential, OnBehalfOfCredential

from config.settings import get_mcp_config

logger = logging.getLogger(__name__)

# Audience for managed identity token exchange (federated credential)
# See: https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-config-app-trust-managed-identity
MI_TOKEN_EXCHANGE_AUDIENCE = "api://AzureADTokenExchange"


def _get_graph_scope() -> str:
    """Get the Microsoft Graph API scope from configuration."""
    config = get_mcp_config()
    return f"https://graph.microsoft.com/{config.graph_scope}"


def _validate_assertion_token_expiry(assertion_token: str) -> None:
    """Validate that the assertion token is not expiring soon.

    Args:
        assertion_token: The user's access token to validate

    Raises:
        RuntimeError: If the token is expiring within 5 minutes
    """
    try:
        # Decode token without verification (already validated by FastMCP middleware)
        payload = jwt.decode(assertion_token, options={"verify_signature": False})
        exp = payload.get("exp")

        if exp:
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            time_until_expiry = (exp_datetime - now).total_seconds()

            # 5-minute buffer (300 seconds) prevents race condition
            if time_until_expiry < 300:
                logger.warning(
                    f"Assertion token expiring in {time_until_expiry:.0f} seconds (< 5 minutes)"
                )
                raise RuntimeError(
                    "Assertion token expiring soon (< 5 minutes), please re-authenticate"
                )
    except jwt.DecodeError:
        # If we can't decode, let Azure AD handle it (will fail with invalid_grant)
        logger.warning("Could not decode assertion token for expiry check")


async def _get_graph_token_with_federated_credential(assertion_token: str) -> str:
    """Exchange user token for Graph token using federated identity credential.

    This method uses a managed identity token as a client assertion, eliminating
    the need for client secrets. The managed identity must be configured as a
    federated credential on the app registration.

    Args:
        assertion_token: User's access token (from Authorization header)

    Returns:
        Graph API access token (JWT string)

    Raises:
        RuntimeError: If OBO exchange fails
    """
    config = get_mcp_config()

    if not config.tenant_id or not config.client_id:
        raise RuntimeError(
            "TENANT_ID and CLIENT_ID must be configured for federated credential OBO flow"
        )

    graph_scope = _get_graph_scope()
    logger.info(
        f"Initiating OBO token exchange using federated credential for scope: {graph_scope}"
    )

    start_time = datetime.now(timezone.utc)

    try:
        # Create managed identity credential using the OID from config
        # This is the client ID of the user-assigned managed identity
        # ManagedIdentityCredential requires the MI client_id (not principal/object ID)
        mi_credential = ManagedIdentityCredential(
            client_id=config.federated_credential_oid
        )

        # Get the MI token first (async)
        # The MI token is requested with the token exchange audience
        mi_token = await mi_credential.get_token(
            f"{MI_TOKEN_EXCHANGE_AUDIENCE}/.default"
        )

        # Cache the MI token for the sync callback
        cached_mi_token = mi_token.token

        # Create a sync function that returns the cached MI token
        # OnBehalfOfCredential requires a sync callable
        def get_client_assertion() -> str:
            return cached_mi_token

        # Create OBO credential with the MI assertion function
        obo_credential = OnBehalfOfCredential(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_assertion_func=get_client_assertion,
            user_assertion=assertion_token,
        )

        # Get the Graph token
        graph_token = await obo_credential.get_token(graph_scope)

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        logger.info(
            f"OBO token exchange successful using federated credential (latency: {latency_ms:.0f}ms)"
        )

        return graph_token.token

    except Exception as e:
        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        logger.error(
            f"OBO exchange with federated credential failed (latency: {latency_ms:.0f}ms): {e}"
        )

        # Check for common consent issues
        error_str = str(e)
        if "AADSTS65001" in error_str or "has not consented" in error_str:
            raise RuntimeError(
                f"OBO exchange failed: User consent required. Please ensure Azure AD app registration "
                f"includes 'Microsoft Graph -> {config.graph_scope}' in API Permissions, then re-authenticate."
            ) from e

        raise RuntimeError(f"OBO failed with federated credential: {e}") from e


async def _get_graph_token_with_client_secret(assertion_token: str) -> str:
    """Exchange user token for Graph token using client secret (legacy).

    This is the method used when client secret is configured.

    Args:
        assertion_token: User's access token (from Authorization header)

    Returns:
        Graph API access token (JWT string)

    Raises:
        RuntimeError: If OBO exchange fails
    """
    import aiohttp

    config = get_mcp_config()

    if not config.client_secret:
        raise RuntimeError("CLIENT_SECRET not configured for OBO flow")

    graph_scope = _get_graph_scope()

    # Token endpoint for OBO exchange
    token_endpoint = (
        f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token"
    )

    data = {
        "client_id": config.client_id,
        "client_secret": config.client_secret.get_secret_value(),
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "requested_token_use": "on_behalf_of",
        "scope": graph_scope,
        "assertion": assertion_token,
    }

    logger.info(
        f"Initiating OBO token exchange using client secret for scope: {graph_scope}"
    )

    try:
        async with aiohttp.ClientSession() as session:
            start_time = datetime.now(timezone.utc)

            async with session.post(
                token_endpoint,
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                latency_ms = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000

                body = await resp.json()

                if resp.status == 200:
                    access_token = body.get("access_token")
                    if not access_token:
                        raise RuntimeError("OBO response missing access_token")

                    logger.info(
                        f"OBO token exchange successful using client secret (latency: {latency_ms:.0f}ms)"
                    )
                    return access_token

                # Error handling
                error = body.get("error", "unknown")
                error_desc = body.get("error_description", "No description")

                # Detect missing Graph API consent (AADSTS65001)
                if "AADSTS65001" in error_desc or "has not consented" in error_desc:
                    logger.error(
                        f"OBO exchange failed ({resp.status}): User has not consented to Graph API permissions. "
                        f"Ensure Azure AD app registration includes 'Microsoft Graph -> {config.graph_scope}' "
                        f"in API Permissions (Delegated). Error: {error} - {error_desc}"
                    )
                    raise RuntimeError(
                        f"OBO exchange failed: User consent required. Please ensure Azure AD app registration "
                        f"includes 'Microsoft Graph -> {config.graph_scope}' in API Permissions, then re-authenticate."
                    )

                # Detect rate limiting (429)
                if resp.status == 429:
                    logger.error(
                        f"OBO exchange rate limited (429, latency: {latency_ms:.0f}ms): {error_desc}"
                    )
                else:
                    logger.error(
                        f"OBO exchange failed ({resp.status}, latency: {latency_ms:.0f}ms): {error} - {error_desc}"
                    )

                raise RuntimeError(f"OBO failed: {error}")

    except aiohttp.ClientError as e:
        logger.error(f"Network error during OBO: {e}")
        raise RuntimeError(f"OBO network error: {e}") from e


async def get_graph_token_obo(assertion_token: str) -> str:
    """Exchange user access token for Graph API token using OBO flow.

    This function implements the OAuth 2.0 On-Behalf-Of (OBO) flow as specified in
    RFC 8693. It exchanges the user's assertion token for a Microsoft Graph API
    access token, allowing the server to act on behalf of the user.

    Authentication method priority:
    1. Client Secret (if CLIENT_SECRET is configured)
       - Works both locally and in Azure
       - Recommended for local development
    2. Federated Identity Credential (if FEDERATED_CREDENTIAL_OID is configured)
       - Azure-only (requires managed identity with IMDS endpoint)
       - Secretless production deployment

    Args:
        assertion_token: User's access token (from Authorization header)

    Returns:
        Graph API access token (JWT string)

    Raises:
        RuntimeError: If OBO exchange fails (missing credentials, token expired,
                     network error, or Azure AD error)
    """
    config = get_mcp_config()

    # Validate assertion token expiry (5-minute buffer)
    _validate_assertion_token_expiry(assertion_token)

    # Priority 1: Use client secret (works locally and in Azure)
    if config.client_secret:
        logger.debug("Using client secret for OBO flow")
        return await _get_graph_token_with_client_secret(assertion_token)

    # Priority 2: Use federated credential (Azure-only, secretless)
    if config.federated_credential_oid:
        logger.debug("Using federated identity credential for OBO flow (Azure-only)")
        return await _get_graph_token_with_federated_credential(assertion_token)

    # No credentials configured
    raise RuntimeError(
        "OBO flow not configured: Set CLIENT_SECRET (works locally and in Azure) "
        "or FEDERATED_CREDENTIAL_OID (Azure-only, secretless) in environment"
    )
