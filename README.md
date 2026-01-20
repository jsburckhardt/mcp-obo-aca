# MCP Server with OAuth 2.1 and On-Behalf-Of (OBO) Flow

An Azure Developer CLI (azd) ready template for deploying an MCP (Model Context Protocol) server with OAuth 2.1 authentication and On-Behalf-Of (OBO) flow to Azure Container Apps.

## Features

- ✅ **OAuth 2.1 / OIDC** - Full authentication with Azure AD (Entra ID)
- ✅ **On-Behalf-Of (OBO) Flow** - Call Microsoft Graph API on behalf of the user
- ✅ **RFC 9728 Compliance** - Protected Resource Metadata endpoint
- ✅ **Secretless Deployment** - Federated identity credentials for production
- ✅ **Azure Container Apps** - Serverless, auto-scaling deployment
- ✅ **azd Ready** - Deploy with a single `azd up` command

## Quick Start

### Prerequisites

- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Docker](https://docs.docker.com/get-docker/)
- Azure subscription with permissions to create resources

### Deploy to Azure

```bash
# Clone this repository
git clone https://github.com/jsburckhardt/mcp-obo-aca.git
cd mcp-obo-aca

# Login to Azure
azd auth login

# Initialize the environment
azd init

# Set your Azure AD app registration client ID
azd env set AZURE_CLIENT_ID "your-client-id-here"

# Deploy everything
azd up
```

### Post-Deployment: Configure Federated Credential

After deployment, configure a federated credential on your Azure AD app registration:

1. Note the **Managed Identity Principal ID** from the deployment output
2. Go to Azure Portal > Azure AD > App Registrations > Your App
3. Go to **Certificates & secrets** > **Federated credentials** > **Add credential**
4. Select **Customer Managed Keys**
5. Enter the Managed Identity Principal ID
6. Add audience: `api://AzureADTokenExchange`

See [src/docs/02-azure-setup.md](src/docs/02-azure-setup.md) for detailed instructions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    MCP Server                             │   │
│  │                                                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │   FastMCP   │  │   Token     │  │   OBO Flow      │   │   │
│  │  │   Server    │  │   Verifier  │  │   (Graph API)   │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                    ┌─────────┴─────────┐                        │
│                    │  Managed Identity  │                        │
│                    │  (Secretless Auth) │                        │
│                    └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
    ┌──────────────────┐              ┌──────────────────┐
    │   Azure AD       │              │  Microsoft Graph │
    │   (Entra ID)     │              │       API        │
    │                  │              │                  │
    │  - Token Verify  │              │  - User Profile  │
    │  - JWKS Endpoint │              │  - On-Behalf-Of  │
    └──────────────────┘              └──────────────────┘
```

## Project Structure

```
mcp-obo-aca/
├── azure.yaml              # Azure Developer CLI configuration
├── infra/                  # Bicep templates for Azure resources
│   ├── main.bicep          # Entry point
│   ├── main.parameters.json
│   └── modules/            # Modular Bicep templates
│       ├── container-app.bicep
│       ├── container-apps-environment.bicep
│       ├── container-registry.bicep
│       ├── log-analytics.bicep
│       └── managed-identity.bicep
└── src/                    # MCP Server source code
    ├── server.py           # Main entry point
    ├── auth/               # Authentication module
    │   ├── verifier.py     # Token verification with JWKS caching
    │   └── obo.py          # On-Behalf-Of flow implementation
    ├── services/           # Business logic
    │   └── general_service.py  # Demo tools
    ├── config/             # Configuration
    ├── utils/              # Utilities
    ├── tests/              # Test suite
    ├── docs/               # Tutorial documentation
    ├── Dockerfile          # Container image
    └── requirements.txt    # Python dependencies
```

## MCP Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `greet_test` | Simple greeting | No |
| `get_mcp_server_status` | Server status info | No |
| `whoami` | User profile from Graph API | Yes (OBO) |

## Local Development

```bash
cd src

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your Azure AD settings

# Run without auth (for testing)
python server.py --no-auth

# Run with auth
python server.py

# Run tests
pytest tests/ -v
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/mcp` | MCP protocol endpoint (SSE) |
| `/health` | Health check |
| `/.well-known/oauth-protected-resource` | RFC 9728 metadata |
| `/.well-known/oauth-authorization-server` | RFC 8414 metadata |

## Documentation

- [Introduction](src/docs/01-introduction.md) - Overview and prerequisites
- [Azure Setup](src/docs/02-azure-setup.md) - App registration configuration
- [Server Implementation](src/docs/03-server-implementation.md) - Code walkthrough
- [Running and Testing](src/docs/04-running-and-testing.md) - Usage guide
- [Troubleshooting](src/docs/05-troubleshooting.md) - Common issues
- [Infrastructure](infra/README.md) - Bicep templates documentation
- [Architecture Decision Records](src/docs/adr/README.md) - Why this architecture was chosen

## Standards Compliance

- [MCP Authorization Specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [OAuth 2.1 (Draft 13)](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13)
- [RFC 9728 - Protected Resource Metadata](https://datatracker.ietf.org/doc/html/rfc9728)
- [RFC 8707 - Resource Indicators](https://www.rfc-editor.org/rfc/rfc8707.html)
- [RFC 8414 - Authorization Server Metadata](https://datatracker.ietf.org/doc/html/rfc8414)

## License

MIT
