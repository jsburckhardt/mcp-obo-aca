"""
Configuration module for the Demo MCP Server.
"""

from .settings import (
    MCPServerConfig,
    get_mcp_config,
    reset_config,
    get_resource_server_url,
    get_authorization_server_url,
)

__all__ = [
    "MCPServerConfig",
    "get_mcp_config",
    "reset_config",
    "get_resource_server_url",
    "get_authorization_server_url",
]
