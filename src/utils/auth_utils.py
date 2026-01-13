"""
Authentication utilities for MCP server.

Provides helpers for extracting user information from JWT tokens.
"""

import logging
from typing import Optional

import jwt
from fastmcp import Context

logger = logging.getLogger(__name__)


def get_user_id_from_context(ctx: Context) -> str:
    """Extract user ID from the JWT token in the MCP context.

    The token has already been validated by the JWTVerifier at this point,
    so we only need to decode it (without verification) to extract claims.

    Args:
        ctx: FastMCP Context containing the request

    Returns:
        User identifier extracted from the token

    Raises:
        ValueError: If no token is found or no user identifier exists in the token
    """
    try:
        # Extract token from Authorization header
        request = ctx.request_context.request
        authorization_header = request.headers.get("Authorization")

        if not authorization_header:
            raise ValueError("No authorization token provided")

        # Parse Bearer token
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0] != "Bearer":
            raise ValueError("Invalid Authorization header format")

        token = parts[1]

        # Decode token without verification (already validated by JWTVerifier)
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Extract user identifier - try common JWT claims in order of preference
        user_id = (
            decoded.get("sub")  # Subject (standard JWT claim)
            or decoded.get("oid")  # Object ID (Azure AD)
            or decoded.get("user_id")  # Generic user_id
            or decoded.get("email")  # Email
            or decoded.get("preferred_username")  # Preferred username
        )

        if not user_id:
            logger.error("No user identifier found in token claims: %s", decoded.keys())
            raise ValueError("No user identifier found in token")

        logger.info("Extracted user ID: %s", user_id)
        return user_id

    except Exception as e:
        logger.error("Failed to extract user ID from token: %s", str(e))
        raise


def get_user_id_safe(ctx: Context, default: Optional[str] = None) -> Optional[str]:
    """Safely extract user ID from context, returning default if not available.

    Useful when auth might be disabled or for testing.

    Args:
        ctx: FastMCP Context containing the request
        default: Value to return if user ID cannot be extracted

    Returns:
        User ID if available, otherwise the default value
    """
    try:
        return get_user_id_from_context(ctx)
    except Exception as e:
        logger.warning("Could not extract user ID (auth may be disabled): %s", str(e))
        return default


def get_bearer_token(ctx: Context) -> str:
    """Extract bearer token from request context.

    This helper extracts the raw JWT token from the Authorization header
    without decoding or validating it. Useful for passing tokens to downstream
    services (e.g., OBO token exchange).

    Args:
        ctx: FastMCP Context with request

    Returns:
        JWT token string (without "Bearer " prefix)

    Raises:
        ValueError: If Authorization header is missing or malformed
    """
    request = ctx.request_context.request
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise ValueError("Authorization header missing")

    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise ValueError("Invalid Authorization header format")

    return parts[1]
