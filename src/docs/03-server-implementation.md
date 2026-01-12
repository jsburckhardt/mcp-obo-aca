# Server Implementation

This guide walks through the key components of the Demo MCP Server.

## Project Structure

```
demo_mcp_server/
├── auth/
│   ├── __init__.py
│   ├── verifier.py      # JWT token verification
│   └── obo.py           # On-Behalf-Of token exchange
├── config/
│   ├── __init__.py
│   └── settings.py      # Configuration management
├── core/
│   ├── __init__.py
│   ├── factory.py       # Tool factory pattern
│   └── exceptions.py    # Custom exceptions
├── services/
│   ├── __init__.py
│   └── general_service.py  # Demo tools
├── utils/
│   ├── __init__.py
│   ├── auth_utils.py    # Token extraction helpers
│   ├── date_utils.py    # Timestamp utilities
│   └── formatters.py    # Response formatters
├── tests/
│   └── ...
├── docs/
│   └── ...
├── server.py            # Main entry point
├── pyproject.toml       # Package configuration
└── .env.example         # Environment template
```

## Key Components

### 1. Token Verifier (auth/verifier.py)

The `EntraIdTokenVerifier` validates JWT tokens from Azure AD:

```python
class EntraIdTokenVerifier(TokenVerifier):
    def __init__(self, tenant_id: str, client_id: str, ...):
        # Initialize with Azure AD configuration
        self.jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        
    async def _get_jwks(self) -> Dict[str, Any]:
        # Fetch and cache JWKS (1-hour TTL)
        
    async def verify_token(self, token: str) -> Optional[AccessToken]:
        # Verify signature, expiration, audience, issuer
        # Extract scopes from 'scp' or 'roles' claims
```

Key features:
- JWKS caching (1-hour TTL) to reduce Azure AD calls
- Signature verification using RS256
- Scope extraction from both `scp` and `roles` claims

### 2. On-Behalf-Of Flow (auth/obo.py)

The OBO flow exchanges user tokens for Graph API tokens:

```python
async def get_graph_token_obo(assertion_token: str) -> str:
    # Validate token isn't expiring soon (5-minute buffer)
    _validate_assertion_token_expiry(assertion_token)
    
    # Priority 1: Client Secret (works locally and in Azure)
    if config.client_secret:
        return await _get_graph_token_with_client_secret(assertion_token)
    
    # Priority 2: Federated Credential (Azure-only, secretless)
    if config.federated_credential_oid:
        return await _get_graph_token_with_federated_credential(assertion_token)
```

The OBO flow makes a POST request to Azure AD's token endpoint:

```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token

grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
requested_token_use=on_behalf_of
scope=https://graph.microsoft.com/User.Read
assertion={user-access-token}
client_id={client-id}
client_secret={client-secret}
```

### 3. Tool Factory (core/factory.py)

The factory pattern organizes tools by domain:

```python
class MCPToolFactory:
    def register_service(self, service: MCPToolBase):
        self._services[service.domain] = service
    
    def create_mcp_server(self, name: str, auth=None) -> FastMCP:
        mcp_server = FastMCP(name, auth=auth)
        for service in self._services.values():
            service.register_tools(mcp_server)
        return mcp_server
```

### 4. General Service (services/general_service.py)

The demo service with three tools:

```python
class GeneralService(MCPToolBase):
    def register_tools(self, mcp):
        @mcp.tool(tags={self.domain.value})
        def greet_test(name: str) -> str:
            # Simple greeting, no auth needed
        
        @mcp.tool(tags={self.domain.value})
        async def get_mcp_server_status() -> str:
            # Server status, no auth needed
        
        @mcp.tool(tags={self.domain.value})
        async def whoami(ctx: Context) -> str:
            # Get user's profile via OBO flow
            user_token = get_bearer_token(ctx)
            graph_token = await get_graph_token_obo(user_token)
            # Call Graph API /me endpoint
```

### 5. OAuth Metadata Endpoints (server.py)

RFC 9728 compliance endpoints:

```python
@mcp_server.custom_route("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata(request):
    return {
        "resource": "http://localhost:9000",
        "bearer_methods_supported": ["header"],
        "authorization_servers": ["https://login.microsoftonline.com/{tenant}/v2.0"],
        "scopes_supported": ["api://{client-id}/access_as_user", ...]
    }
```

## Configuration

Settings are loaded from environment variables with Pydantic:

```python
class MCPServerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    # Server
    host: str = "0.0.0.0"
    port: int = 9000
    
    # Authentication
    enable_auth: bool = True
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[SecretStr] = None
    # ...
```

## Next Steps

Continue to [04-running-and-testing.md](04-running-and-testing.md) to run and test the server.
