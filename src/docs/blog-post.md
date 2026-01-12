---
post_title: 'Building a Secure MCP Server with OAuth 2.1 and Azure AD: Lessons from the Field'
author1: petergregg
# author2: second-author-alias
# author3: third-author-alias
post_slug: secure-mcp-server-oauth21-azure-ad
post_date: 2026-01-11 10:00:00
categories: Security, AI, Cloud Architecture
tags: MCP, OAuth, Azure AD, Authentication, FastMCP, On-Behalf-Of
featured_image: assets/mcp-oauth-architecture.png
summary: "How we built a production-ready MCP server with OAuth 2.1 authentication and On-Behalf-Of flow for Microsoft Graph, navigating a rapidly evolving specification."
---

## Introduction: The Problem

When a customer approached us with a seemingly straightforward request—"We need an MCP server that's secure and fast"—we didn't anticipate the journey ahead. The Model Context Protocol (MCP) had been gaining traction as a way to expose tools and resources to AI agents, but one critical piece was still evolving: **authentication**.

The customer's requirements were clear:
- **Enterprise-grade security**: Azure AD (Entra ID) integration with proper token validation
- **Low latency**: No per-request round trips to identity providers
- **Downstream API access**: The ability to call Microsoft Graph on behalf of authenticated users
- **Standards compliance**: Following OAuth 2.1 best practices

The challenge? The MCP specification had been changing rapidly to address security concerns. Earlier versions had limited guidance on authentication, and the community was still figuring out best practices. We needed to build something production-ready while the ground was shifting beneath our feet.

## The Journey: Our Approach and Solution

We decided to follow the [MCP Authorization Specification (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), which finally provided clear guidance on OAuth 2.1 integration. Our goal was to create a reusable implementation that could serve as a reference for others facing the same challenges.

### Section 1: Understanding the MCP Auth Landscape

The MCP specification defines two key roles:

1. **Authorization Server**: Issues tokens (Azure AD in our case)
2. **Resource Server (MCP Server)**: Validates tokens and serves protected resources

The spec mandates support for [RFC 9728 - OAuth 2.0 Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728), which allows clients to discover where to authenticate. This was crucial for VS Code and other MCP clients that needed to know how to obtain tokens.

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  MCP Client │────>│   MCP Server    │────>│  Graph API   │
│  (VS Code)  │     │  (Resource)     │     │  (Downstream)│
└─────────────┘     └─────────────────┘     └──────────────┘
      │                    │                       │
      │ 1. Discover auth   │                       │
      │    server          │                       │
      │◄───────────────────│                       │
      │                    │                       │
      │ 2. Get token from  │                       │
      │    Azure AD        │                       │
      │────────────────────────────────────────────>
      │                    │                       │
      │ 3. Call with token │                       │
      │───────────────────>│                       │
      │                    │ 4. OBO exchange       │
      │                    │──────────────────────>│
      │                    │                       │
      │ 5. Response        │                       │
      │◄───────────────────│                       │
```

### Section 2: Token Verification with JWKS Caching

The first challenge was validating Azure AD tokens without adding latency to every request. Azure AD uses asymmetric keys (RS256), and the public keys are available via a JWKS (JSON Web Key Set) endpoint.

**The naive approach**—fetching JWKS on every request—would add 50-100ms of latency. Instead, we implemented a caching strategy:

```python
class EntraIdTokenVerifier(TokenVerifier):
    """JWT token verifier with 1-hour JWKS caching."""
    
    def __init__(self, tenant_id: str, client_id: str):
        self.jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        self._jwks_cache: Optional[Dict] = None
        self._cache_expiry: Optional[datetime] = None
    
    async def _get_jwks(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        
        # Return cached if still valid
        if self._jwks_cache and self._cache_expiry and now < self._cache_expiry:
            return self._jwks_cache
        
        # Fetch fresh JWKS
        async with aiohttp.ClientSession() as session:
            async with session.get(self.jwks_uri) as response:
                self._jwks_cache = await response.json()
                self._cache_expiry = now + timedelta(hours=1)
                return self._jwks_cache
```

This reduced our token validation to sub-millisecond times for cached keys while still refreshing them hourly to handle key rotation.

### Section 3: The On-Behalf-Of Flow Challenge

Our customer needed to call Microsoft Graph to fetch user profiles. The problem: we had the *user's* token for our MCP server, but we needed a *Graph API* token.

Enter the [OAuth 2.0 On-Behalf-Of (OBO) flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow). This allows a middle-tier service to exchange an incoming token for an outbound token to a different resource.

```python
async def get_graph_token_obo(assertion_token: str) -> str:
    """Exchange user token for Graph API token using OBO flow."""
    
    # Validate the incoming token isn't about to expire
    _validate_assertion_token_expiry(assertion_token)
    
    token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "requested_token_use": "on_behalf_of",
        "scope": "https://graph.microsoft.com/User.Read",
        "assertion": assertion_token,
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(token_endpoint, data=data) as resp:
            body = await resp.json()
            return body["access_token"]
```

A critical lesson learned: **always validate the incoming token's expiry before OBO exchange**. We added a 5-minute buffer to prevent race conditions where the token expires mid-exchange:

```python
def _validate_assertion_token_expiry(assertion_token: str) -> None:
    payload = jwt.decode(assertion_token, options={"verify_signature": False})
    exp = payload.get("exp")
    
    if exp:
        time_until_expiry = exp - time.time()
        if time_until_expiry < 300:  # 5 minutes
            raise RuntimeError("Token expiring soon, please re-authenticate")
```

### Section 4: RFC 9728 Protected Resource Metadata

For MCP clients to know where to authenticate, we needed to implement the OAuth Protected Resource Metadata endpoint:

```python
@mcp_server.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def oauth_protected_resource_metadata(request: Request) -> JSONResponse:
    return JSONResponse({
        "resource": "http://localhost:9000",
        "bearer_methods_supported": ["header"],
        "authorization_servers": [
            f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        ],
        "scopes_supported": [
            f"api://{client_id}/access_as_user",
            f"api://{client_id}/MCP.Tools",
        ]
    })
```

This endpoint tells clients: "I'm a protected resource, and here's where you get tokens to access me."

### Section 5: Secretless Production Deployment

Client secrets are fine for development, but production deployments should avoid secrets entirely. We implemented support for **Federated Identity Credentials**, which use Azure Managed Identities:

```python
async def _get_graph_token_with_federated_credential(assertion_token: str) -> str:
    # Use managed identity token as client assertion
    mi_credential = ManagedIdentityCredential(client_id=managed_identity_oid)
    mi_token = await mi_credential.get_token("api://AzureADTokenExchange/.default")
    
    def get_client_assertion() -> str:
        return mi_token.token
    
    obo_credential = OnBehalfOfCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_assertion_func=get_client_assertion,
        user_assertion=assertion_token,
    )
    
    graph_token = await obo_credential.get_token("https://graph.microsoft.com/User.Read")
    return graph_token.token
```

This eliminates client secrets from the deployment entirely—the managed identity authenticates using Azure's Instance Metadata Service (IMDS).

## The Destination: Outcomes and Learnings

After several iterations, we delivered a production-ready MCP server that met all requirements:

| Metric | Result |
|--------|--------|
| Token validation latency | < 1ms (cached JWKS) |
| OBO exchange latency | ~100-200ms (Azure AD round trip) |
| Standards compliance | OAuth 2.1, RFC 9728, RFC 8414 |
| Test coverage | 27 tests passing |

### Key Takeaways

1. **Cache JWKS aggressively**: A 1-hour cache dramatically reduces latency while still handling key rotation.

2. **Validate token expiry before OBO**: A 5-minute buffer prevents frustrating "token expired during exchange" errors.

3. **Plan for secretless deployments**: Federated Identity Credentials should be the production default.

4. **Implement Protected Resource Metadata**: MCP clients need `/.well-known/oauth-protected-resource` to discover auth requirements.

5. **Handle scope extraction carefully**: Azure AD tokens may have scopes in `scp` (space-separated string) or `roles` (array)—handle both.

## Conclusion

Building a secure MCP server in a rapidly evolving specification landscape was challenging, but the resulting implementation follows best practices that should remain stable. The key insight is that MCP authentication is fundamentally OAuth 2.1 with Protected Resource Metadata—once you understand that, the pieces fall into place.

We've open-sourced our implementation as a demo that others can use as a starting point. It includes:
- Complete OAuth 2.1 / OIDC authentication with Azure AD
- On-Behalf-Of flow for Microsoft Graph
- JWKS caching for low-latency token validation
- Support for both client secrets and federated credentials
- Comprehensive test suite

## Call to Action

If you're building MCP servers that need authentication, check out our demo implementation. The code is structured to be extracted and adapted for your own projects:

```bash
# Clone and run
cd src/demo_mcp_server
cp .env.example .env
# Edit .env with your Azure AD values
python server.py --no-auth  # Test without auth first
python server.py            # Run with auth enabled
```

The MCP ecosystem is growing rapidly, and we believe secure-by-default implementations will be crucial for enterprise adoption. We hope this work helps accelerate that journey.

## Thanks

A special thanks to the [mcp-workshop](https://github.com/huangyingting/mcp-workshop) project for providing OAuth setup guidance, and to the FastMCP team for building a solid foundation for MCP server development.

---

*For more details on Azure AD token verification, see the [official documentation](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens). For the full MCP authorization specification, visit [modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).*
