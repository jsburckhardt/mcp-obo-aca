# ADR-001: MCP Server Hosting Architecture for OAuth 2.1 + OBO Flow

## Status

**Accepted**

## Date

2026-01-20

## Context

### Customer Use Case

The customer needed a **voice-enabled assistant** that could stream responses and answer questions about specific organizational data. Users would interact via voice to query and receive summaries from documents stored in SharePoint. This required:

- **Real-time streaming** - Voice interactions demand low-latency responses with support for streaming audio/text
- **Authenticated data access** - Documents are secured; access must respect user permissions
- **On-Behalf-Of pattern** - The MCP server must access SharePoint/Microsoft Graph using the authenticated user's identity, not service credentials

While the specific implementation details for SharePoint data retrieval are omitted here (document extraction, chunking, vector search, etc.), this ADR focuses on the **reusable architectural patterns** that apply to any MCP server requiring:

- OAuth 2.1 authentication with Azure AD (Entra ID)
- On-Behalf-Of (OBO) flow to call downstream APIs on behalf of authenticated users
- Low latency with sub-second response times and no cold starts
- Auto-scaling to handle variable load efficiently
- Standards compliance (RFC 9728, RFC 8414, RFC 8707, MCP Authorization Specification)

The MCP protocol requires support for SSE (Server-Sent Events) or Streamable HTTP transport for real-time communication between MCP clients and servers, which aligns perfectly with the voice streaming requirements.

## Decision Drivers

| Priority | Driver | Description |
|----------|--------|-------------|
| 1 | **Low Latency** | Must maintain <1s response times; cold starts are unacceptable |
| 2 | **Scaling** | Handle variable load with auto-scaling capabilities |
| 3 | **Pattern Reusability** | Create a template others can follow for MCP server implementations |
| 4 | **Operational Simplicity** | Minimize infrastructure complexity and moving parts |
| 5 | **Standards Compliance** | Full compliance with OAuth 2.1, RFC 9728, and MCP specification |

## Considered Options

### Option A: Azure Container Apps with Internal Authentication (Recommended)

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

### Option D: Azure App Service (Web App) with Built-in MCP Authorization

Azure App Service with native MCP authentication support (preview) and built-in OAuth integration.

```
┌──────────────────────────────────────────────────────────────────┐
│                      Azure App Service                           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Built-in MCP Authorization (Preview)           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │ │
│  │  │   Easy Auth │  │  MCP OAuth  │  │  Always On          │  │ │
│  │  │  (Entra ID) │  │  Endpoints  │  │  (No Cold Start)    │  │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      MCP Server Code                        │ │
│  │                                                             │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐     │ │
│  │  │  MCP Tools  │  │  OBO Flow   │  │  Graph Client   │     │ │
│  │  │  (FastMCP)  │  │             │  │                 │     │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────┐                                             │
│  │ App Service     │                                             │
│  │ Managed Identity│                                             │
│  └─────────────────┘                                             │
└──────────────────────────────────────────────────────────────────┘
              │                                    │
              ▼                                    ▼
    ┌──────────────────┐                ┌──────────────────┐
    │    Azure AD      │                │  Microsoft Graph │
    │   (Entra ID)     │                │       API        │
    └──────────────────┘                └──────────────────┘
```

**Characteristics:**

- PaaS-first platform with built-in MCP authorization (preview)
- Native Easy Auth with Azure AD integration
- No cold starts with "Always On" feature (Standard tier+)
- Built-in deployment slots for blue/green deployments
- Configurable idle timeouts for long-running SSE connections
- Container support or code deployment (Python, Node.js, .NET)

**Latency Profile:**

- Request → App Service: ~0ms overhead (direct)
- Easy Auth evaluation: ~5-15ms (managed by platform)
- Cold start: Eliminated with "Always On" in Standard+ tiers
- Total overhead: ~5-15ms for platform auth

## Decision

We will use **Option A: Azure Container Apps with Internal Authentication**.

## Rationale

### 1. Lowest Latency (Primary Driver)

Option A eliminates the gateway hop entirely. With JWKS caching (1-hour TTL), token verification adds only 1-5ms. Options B and C add 20-50ms of overhead per request due to APIM policy evaluation and internal routing. While Option D (App Service) has low latency (~5-15ms), Option A is still faster for high-throughput scenarios.

For the customer's <1s latency requirement with always-warm instances, this overhead may seem acceptable, but it compounds with downstream API calls (OBO + Graph API), making every millisecond valuable.

### 2. Simplest Operational Model

Option A deploys as a single unit via `azd up`. There's one service to monitor, one set of logs, and one scaling configuration. Options B and C require coordinating two services, their networking, and their individual scaling behaviors. While Option D (App Service) is also simple as a PaaS offering, it lacks the container-native flexibility.

### 3. Event-Driven and Unpredictable Workloads

Container Apps excel at handling **variable, event-driven, or unpredictable workloads** with KEDA-based autoscaling and scale-to-zero capabilities. This makes it ideal for MCP servers with:
- Bursty request patterns (Claude Desktop sessions starting/stopping)
- Long idle periods (no active MCP clients)
- Dynamic scaling needs (multiple concurrent users)

App Service requires "Always On" to avoid cold starts, resulting in continuous billing even during idle periods. For cost-conscious deployments, Container Apps can scale to zero and incur minimal costs during low usage.

### 4. Self-Contained and Portable

The container image includes everything needed to run the MCP server. It can be deployed to any container platform (AKS, ACI, on-premises) without depending on APIM infrastructure or App Service-specific features.

### 5. Full Control Over Standards Compliance

Implementing token verification and RFC 9728 endpoints directly in the application provides complete control over compliance behavior, error handling, and edge cases. Option D's preview MCP authorization feature is convenient but offers less flexibility for custom OAuth 2.1 flows and RFC compliance requirements.

### 6. Streaming Protocol Optimization

Container Apps provide excellent support for **SSE (Server-Sent Events)** and streamable HTTP transport required by the MCP protocol. The Envoy-based ingress handles long-lived connections efficiently. While App Service also supports SSE, Container Apps' container-native architecture is better suited for streaming workloads.

### 5. Cost Efficiency

| Component | Option A | Option B | Option C | Option D |
|-----------|----------|----------|----------|----------|
| Container Apps (minReplicas=1) | ~$30-50/month | - | ~$30-50/month | - |
| Functions Premium (always-ready) | - | ~$150+/month | - | - |
| APIM (Basic v2) | - | ~$175/month | ~$175/month | - |
| App Service (Standard S1) | - | - | - | ~$75/month |
| App Service (Premium P1v3) | - | - | - | ~$125/month |
| **Total Estimate** | **~$30-50/month** | **~$325+/month** | **~$205+/month** | **~$75-125/month** |

*Estimates based on minimal configuration; actual costs vary by usage.*

### Comparison Matrix

| Criteria | Option A (Container Apps) ✅ | Option B (APIM + Functions) | Option C (APIM + Container Apps) | Option D (App Service) |
|----------|------------------------------|----------------------------|----------------------------------|------------------------|
| **Latency** | ✅ Lowest (~1-5ms auth) | ⚠️ High (~20-50ms) | ⚠️ Medium (~15-30ms) | ✅ Low (~5-15ms) |
| **Cold Start** | ⚠️ Mitigated (minReplicas=1) | ⚠️ Requires Premium plan | ⚠️ Mitigated (minReplicas=1) | ✅ None (Always On) |
| **Streaming Support** | ✅ Excellent (SSE/HTTP/2) | ⚠️ Limited timeout | ✅ Good | ✅ Configurable timeout |
| **Autoscaling** | ✅ Event-driven, scale-to-zero | ⚠️ Metric-based only | ✅ Event-driven | ⚠️ Metric-based, no scale-to-zero |
| **Operational Complexity** | ✅ Very Low (single service) | ⚠️ High (2 services) | ⚠️ High (2 services) | ✅ Very Low (PaaS) |
| **OAuth Control** | ✅ Full control (RFC 9728) | ⚠️ Limited to APIM policies | ⚠️ Limited to APIM policies | ⚠️ Preview feature, less control |
| **Cost** | ✅ ~$30-50/mo | ❌ ~$325+/mo | ⚠️ ~$205+/mo | ⚠️ ~$75-125/mo |
| **Deployment Slots** | ❌ No | ❌ No | ❌ No (Container Apps) | ✅ Yes (blue/green) |
| **MCP Authorization** | ✅ Full implementation | ⚠️ Via APIM policies | ⚠️ Via APIM policies | ⚠️ Preview, built-in |
| **Variable/Event-Driven Workload** | ✅ Excellent | ❌ Poor | ✅ Good | ❌ Always-on billing |

### When to Reconsider

**Option C (APIM + Container Apps)** should be reconsidered if:

- Multiple MCP servers need centralized governance
- Organization mandates API Management for all external APIs
- Advanced APIM features (rate limiting, analytics, developer portal) become requirements
- REST APIs need to be exposed as MCP servers without code changes

**Option D (Azure App Service)** should be reconsidered if:

- Team prefers platform-managed authentication over custom implementation
- Deployment slots for blue/green deployments are required
- Preview MCP authorization features are acceptable
- Workload is predictable and doesn't require scale-to-zero
- Higher cost (~2-4x) is acceptable for operational simplicity

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
- [Host Remote MCP Servers in Azure App Service](https://techcommunity.microsoft.com/blog/appsonazureblog/host-remote-mcp-servers-in-azure-app-service/4405082)
- [Configure MCP Authentication in Azure App Service](https://learn.microsoft.com/azure/app-service/configure-authentication-mcp)

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
