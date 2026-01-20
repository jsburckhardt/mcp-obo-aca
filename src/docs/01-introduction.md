# Introduction

This tutorial walks you through building an authenticated MCP (Model Context Protocol) server with OAuth 2.1 / OIDC authentication using Azure AD (Entra ID) and the On-Behalf-Of (OBO) flow.

## What This Demo Covers

- **OAuth 2.1 Authentication**: How to protect your MCP server with Azure AD tokens
- **On-Behalf-Of Flow**: How to call downstream APIs (like Microsoft Graph) on behalf of authenticated users
- **RFC 9728 Compliance**: Implementing Protected Resource Metadata endpoints
- **FastMCP Integration**: Using the FastMCP library with custom authentication

## What You'll Build

A minimal MCP server with three tools:

1. **greet_test** - A simple greeting tool (no auth required)
2. **get_mcp_server_status** - Returns server status (no auth required)
3. **whoami** - Returns the authenticated user's profile from Microsoft Graph (demonstrates OBO flow)

## Prerequisites

- Python 3.10+
- An Azure AD (Entra ID) tenant
- An Azure AD app registration with appropriate permissions
- `uv` package manager (recommended) or `pip`

## Architecture Overview

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  MCP Client │────>│   MCP Server    │────>│  GeneralService  │
│  (VS Code)  │     │  (Entry Point)  │     │  (greet, whoami) │
└─────────────┘     └─────────────────┘     └──────────────────┘
      │                    │                       │
      │                    ▼                       │
      │            ┌─────────────────┐             │
      │            │ MCPToolFactory  │             │
      │            │ (core/factory)  │             │
      │            └─────────────────┘             │
      │                    │                       │
      ▼                    ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    Authentication Layer                       │
│  ┌─────────────────────┐    ┌─────────────────────────────┐  │
│  │ EntraIdTokenVerifier│    │     get_graph_token_obo()   │  │
│  │ (auth/verifier.py)  │    │     (auth/obo.py)           │  │
│  └─────────────────────┘    └─────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
      │                                            │
      ▼                                            ▼
┌──────────────┐                           ┌──────────────────┐
│   Azure AD   │                           │  Microsoft Graph │
│  (Entra ID)  │                           │   API (/me)      │
└──────────────┘                           └──────────────────┘
```

## Architecture Decision

For details on why this architecture was chosen over alternatives (such as APIM + Azure Functions or APIM + Container Apps), see [ADR-001: MCP Server Hosting Architecture](adr/ADR-001-mcp-server-hosting-architecture.md).

## Next Steps

Continue to [02-azure-setup.md](02-azure-setup.md) to configure your Azure AD app registration.
