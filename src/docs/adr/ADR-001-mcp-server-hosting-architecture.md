# ADR-001: MCP Server Hosting Architecture for OAuth 2.1 + OBO Flow

## Status

**Accepted**

## Date

2026-01-20

## Context

We are building an MCP (Model Context Protocol) server that requires:

- **OAuth 2.1 authentication** with Azure AD (Entra ID)
- **On-Behalf-Of (OBO) flow** to call downstream APIs (Microsoft Graph) on behalf of authenticated users
- **Low latency** - Customer requirement of sub-second response times with no cold starts
- **Auto-scaling** - Handle variable load efficiently
- **Reusable pattern** - Serve as a template for future MCP server implementations
- **Standards compliance** - RFC 9728, RFC 8414, RFC 8707, MCP Authorization Specification

The MCP protocol requires support for SSE (Server-Sent Events) or Streamable HTTP transport for real-time communication between MCP clients and servers.

## Decision Drivers

| Priority | Driver | Description |
|----------|--------|-------------|
| 1 | **Low Latency** | Must maintain <1s response times; cold starts are unacceptable |
| 2 | **Scaling** | Handle variable load with auto-scaling capabilities |
| 3 | **Pattern Reusability** | Create a template others can follow for MCP server implementations |
| 4 | **Operational Simplicity** | Minimize infrastructure complexity and moving parts |
| 5 | **Standards Compliance** | Full compliance with OAuth 2.1, RFC 9728, and MCP specification |

## Considered Options

### Option A: Azure Container Apps with Internal Authentication

Authentication, token verification, and OBO flow are handled directly within the application code.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                         │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      MCP Server                           │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │  │
│  │  │   Token     │  │  MCP Tools  │  │   OBO Flow      │    │  │
│  │  │  Verifier   │  │  (FastMCP)  │  │  (Graph API)    │    │  │
│  │  │  (JWKS)     │  │             │  │                 │    │  │
│  │  └──────┬──────┘  └─────────────┘  └────────┬────────┘    │  │
│  │         │                                    │            │  │
│  └─────────┼────────────────────────────────────┼────────────┘  │
│            │                                    │               │
│  ┌─────────┴─────────┐                          │               │
│  │ Managed Identity  │──────────────────────────┘               │
│  │ (Secretless Auth) │                                          │
│  └───────────────────┘                                          │
└───────────────────────────────────────────────────────────────-─┘
             │                                    │
             ▼                                    ▼
   ┌──────────────────┐                ┌──────────────────┐
   │    Azure AD      │                │  Microsoft Graph │
   │   (Entra ID)     │                │       API        │
   │                  │                │                  │
   │  - JWKS Endpoint │                │  - User Profile  │
   │  - Token Issuer  │                │  - OBO Exchange  │
   └──────────────────┘                └──────────────────┘
```

**Characteristics:**

- Single deployment unit (container image)
- Direct token verification using cached JWKS
- OBO flow via Azure Identity SDK with federated credentials
- `minReplicas=1` ensures always-warm instances
- Full control over RFC compliance implementation
- SSE transport fully supported

**Latency Profile:**

- Request → Application: ~0ms overhead (direct)
- Token verification: ~1-5ms (JWKS cached for 1 hour)
- Cold start: Eliminated with `minReplicas=1`

### Option B: Azure API Management + Azure Functions

API Management handles JWT validation via policies; Azure Functions execute MCP tools and OBO flow.

```
┌──────────────────────────────────────────────────────────────────┐
│                         Request Flow                             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Azure API Management                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     Inbound Policies                        │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │validate-jwt │  │ rate-limit  │  │  cors / headers     │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Azure Functions                             │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │   MCP Tools     │  │   OBO Flow      │  │  Graph Client   │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Microsoft Graph │
                    └──────────────────┘
```

**Characteristics:**

- Two-service architecture with separation of concerns
- Policy-based authentication (declarative)
- Centralized API governance and monitoring
- Functions Premium plan required for always-ready instances
- OBO flow implemented in Function code
- APIM adds latency overhead per request

**Latency Profile:**

- Request → APIM: ~10-30ms (policy evaluation)
- APIM → Functions: ~5-10ms (internal routing)
- Functions cold start: Requires Premium plan with always-ready instances
- Total overhead: ~20-50ms additional latency

### Option C: Azure API Management + Azure Container Apps

API Management as gateway with native MCP server support; Container Apps as backend compute.

```
┌──────────────────────────────────────────────────────────────────┐
│                    Azure API Management                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │               MCP Server Gateway Features                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │ MCP Server  │  │validate-jwt │  │  Monitoring &       │  │ │
│  │  │ Endpoints   │  │  policy     │  │  Rate Limiting      │  │ │
│  │  │ (/mcp,/sse) │  │             │  │                     │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                          │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │  MCP Backend    │  │   OBO Flow      │  │  Graph Client   │   │
│  │  (Tools Only)   │  │                 │  │                 │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**Characteristics:**

- APIM provides native MCP server support (Streamable HTTP & SSE)
- Centralized API governance across all MCP servers
- Container Apps handles business logic and OBO
- `minReplicas=1` on Container Apps + APIM always-on
- Enables exposing REST APIs as MCP servers via APIM

**Latency Profile:**

- Request → APIM: ~10-20ms (MCP routing + policy)
- APIM → Container Apps: ~5-10ms
- Total overhead: ~15-30ms additional latency

## Decision

We will use **Option A: Azure Container Apps with Internal Authentication**.

## Rationale

### 1. Lowest Latency (Primary Driver)

Option A eliminates the gateway hop entirely. With JWKS caching (1-hour TTL), token verification adds only 1-5ms. Options B and C add 20-50ms of overhead per request due to APIM policy evaluation and internal routing.

For the customer's <1s latency requirement with always-warm instances, this overhead may seem acceptable, but it compounds with downstream API calls (OBO + Graph API), making every millisecond valuable.

### 2. Simplest Operational Model

Option A deploys as a single unit via `azd up`. There's one service to monitor, one set of logs, and one scaling configuration. Options B and C require coordinating two services, their networking, and their individual scaling behaviors.

### 3. Self-Contained and Portable

The container image includes everything needed to run the MCP server. It can be deployed to any container platform (AKS, ACI, on-premises) without depending on APIM infrastructure.

### 4. Full Control Over Standards Compliance

Implementing token verification and RFC 9728 endpoints directly in the application provides complete control over compliance behavior, error handling, and edge cases.

### 5. Cost Efficiency

| Component | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| Container Apps (minReplicas=1) | ~$30-50/month | - | ~$30-50/month |
| Functions Premium (always-ready) | - | ~$150+/month | - |
| APIM (Basic v2) | - | ~$175/month | ~$175/month |
| **Total Estimate** | **~$30-50/month** | **~$325+/month** | **~$205+/month** |

*Estimates based on minimal configuration; actual costs vary by usage.*

### When to Reconsider

Option C (APIM + Container Apps) should be reconsidered if:

- Multiple MCP servers need centralized governance
- Organization mandates API Management for all external APIs
- Advanced APIM features (rate limiting, analytics, developer portal) become requirements
- REST APIs need to be exposed as MCP servers without code changes

## Consequences

### Positive

- **Lowest latency** - Single service with no gateway overhead
- **Simplest deployment** - One `azd up` deploys everything
- **Full control** - Complete ownership of authentication and protocol compliance
- **Cost effective** - No APIM licensing costs
- **Portable** - Container can run anywhere
- **Secretless in production** - Federated credentials eliminate secret management

### Negative

- **No centralized gateway** - Each MCP server manages its own auth
- **Coupled implementation** - Auth logic is part of the application
- **Manual compliance** - Must implement RFC endpoints in code
- **No built-in rate limiting** - Would need to implement or add middleware
- **Limited API analytics** - Requires separate monitoring setup

## Compliance

This architecture maintains full compliance with:

| Standard | Status | Implementation |
|----------|--------|----------------|
| MCP Authorization Specification | ✓ | FastMCP with custom auth provider |
| OAuth 2.1 (Draft 13) | ✓ | EntraIdTokenVerifier class |
| RFC 9728 - Protected Resource Metadata | ✓ | `/.well-known/oauth-protected-resource` endpoint |
| RFC 8707 - Resource Indicators | ✓ | Scopes include resource URI prefix |
| RFC 8414 - Authorization Server Metadata | ✓ | `/.well-known/oauth-authorization-server` endpoint |

## References

### Azure Documentation

- [Azure Container Apps Overview](https://learn.microsoft.com/azure/container-apps/overview)
- [Azure Container Apps Scaling](https://learn.microsoft.com/azure/container-apps/scale-app)
- [Reducing Cold-Start Time on Azure Container Apps](https://learn.microsoft.com/azure/container-apps/cold-start)
- [Azure API Management MCP Server Support](https://learn.microsoft.com/azure/api-management/mcp-server-overview)
- [Azure API Management JWT Validation Policy](https://learn.microsoft.com/azure/api-management/validate-jwt-policy)
- [Azure Functions Hosting Options](https://learn.microsoft.com/azure/azure-functions/functions-scale)
- [Azure Functions Premium Plan](https://learn.microsoft.com/azure/azure-functions/functions-premium-plan)

### OAuth and Authentication

- [Microsoft Identity Platform OBO Flow](https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [OAuth 2.1 Draft Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13)
- [RFC 9728 - OAuth 2.0 Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728)
- [RFC 8414 - OAuth 2.0 Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414)
- [RFC 8707 - Resource Indicators for OAuth 2.0](https://www.rfc-editor.org/rfc/rfc8707.html)

### MCP Protocol

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)
- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)

---

*This ADR documents the architectural decision for the [mcp-obo-aca](https://github.com/jsburckhardt/mcp-obo-aca) repository.*
