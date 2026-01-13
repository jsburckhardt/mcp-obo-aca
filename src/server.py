"""
Demo MCP Server - FastMCP server with OAuth 2.1 authentication and OBO flow.

This module implements a minimal MCP server demonstrating:
- OAuth 2.1 / OIDC authentication with Azure AD (Entra ID)
- On-Behalf-Of (OBO) token exchange for Microsoft Graph API
- RFC 9728 Protected Resource Metadata endpoints
- Health check endpoint for container orchestration

Usage:
    # Run with authentication disabled (for testing)
    python mcp_server.py --no-auth

    # Run with authentication enabled
    python mcp_server.py

    # Run with debug logging
    python mcp_server.py --debug
"""

import argparse
import logging
from typing import Any, Optional, cast

from auth.verifier import EntraIdTokenVerifier
from config.settings import (
    MCPServerConfig,
    get_mcp_config,
    get_authorization_server_url,
    get_resource_server_url,
)
from core.exceptions import ConfigurationError, DependencyError, AuthSetupError
from core.factory import MCPToolBase, MCPToolFactory
from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.server import Transport
from pydantic import AnyHttpUrl
from services.general_service import GeneralService
from starlette.requests import Request
from starlette.responses import JSONResponse

# Setup logging - will be reconfigured based on config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Service Registration
# =============================================================================


def get_default_services() -> list[MCPToolBase]:
    """Return default service instances.

    For the demo, only GeneralService is included.

    Returns:
        List containing the GeneralService instance.
    """
    return [
        GeneralService(),
    ]


def create_factory(services: Optional[list[MCPToolBase]] = None) -> MCPToolFactory:
    """Create factory with services.

    Args:
        services: Optional list of services to register. If None, uses defaults.

    Returns:
        Configured MCPToolFactory instance.
    """
    factory = MCPToolFactory()
    for service in services or get_default_services():
        factory.register_service(service)
    return factory


# =============================================================================
# OAuth Metadata Builders
# =============================================================================


def build_api_scopes(client_id: Optional[str]) -> list[str]:
    """Build the list of API scopes for OAuth metadata.

    Args:
        client_id: The application (client) ID.

    Returns:
        List of API scope URIs.
    """
    if not client_id:
        return []
    return [
        f"api://{client_id}/access_as_user",
        f"api://{client_id}/user_impersonate",
        f"api://{client_id}/MCP.Resources",
        f"api://{client_id}/MCP.Tools",
        f"api://{client_id}/MCP.Prompts",
    ]


def build_protected_resource_metadata(config: MCPServerConfig) -> dict[str, Any]:
    """Build OAuth 2.0 Protected Resource Metadata (RFC 9728).

    This metadata tells clients about this MCP server as a protected resource,
    including where to find the authorization server.

    Args:
        config: The MCP server configuration.

    Returns:
        Dictionary containing protected resource metadata.
    """
    resource_url = get_resource_server_url()
    auth_server_url = get_authorization_server_url()
    scopes = build_api_scopes(config.client_id)

    metadata: dict[str, Any] = {
        "resource": resource_url,
        "bearer_methods_supported": ["header"],
    }

    if auth_server_url:
        metadata["authorization_servers"] = [auth_server_url]

    if scopes:
        metadata["scopes_supported"] = scopes

    return metadata


def build_authorization_server_metadata(config: MCPServerConfig) -> dict[str, Any]:
    """Build OAuth 2.0 Authorization Server Metadata (RFC 8414).

    Points to Azure AD's endpoints for token acquisition.

    Args:
        config: The MCP server configuration.

    Returns:
        Dictionary containing authorization server metadata.
    """
    auth_server_url = get_authorization_server_url()
    scopes = build_api_scopes(config.client_id)

    return {
        "issuer": auth_server_url,
        "authorization_endpoint": f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/authorize",
        "token_endpoint": f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token",
        "jwks_uri": f"https://login.microsoftonline.com/{config.tenant_id}/discovery/v2.0/keys",
        "response_types_supported": ["code", "token", "id_token"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
        ],
        "scopes_supported": scopes,
    }


def build_openid_configuration(config: MCPServerConfig) -> dict[str, Any]:
    """Build OpenID Connect Discovery metadata.

    Provides OIDC endpoints for VS Code compatibility.

    Args:
        config: The MCP server configuration.

    Returns:
        Dictionary containing OpenID configuration.
    """
    auth_server_url = get_authorization_server_url()
    scopes = build_api_scopes(config.client_id)

    return {
        "issuer": auth_server_url,
        "authorization_endpoint": f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/authorize",
        "token_endpoint": f"https://login.microsoftonline.com/{config.tenant_id}/oauth2/v2.0/token",
        "userinfo_endpoint": "https://graph.microsoft.com/oidc/userinfo",
        "jwks_uri": f"https://login.microsoftonline.com/{config.tenant_id}/discovery/v2.0/keys",
        "response_types_supported": ["code", "id_token", "token"],
        "subject_types_supported": ["pairwise"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"] + scopes,
    }


# =============================================================================
# Endpoint Registration
# =============================================================================


def register_health_endpoint(mcp_server: FastMCP) -> None:
    """Register health check endpoint for container orchestration.

    This endpoint is used by Docker healthchecks and Azure Container Apps
    health probes to verify the application is running and responsive.

    Args:
        mcp_server: The FastMCP server instance.
    """

    @mcp_server.custom_route("/health", methods=["GET"], name="health_check")
    async def health_check(request: Request) -> JSONResponse:
        """Simple health check endpoint for container orchestration."""
        return JSONResponse(
            content={"status": "healthy", "service": "demo-mcp-server"},
            headers={"Content-Type": "application/json"},
        )

    logger.info("Health check endpoint registered at /health")


def register_oauth_endpoints(mcp_server: FastMCP, config: MCPServerConfig) -> None:
    """Register OAuth 2.1 / RFC 9728 compliance endpoints.

    Implements:
    - Protected Resource Metadata endpoint (RFC 9728)
    - Authorization Server Metadata endpoint (for VS Code compatibility)
    - OpenID Configuration endpoint (for VS Code compatibility)

    Args:
        mcp_server: The FastMCP server instance.
        config: The MCP server configuration.
    """

    @mcp_server.custom_route(
        "/.well-known/oauth-protected-resource",
        methods=["GET"],
        name="oauth_protected_resource_metadata",
    )
    async def oauth_protected_resource_metadata(request: Request) -> JSONResponse:
        """OAuth 2.0 Protected Resource Metadata endpoint (RFC 9728)."""
        metadata = build_protected_resource_metadata(config)
        logger.info("Served Protected Resource Metadata", extra={"metadata": metadata})
        return JSONResponse(
            content=metadata,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=3600",
            },
        )

    @mcp_server.custom_route(
        "/.well-known/oauth-protected-resource/mcp",
        methods=["GET"],
        name="oauth_protected_resource_metadata_mcp",
    )
    async def oauth_protected_resource_metadata_mcp(request: Request) -> JSONResponse:
        """Path-specific Protected Resource Metadata for /mcp endpoint."""
        metadata = build_protected_resource_metadata(config)
        return JSONResponse(
            content=metadata,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=3600",
            },
        )

    @mcp_server.custom_route(
        "/.well-known/oauth-authorization-server",
        methods=["GET"],
        name="oauth_authorization_server_metadata",
    )
    async def oauth_authorization_server_metadata(request: Request) -> JSONResponse:
        """OAuth 2.0 Authorization Server Metadata endpoint (RFC 8414)."""
        auth_server_url = get_authorization_server_url()
        if not auth_server_url:
            return JSONResponse(
                content={"error": "authorization_server_not_configured"},
                status_code=404,
            )
        metadata = build_authorization_server_metadata(config)
        logger.info("Served Authorization Server Metadata pointing to Azure AD")
        return JSONResponse(
            content=metadata,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=3600",
            },
        )

    @mcp_server.custom_route(
        "/.well-known/openid-configuration",
        methods=["GET"],
        name="openid_configuration",
    )
    async def openid_configuration(request: Request) -> JSONResponse:
        """OpenID Connect Discovery endpoint."""
        auth_server_url = get_authorization_server_url()
        if not auth_server_url:
            return JSONResponse(
                content={"error": "authorization_server_not_configured"},
                status_code=404,
            )
        metadata = build_openid_configuration(config)
        logger.info("Served OpenID Configuration pointing to Azure AD")
        return JSONResponse(
            content=metadata,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=3600",
            },
        )

    resource_url = get_resource_server_url()
    logger.info(
        f"OAuth 2.1 Protected Resource Metadata endpoint registered: {resource_url}/.well-known/oauth-protected-resource"
    )
    logger.info(
        f"OAuth Authorization Server Metadata endpoint registered: {resource_url}/.well-known/oauth-authorization-server"
    )
    logger.info(
        f"OpenID Configuration endpoint registered: {resource_url}/.well-known/openid-configuration"
    )


# =============================================================================
# Server Initialization
# =============================================================================


def validate_auth_config(config: MCPServerConfig) -> None:
    """Validate authentication configuration.

    Args:
        config: The MCP server configuration.

    Raises:
        ConfigurationError: If auth is enabled but required values are missing.
    """
    if not config.enable_auth:
        return

    missing = []
    if not config.tenant_id:
        missing.append("TENANT_ID")
    if not config.client_id:
        missing.append("CLIENT_ID")
    if not config.jwks_uri:
        missing.append("JWKS_URI")
    if not config.issuer:
        missing.append("ISSUER")
    if not config.audience:
        missing.append("AUDIENCE")

    # Check for credential: either CLIENT_SECRET or FEDERATED_CREDENTIAL_OID
    has_client_secret = config.client_secret and config.client_secret.get_secret_value()
    has_federated_credential = bool(config.federated_credential_oid)
    if not has_client_secret and not has_federated_credential:
        missing.append("CLIENT_SECRET or FEDERATED_CREDENTIAL_OID")

    if missing:
        logger.error(
            "ENABLE_AUTH=true but required config missing",
            extra={"missing_config": missing},
        )
        raise ConfigurationError(
            f"Authentication enabled but missing required configuration: {', '.join(missing)}"
        )

    logger.info(
        "Auth config loaded",
        extra={
            "tenant_id": config.tenant_id,
            "client_id": config.client_id,
            "graph_scope": config.graph_scope,
        },
    )


def create_auth_provider(config: MCPServerConfig) -> Optional[RemoteAuthProvider]:
    """Create authentication provider if enabled.

    Args:
        config: The MCP server configuration.

    Returns:
        RemoteAuthProvider if auth is enabled, None otherwise.

    Raises:
        AuthSetupError: If auth provider creation fails.
    """
    if not config.enable_auth:
        return None

    try:
        # Create the token verifier for Azure AD
        token_verifier = EntraIdTokenVerifier(
            tenant_id=config.tenant_id,  # type: ignore
            client_id=config.client_id,  # type: ignore
            jwks_uri=config.jwks_uri,
            issuer=config.issuer,
        )
        logger.info(
            "EntraIdTokenVerifier initialized", extra={"tenant_id": config.tenant_id}
        )

        # Get URLs for auth provider
        auth_server_url = get_authorization_server_url()
        resource_url = get_resource_server_url()

        # Build the scopes that clients should request
        scopes = build_api_scopes(config.client_id)

        auth = RemoteAuthProvider(
            token_verifier=token_verifier,
            authorization_servers=[AnyHttpUrl(auth_server_url)]
            if auth_server_url
            else [],
            base_url=resource_url,
            resource_name="Demo MCP Server",
        )

        # Set required_scopes on the verifier for scope enforcement
        token_verifier.required_scopes = scopes

        logger.info(
            "RemoteAuthProvider configured", extra={"auth_server": auth_server_url}
        )

        return auth

    except Exception as e:
        logger.error("Failed to create auth provider", extra={"error": str(e)})
        raise AuthSetupError(f"Failed to create authentication provider: {e}") from e


def register_endpoints(server: FastMCP, config: MCPServerConfig) -> None:
    """Register all endpoints on the server.

    Args:
        server: The FastMCP server instance.
        config: The MCP server configuration.
    """
    register_health_endpoint(server)
    if config.enable_auth:
        register_oauth_endpoints(server, config)


def create_fastmcp_server(
    config: Optional[MCPServerConfig] = None,
    services: Optional[list[MCPToolBase]] = None,
) -> FastMCP:
    """Create and configure FastMCP server.

    Args:
        config: Optional config instance. If None, uses global config.
        services: Optional list of services. If None, uses defaults.

    Returns:
        Configured FastMCP server instance.

    Raises:
        ConfigurationError: If configuration validation fails.
        AuthSetupError: If authentication setup fails.
        DependencyError: If required dependencies are not available.
    """
    try:
        config = config or get_mcp_config()

        # Configure logging based on debug setting
        log_level = logging.DEBUG if config.debug else logging.INFO
        logging.getLogger().setLevel(log_level)

        # Validate configuration
        validate_auth_config(config)

        # Create authentication provider
        auth = create_auth_provider(config)

        # Create factory with services
        factory = create_factory(services)

        # Create MCP server
        mcp_server = factory.create_mcp_server(
            name=config.server_name,
            auth=auth,
        )

        # Register endpoints
        register_endpoints(mcp_server, config)

        logger.info("FastMCP server created successfully")
        return mcp_server

    except ImportError as e:
        logger.error("FastMCP not available", extra={"error": str(e)})
        raise DependencyError(
            "FastMCP not installed. Install with: pip install fastmcp"
        ) from e


# =============================================================================
# Global Server Instance (Lazy Initialization via __getattr__)
# =============================================================================

# Private storage for lazy-initialized instances
_mcp: Optional[FastMCP] = None
_factory: Optional[MCPToolFactory] = None
_initialized: bool = False


def _lazy_init() -> None:
    """Initialize mcp and factory on first access.

    This is called automatically when accessing module.mcp or module.factory
    via __getattr__. It uses the default configuration from environment.
    """
    global _mcp, _factory, _initialized
    if _initialized:
        return
    _initialized = True
    try:
        _mcp = create_fastmcp_server()
        _factory = create_factory()
    except Exception as e:
        logger.warning(f"Deferred server initialization due to: {e}")


def __getattr__(name: str) -> Any:
    """Lazy initialization of module-level mcp and factory.

    This enables `fastmcp run mcp_server.py` to work without eager initialization.
    When fastmcp imports the module and accesses `mcp`, this triggers lazy init
    with the default configuration.

    For CLI usage (`python mcp_server.py --no-auth`), the main() function
    sets _mcp directly before any access, so __getattr__ is not called.
    """
    if name == "mcp":
        _lazy_init()
        return _mcp
    if name == "factory":
        _lazy_init()
        return _factory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_mcp_instance() -> Optional[FastMCP]:
    """Get or create the MCP server instance.

    Returns:
        The FastMCP server instance, or None if initialization failed.
    """
    _lazy_init()
    return _mcp


def get_factory_instance() -> MCPToolFactory:
    """Get or create the factory instance.

    Returns:
        The MCPToolFactory instance.

    Raises:
        RuntimeError: If factory was not initialized.
    """
    _lazy_init()
    if _factory is None:
        raise RuntimeError("Factory not initialized")
    return _factory


# =============================================================================
# Server Runtime
# =============================================================================


def log_server_info(
    server_instance: Optional[FastMCP], config: MCPServerConfig
) -> None:
    """Log server initialization info.

    Args:
        server_instance: The FastMCP server instance.
        config: The MCP server configuration.
    """
    if not server_instance:
        logger.error("FastMCP server not available")
        return

    factory = create_factory()
    summary = factory.get_tool_summary()

    logger.info(
        "Server initialized",
        extra={
            "server_name": config.server_name,
            "total_services": summary["total_services"],
            "total_tools": summary["total_tools"],
            "auth_enabled": config.enable_auth,
        },
    )

    for domain, info in summary["services"].items():
        logger.info(
            f"Service registered: {domain}",
            extra={"tool_count": info["tool_count"], "class_name": info["class_name"]},
        )


def run_server(
    server_instance: Optional[FastMCP],
    transport: Transport = "streamable-http",
    host: str = "127.0.0.1",
    port: int = 9000,
    **kwargs: Any,
) -> None:
    """Run the FastMCP server with streamable-http transport.

    Args:
        server_instance: The FastMCP server to run.
        transport: Transport protocol (default: streamable-http).
        host: Host to bind to.
        port: Port to bind to.
        **kwargs: Additional arguments passed to server.run().
    """
    if not server_instance:
        logger.error("Cannot start FastMCP server - not available")
        return

    config = get_mcp_config()
    log_server_info(server_instance, config)

    logger.info(
        "Starting FastMCP server",
        extra={"transport": transport, "host": host, "port": port},
    )
    server_instance.run(transport=transport, host=host, port=port, **kwargs)


# =============================================================================
# CLI Entry Point
# =============================================================================


def main() -> None:
    """Main entry point with argument parsing."""
    global _mcp, _factory, _initialized

    parser = argparse.ArgumentParser(description="Demo MCP Server")
    parser.add_argument(
        "--transport",
        "-t",
        choices=["streamable-http"],
        default="streamable-http",
        help="Transport protocol (default: streamable-http)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=9000,
        help="Port to bind to (default: 9000)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--no-auth", action="store_true", help="Disable authentication")

    args = parser.parse_args()

    # Build config overrides from CLI
    overrides: dict[str, Any] = {}
    if args.debug:
        overrides["debug"] = True
    if args.no_auth:
        overrides["enable_auth"] = False

    # Create config with CLI overrides using model_copy
    base_config = get_mcp_config()
    if overrides:
        config = base_config.model_copy(update=overrides)
    else:
        config = base_config

    # Create server with explicit config
    try:
        server = create_fastmcp_server(config=config)
    except (ConfigurationError, AuthSetupError, DependencyError) as e:
        print(f"Failed to create server: {e}")
        return

    # Mark as initialized to prevent lazy init from overwriting
    _mcp = server
    _factory = create_factory()
    _initialized = True

    # Print startup info
    print("Starting Demo MCP Server")
    print(f"Transport: {args.transport.upper()}")
    print(f"Debug: {config.debug}")
    print(f"Auth: {'Enabled' if config.enable_auth else 'Disabled'}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print("-" * 50)

    # Run the server
    run_server(
        server,
        transport=cast(Transport, args.transport),
        host=args.host,
        port=args.port,
        log_level="debug" if config.debug else "info",
    )


if __name__ == "__main__":
    main()
