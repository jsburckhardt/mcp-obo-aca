"""
Core module for MCP server components and factory patterns.
"""

from .factory import Domain, MCPToolBase, MCPToolFactory
from .exceptions import (
    MCPServerError,
    ConfigurationError,
    AuthSetupError,
    TokenVerificationError,
    ServiceRegistrationError,
    DependencyError,
)

__all__ = [
    "Domain",
    "MCPToolBase",
    "MCPToolFactory",
    "MCPServerError",
    "ConfigurationError",
    "AuthSetupError",
    "TokenVerificationError",
    "ServiceRegistrationError",
    "DependencyError",
]
