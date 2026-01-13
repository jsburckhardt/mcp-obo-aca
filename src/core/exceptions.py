"""
Custom exception hierarchy for the MCP server.

Provides explicit failure modes instead of silent failures and generic exceptions.
This improves debuggability and allows callers to handle specific error types.
"""


class MCPServerError(Exception):
    """
    Base exception for all MCP server errors.

    All custom exceptions in the MCP server should inherit from this class
    to allow catching all MCP-related errors with a single except clause.
    """

    pass


class ConfigurationError(MCPServerError):
    """
    Configuration validation failed.

    Raised when required configuration values are missing or invalid.
    Examples:
    - Missing TENANT_ID when auth is enabled
    - Missing CLIENT_SECRET when auth is enabled
    - Invalid URL format for endpoints
    """

    pass


class AuthSetupError(MCPServerError):
    """
    Authentication setup failed.

    Raised when the authentication provider cannot be initialized.
    Examples:
    - Failed to create EntraIdTokenVerifier
    - Failed to create RemoteAuthProvider
    - Invalid auth configuration combination
    """

    pass


class TokenVerificationError(MCPServerError):
    """
    Token verification failed.

    Raised when a token cannot be verified.
    Note: For security reasons, specific details may not be exposed.
    """

    pass


class ServiceRegistrationError(MCPServerError):
    """
    Service registration failed.

    Raised when a service cannot be registered with the factory.
    Examples:
    - Duplicate service domain
    - Invalid service implementation
    """

    pass


class DependencyError(MCPServerError):
    """
    Required dependency is not available.

    Raised when a required package or module is not installed.
    Examples:
    - FastMCP not installed
    - Azure SDK not available
    """

    pass
