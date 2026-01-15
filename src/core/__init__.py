"""
Core module for MCP server components and factory patterns.
"""

from .exceptions import (
    AuthSetupError,
    ConfigurationError,
    DependencyError,
    MCPServerError,
    ServiceRegistrationError,
    TokenVerificationError,
)
from .factory import Domain, MCPToolBase, MCPToolFactory

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
