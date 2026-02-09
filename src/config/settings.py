"""
Configuration settings for the Demo MCP Server.

This module provides a simplified configuration for the demo MCP server,
including only OAuth/OIDC settings required for authentication.
"""

from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerConfig(BaseSettings):
    """Demo MCP Server configuration.

    This configuration includes only the settings required for the demo:
    - OAuth/OIDC authentication settings
    - Server settings (host, port, debug)
    - Graph API scope settings

    Production implementations may add additional settings as needed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra environment variables
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=9000, description="Port to bind to")
    debug: bool = Field(default=False, description="Enable debug mode")
    server_name: str = Field(default="DemoMcpServer", description="Server name")

    # Authentication settings
    enable_auth: bool = Field(default=True, description="Enable authentication")
    tenant_id: Optional[str] = Field(default=None, description="Azure AD tenant ID")
    client_id: Optional[str] = Field(
        default=None, description="Application (client) ID"
    )
    client_secret: Optional[SecretStr] = Field(
        default=None,
        description="OAuth 2.0 client secret for On-Behalf-Of (OBO) token exchange",
    )
    jwks_uri: Optional[str] = Field(
        default=None, description="Custom JWKS URI (optional)"
    )
    issuer: Optional[str] = Field(default=None, description="Custom issuer (optional)")
    audience: Optional[str] = Field(
        default=None, description="Expected audience (defaults to client_id)"
    )
    graph_scope: str = Field(
        default="User.Read",
        description="Microsoft Graph API scope for OBO token requests",
    )
    federated_credential_oid: Optional[str] = Field(
        default=None,
        alias="FEDERATED_CREDENTIAL_OID",
        description="Client ID of the user-assigned managed identity for federated credential authentication (secretless OBO flow). Note: ManagedIdentityCredential requires the MI client_id, not the principal/object ID.",
    )

    # OAuth 2.1 / RFC 9728 Protected Resource Metadata
    resource_server_url: Optional[str] = Field(
        default=None, description="Canonical resource server URL"
    )
    authorization_server_url: Optional[str] = Field(
        default=None, description="Authorization server URL"
    )


# Global configuration instance - lazy initialized
_mcp_config: MCPServerConfig | None = None


def get_mcp_config(config: MCPServerConfig | None = None) -> MCPServerConfig:
    """Get the global MCP server configuration with optional injection.

    Args:
        config: Optional config instance to inject (useful for testing).
                If provided, sets this as the global config.

    Returns:
        The global MCPServerConfig instance.
    """
    global _mcp_config
    if config is not None:
        _mcp_config = config
    if _mcp_config is None:
        _mcp_config = MCPServerConfig()
    return _mcp_config


def reset_config() -> None:
    """Reset the config singleton for testing.

    This clears the cached config instance, allowing a fresh config
    to be created on the next call to get_mcp_config().
    """
    global _mcp_config
    _mcp_config = None


def get_resource_server_url() -> str:
    """Get the canonical resource server URL for OAuth 2.1 compliance.

    Per RFC 8707 and MCP spec, this should be the canonical URI of the MCP server.
    Falls back to constructing from host:port if not explicitly configured.

    Returns:
        The resource server URL string.
    """
    config = get_mcp_config()

    if config.resource_server_url:
        return config.resource_server_url

    # Construct canonical URL from host/port
    # Use localhost for 127.0.0.1, otherwise use the configured host
    host = "localhost" if config.host in ("127.0.0.1", "0.0.0.0") else config.host

    # Use http:// for local development, https:// for production
    # Local development is detected by localhost or 127.0.0.1
    is_local = host == "localhost" or config.host in ("127.0.0.1", "0.0.0.0")
    scheme = "http" if is_local else "https"

    # Standard ports don't need to be specified
    if (scheme == "https" and config.port == 443) or (
        scheme == "http" and config.port == 80
    ):
        return f"{scheme}://{host}"
    else:
        return f"{scheme}://{host}:{config.port}"


def get_authorization_server_url() -> Optional[str]:
    """Get the authorization server URL for OAuth 2.1 Protected Resource Metadata.

    Returns the configured authorization server URL or constructs it from tenant_id.

    Returns:
        The authorization server URL, or None if not configured.
    """
    config = get_mcp_config()

    if config.authorization_server_url:
        return config.authorization_server_url

    # Construct Azure AD authorization server URL from tenant_id
    if config.tenant_id:
        return f"https://login.microsoftonline.com/{config.tenant_id}/v2.0"

    return None
