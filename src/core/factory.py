"""
Core MCP server components and factory patterns.

This module provides a simplified factory pattern for creating MCP tools
with a single GENERAL domain for demonstration purposes.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from fastmcp import FastMCP


class Domain(Enum):
    """Service domains for organizing MCP tools.

    For this demo, only GENERAL domain is provided.
    Production implementations may add additional domains.
    """

    GENERAL = "general"


class MCPToolBase(ABC):
    """Base class for MCP tool services.

    All tool services must inherit from this class and implement
    the register_tools method to register their tools with the MCP server.
    """

    def __init__(self, domain: Domain) -> None:
        """Initialize the tool service with a domain.

        Args:
            domain: The domain this service belongs to.
        """
        self.domain = domain
        self.tools: list[Any] = []

    @abstractmethod
    def register_tools(self, mcp: FastMCP) -> None:
        """Register tools with the MCP server.

        Args:
            mcp: The FastMCP server instance to register tools with.
        """
        pass

    @property
    @abstractmethod
    def tool_count(self) -> int:
        """Return the number of tools provided by this service."""
        pass


class MCPToolFactory:
    """Factory for creating and managing MCP tools.

    This factory manages the registration of tool services and creates
    configured MCP server instances.
    """

    def __init__(self) -> None:
        """Initialize the factory with empty service registry."""
        self._services: Dict[Domain, MCPToolBase] = {}
        self._mcp_server: Optional[FastMCP] = None

    def register_service(self, service: MCPToolBase) -> None:
        """Register a tool service with the factory.

        Args:
            service: The tool service to register.
        """
        self._services[service.domain] = service

    def create_mcp_server(
        self,
        name: str = "Demo MCP Server",
        auth: Optional[Any] = None,
        middleware: Optional[Any] = None,
    ) -> FastMCP:
        """Create and configure the MCP server with all registered services.

        Args:
            name: The name of the MCP server.
            auth: Optional authentication provider.
            middleware: Optional middleware to apply.

        Returns:
            Configured FastMCP server instance.
        """
        # Create server with optional middleware
        if middleware:
            self._mcp_server = FastMCP(name, auth=auth, middleware=middleware)
        else:
            self._mcp_server = FastMCP(name, auth=auth)

        # Register all tools from all services
        for service in self._services.values():
            service.register_tools(self._mcp_server)

        return self._mcp_server

    def get_services_by_domain(self, domain: Domain) -> Optional[MCPToolBase]:
        """Get service by domain.

        Args:
            domain: The domain to look up.

        Returns:
            The service for the domain, or None if not found.
        """
        return self._services.get(domain)

    def get_all_services(self) -> Dict[Domain, MCPToolBase]:
        """Get all registered services.

        Returns:
            A copy of the services dictionary.
        """
        return self._services.copy()

    def get_tool_summary(self) -> Dict[str, Any]:
        """Get a summary of all tools and services.

        Returns:
            Dictionary containing service and tool counts.
        """
        summary: Dict[str, Any] = {
            "total_services": len(self._services),
            "total_tools": sum(
                service.tool_count for service in self._services.values()
            ),
            "services": {},
        }

        for domain, service in self._services.items():
            summary["services"][domain.value] = {
                "tool_count": service.tool_count,
                "class_name": service.__class__.__name__,
            }

        return summary
