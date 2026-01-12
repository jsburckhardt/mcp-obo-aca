# Demo MCP Server

A minimal, reusable MCP (Model Context Protocol) server with OAuth 2.1 / OIDC authentication and On-Behalf-Of (OBO) flow for Microsoft Graph API.

This demo serves as a community sample for building authenticated MCP servers with Azure AD (Entra ID) integration.

## Features

- ✅ OAuth 2.1 / OIDC authentication with Azure AD (Entra ID)
- ✅ On-Behalf-Of (OBO) flow for calling Microsoft Graph API
- ✅ RFC 9728 Protected Resource Metadata compliance
- ✅ JWKS caching for optimal performance
- ✅ Support for both client secret and federated identity credentials
- ✅ Docker support with health checks
- ✅ Comprehensive test suite

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure AD configuration
```

### 3. Run the Server

```bash
# Without authentication (for testing)
python server.py --no-auth

# With authentication
python server.py

# With debug logging
python server.py --debug
```

### 4. Test Endpoints

```bash
# Health check
curl http://localhost:9000/health

# OAuth metadata
curl http://localhost:9000/.well-known/oauth-protected-resource
```

## Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `greet_test` | Simple greeting | No |
| `get_mcp_server_status` | Server status | No |
| `whoami` | User profile from Graph API | Yes (OBO) |

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  MCP Client │────>│   MCP Server    │────>│  GeneralService  │
└─────────────┘     └─────────────────┘     └──────────────────┘
                           │
                    Authentication Layer
              ┌────────────┴────────────┐
              │                         │
    ┌─────────────────┐       ┌─────────────────┐
    │ Token Verifier  │       │   OBO Flow      │
    │ (JWKS caching)  │       │ (Graph API)     │
    └─────────────────┘       └─────────────────┘
              │                         │
              ▼                         ▼
        ┌──────────┐            ┌──────────────┐
        │ Azure AD │            │ Graph API    │
        └──────────┘            └──────────────┘
```

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `ENABLE_AUTH` | Enable authentication | No (default: true) |
| `TENANT_ID` | Azure AD tenant ID | When auth enabled |
| `CLIENT_ID` | Application (client) ID | When auth enabled |
| `CLIENT_SECRET` | Client secret for OBO | One of secret or FIC |
| `FEDERATED_CREDENTIAL_OID` | Managed identity OID | One of secret or FIC |
| `GRAPH_SCOPE` | Graph API scope | No (default: User.Read) |

See [.env.example](.env.example) for all options.

## Documentation

1. [Introduction](docs/01-introduction.md) - Overview and prerequisites
2. [Azure Setup](docs/02-azure-setup.md) - App registration configuration
3. [Server Implementation](docs/03-server-implementation.md) - Code walkthrough
4. [Running and Testing](docs/04-running-and-testing.md) - Usage guide
5. [Troubleshooting](docs/05-troubleshooting.md) - Common issues

## Standards Compliance

- ✅ [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- ✅ [OAuth 2.1 (Draft 13)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13)
- ✅ [RFC 9728 - Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728)
- ✅ [RFC 8707 - Resource Indicators](https://www.rfc-editor.org/rfc/rfc8707.html)
- ✅ [RFC 8414 - Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414)

## References

- [OAuth Provider Setup (mcp-workshop)](https://github.com/huangyingting/mcp-workshop)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Azure AD Token Verification](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)
- [On-Behalf-Of Flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow)

## License

MIT
