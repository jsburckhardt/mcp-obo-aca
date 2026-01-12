"""
General purpose MCP tools service.

This service provides three demo tools:
- greet_test: Simple greeting (no auth required)
- get_mcp_server_status: Server status (no auth required)
- whoami: User info from Graph API (demonstrates OBO flow)
"""

import aiohttp
from fastmcp import Context

from auth.obo import get_graph_token_obo
from core.factory import Domain, MCPToolBase
from utils.auth_utils import get_bearer_token, get_user_id_from_context
from utils.date_utils import get_current_timestamp
from utils.formatters import format_error_response, format_success_response


class GeneralService(MCPToolBase):
    """General purpose tools for common operations.

    Provides demo tools including one that demonstrates the OBO flow
    for calling Microsoft Graph API on behalf of the authenticated user.
    """

    def __init__(self) -> None:
        """Initialize the general service."""
        super().__init__(Domain.GENERAL)

    def register_tools(self, mcp) -> None:
        """Register general tools with the MCP server.

        Args:
            mcp: The FastMCP server instance to register tools with.
        """

        @mcp.tool(tags={self.domain.value})
        def greet_test(name: str) -> str:
            """Test for MCP - Greets the user with the provided name.

            This is a simple tool that doesn't require authentication.

            Args:
                name: The name to greet.

            Returns:
                A formatted greeting response.
            """
            try:
                details = {
                    "name": name,
                    "greeting": f"Hello from Demo MCP Server, {name}!",
                    "timestamp": get_current_timestamp(),
                }
                summary = f"Greeted user {name}."

                return format_success_response(
                    action="Greeting", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="greeting user"
                )

        @mcp.tool(tags={self.domain.value})
        async def get_mcp_server_status() -> str:
            """Get the current server status and information.

            This tool returns basic server information and doesn't
            require authentication.

            Returns:
                Server status information.
            """
            try:
                details = {
                    "server_name": "Demo MCP Server",
                    "status": "Running",
                    "timestamp": get_current_timestamp(),
                    "version": "0.1.0",
                }
                summary = "Retrieved server status information."

                return format_success_response(
                    action="Server Status", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e), context="getting server status"
                )

        @mcp.tool(tags={self.domain.value})
        async def whoami(ctx: Context) -> str:
            """Get the current authenticated user's information from Microsoft Graph API.

            This tool demonstrates the On-Behalf-Of (OBO) flow:
            1. Extracts the user's access token from the request
            2. Exchanges it for a Graph API token using OBO
            3. Calls the Graph API /me endpoint
            4. Returns the user's profile information

            Requires authentication to be enabled.

            Args:
                ctx: The FastMCP context containing the request.

            Returns:
                User profile information from Graph API.
            """
            try:
                # Extract user token from context
                user_token = get_bearer_token(ctx)

                # Exchange user token for Graph API token via OBO
                graph_token = await get_graph_token_obo(user_token)

                # Call Microsoft Graph API /me endpoint
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {graph_token}"}
                    async with session.get(
                        "https://graph.microsoft.com/v1.0/me", headers=headers
                    ) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            raise RuntimeError(
                                f"Graph API failed: {resp.status} - {error_text}"
                            )
                        profile = await resp.json()

                # Extract user ID from JWT claims for consistency
                user_id = get_user_id_from_context(ctx)

                details = {
                    "user_id": user_id,
                    "display_name": profile.get("displayName"),
                    "email": profile.get("mail") or profile.get("userPrincipalName"),
                    "given_name": profile.get("givenName"),
                    "surname": profile.get("surname"),
                    "job_title": profile.get("jobTitle"),
                    "office_location": profile.get("officeLocation"),
                    "timestamp": get_current_timestamp(),
                }
                summary = f"Retrieved user profile from Graph API for: {user_id}"

                return format_success_response(
                    action="Get User Info", details=details, summary=summary
                )
            except Exception as e:
                return format_error_response(
                    error_message=str(e),
                    context="getting user information from Graph API",
                )

    @property
    def tool_count(self) -> int:
        """Return the number of tools provided by this service.

        Returns:
            The number of tools (3: greet_test, get_server_status, whoami).
        """
        return 3
