# Infrastructure Deployment Guide

This guide explains how to deploy the MCP Server with OAuth 2.1 + OBO flow to Azure Container Apps using Azure Developer CLI (azd).

## Prerequisites

- **Azure Developer CLI (azd)**: [Install azd](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) (v1.15.0+)
- **Azure CLI**: [Install Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- **Azure Subscription**: With permissions to create resources
- **Azure AD App Registration**: See [Azure Setup Guide](../src/docs/02-azure-setup.md)

## Architecture

The infrastructure deploys the following Azure resources:

```
+------------------------------------------------------------------+
|                         Resource Group                            |
|                                                                   |
|   +------------------+     +--------------------------------+     |
|   |  Log Analytics   |<----|  Container Apps Environment   |     |
|   |    Workspace     |     |                                |     |
|   +------------------+     |   +-------------------------+  |     |
|                            |   |    MCP Server           |  |     |
|   +------------------+     |   |    Container App        |  |     |
|   | User-Assigned    |-----|   |                         |  |     |
|   | Managed Identity |     |   |  - OAuth 2.1 Auth       |  |     |
|   +------------------+     |   |  - OBO Flow (Graph API) |  |     |
|           |                |   |  - Health Probes        |  |     |
|           |                |   +-------------------------+  |     |
|           v                +--------------------------------+     |
|   +------------------+                                            |
|   | Azure Container  |<-- Container images (remote build)        |
|   |    Registry      |                                            |
|   +------------------+                                            |
+------------------------------------------------------------------+
                                |
                                v
                    +----------------------+
                    |   Microsoft Entra ID |
                    |                      |
                    |  - App Registration  |
                    |  - Federated Cred    |
                    |  - OAuth Tokens      |
                    +----------------------+
```

## Project Structure

```
/
├── azure.yaml                    # azd configuration (entry point)
├── infra/
│   ├── main.bicep                # Main Bicep template
│   ├── main.parameters.json      # Parameters (uses azd env vars)
│   ├── abbreviations.json        # Resource naming conventions
│   └── modules/
│       ├── log-analytics.bicep
│       ├── managed-identity.bicep
│       ├── container-registry.bicep
│       ├── container-apps-environment.bicep
│       └── container-app.bicep
└── src/
    ├── Dockerfile                # Container image definition
    ├── server.py                 # MCP server entry point
    └── ...
```

## Quick Start with azd

### 1. Login to Azure

```bash
# From the repository root
azd auth login
```

### 2. Initialize Environment

```bash
# Create a new environment (e.g., "dev", "staging", "prod")
azd env new dev
```

### 3. Configure Required Variables

```bash
# Required: Your Azure AD App Registration Client ID
azd env set AZURE_CLIENT_ID "your-app-client-id"

# Optional: Override tenant (defaults to subscription tenant)
azd env set AZURE_TENANT_ID "your-tenant-id"

# Optional: Disable auth for testing (default: true)
azd env set ENABLE_AUTH false
```

### 4. Deploy Everything

```bash
# Provision infrastructure AND deploy the app
azd up
```

This command will:
1. Provision all Azure resources (ACR, Container Apps Environment, etc.)
2. Build the Docker image remotely in Azure Container Registry
3. Deploy the container to Azure Container Apps
4. Output the service URLs and managed identity details

### 5. Set Resource Server URL (Required for OAuth Metadata)

After the first deployment, set the `RESOURCE_SERVER_URL` to your Container App's FQDN:

```bash
# Get the deployed URL from outputs
azd env get-values | grep mcpServerUrl

# Set the RESOURCE_SERVER_URL (replace with your actual URL)
azd env set RESOURCE_SERVER_URL "https://your-app.azurecontainerapps.io"

# Re-provision to update the container with the correct URL
azd provision
```

This ensures the OAuth Protected Resource Metadata (`/.well-known/oauth-protected-resource`) returns the correct `resource` URL instead of `localhost`.

### 6. Configure Federated Credential (Required for OBO)

After deployment, configure a federated credential on your Azure AD app registration to enable the secretless OBO flow:

1. **Get the Managed Identity Principal ID** from the deployment output:
   ```bash
   azd env get-values | grep MANAGED_IDENTITY
   ```

2. **Go to Azure Portal**:
   - Navigate to: **Microsoft Entra ID** > **App registrations** > **Your App**
   - Select **Certificates & secrets** > **Federated credentials** > **Add credential**

3. **Configure the Federated Credential**:
   - **Federated credential scenario**: Select **Other issuer**
   - **Issuer**: `https://login.microsoftonline.com/{tenant-id}/v2.0`
     (Replace `{tenant-id}` with your Azure AD tenant ID)
   - **Subject identifier**: The Managed Identity **Principal ID** from step 1
   - **Audience**: `api://AzureADTokenExchange`
   - **Name**: `mcp-server-obo-credential` (or your preferred name)

4. **Save** the credential

See [Azure Setup Guide](../src/docs/02-azure-setup.md) for detailed instructions with screenshots.

## How azure.yaml Works

The `azure.yaml` file in the repository root configures azd:

```yaml
name: demo-mcp-server

infra:
  provider: bicep
  path: ./infra
  module: main

services:
  demo-mcp-server:
    project: ./src
    language: py
    host: containerapp
    docker:
      path: ./src/Dockerfile
      context: ./src
      remoteBuild: true    # Builds in Azure, not locally
```

**Key points:**
- **remoteBuild: true** - Docker images are built in Azure Container Registry, so you don't need Docker installed locally
- **Hooks** - The config includes `preprovision`, `postprovision`, and `postdeploy` hooks that display helpful information

## Bicep Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | (from azd) | Base name for all resources |
| `location` | string | resource group location | Azure region |
| `clientId` | string | (required) | Azure AD app client ID |
| `clientSecret` | string | `''` | Client secret (optional, prefer managed identity) |
| `tenantId` | string | subscription tenant | Azure AD tenant ID |
| `enableAuth` | bool | `true` | Enable OAuth 2.1 authentication |
| `resourceServerUrl` | string | `''` | Canonical resource server URL (set after first deployment) |
| `containerImageName` | string | `demo-mcp-server` | Container image name |
| `containerImageTag` | string | `latest` | Container image tag |
| `containerPort` | int | `9000` | Port the container listens on |
| `minReplicas` | int | `0` | Minimum container replicas (0 = scale to zero) |
| `maxReplicas` | int | `3` | Maximum container replicas |
| `containerCpuCores` | string | `0.5` | CPU cores per container |
| `containerMemory` | string | `1Gi` | Memory per container |

## Deployment Outputs

After deployment, these outputs are available:

| Output | Description |
|--------|-------------|
| `containerRegistryLoginServer` | ACR login server URL |
| `containerAppFqdn` | Container App FQDN |
| `mcpServerUrl` | Full MCP server URL |
| `mcpEndpoint` | MCP protocol endpoint (`/mcp`) |
| `oauthMetadataUrl` | Protected resource metadata endpoint |
| `managedIdentityPrincipalId` | Principal ID for federated credential |
| `managedIdentityClientId` | Client ID of the managed identity |

View outputs:
```bash
# Using azd
azd env get-values

# Using Azure CLI
az deployment group show \
  --resource-group rg-<env-name> \
  --name main \
  --query properties.outputs
```

## Manual Deployment (Without azd)

If you prefer not to use azd:

### 1. Create Resource Group

```bash
az group create \
  --name rg-mcp-server-dev \
  --location eastus
```

### 2. Deploy Bicep Template

```bash
az deployment group create \
  --resource-group rg-mcp-server-dev \
  --template-file infra/main.bicep \
  --parameters \
    name=mcp-server \
    clientId=your-client-id
```

### 3. Build and Push Container

```bash
# Get ACR details
ACR_NAME=$(az deployment group show \
  --resource-group rg-mcp-server-dev \
  --name main \
  --query properties.outputs.containerRegistryName.value -o tsv)

# Login and build
az acr login --name $ACR_NAME
az acr build --registry $ACR_NAME --image demo-mcp-server:latest ./src
```

### 4. Restart Container App

```bash
CA_NAME=$(az deployment group show \
  --resource-group rg-mcp-server-dev \
  --name main \
  --query properties.outputs.containerAppName.value -o tsv)

az containerapp revision restart \
  --name $CA_NAME \
  --resource-group rg-mcp-server-dev
```

## Scaling Configuration

The Container App uses HTTP-based autoscaling:

- **Min replicas**: 0 (scales to zero when idle - cold start ~10s)
- **Max replicas**: 3
- **Scale trigger**: 100 concurrent HTTP requests

To keep at least one instance always running (no cold starts):
```bash
azd env set MIN_REPLICAS 1
azd up
```

Or modify `main.bicep`:
```bicep
minReplicas: 1
```

## Monitoring

Logs are sent to Log Analytics. View them:

```bash
# Stream live logs
az containerapp logs show \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --follow

# Query Log Analytics
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | order by TimeGenerated desc | take 50"
```

Or use **Azure Portal** > **Container App** > **Monitoring** > **Logs**.

## Cleanup

Remove all deployed resources:

```bash
# Using azd (recommended)
azd down

# Using Azure CLI
az group delete --name rg-<env-name> --yes --no-wait
```

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
az containerapp logs show \
  --name <container-app-name> \
  --resource-group <resource-group> \
  --type system
```

Common issues:
- **Port mismatch**: Ensure `containerPort` matches what the app listens on (default: 9000)
- **Missing env vars**: Check `ENABLE_AUTH`, `CLIENT_ID`, `TENANT_ID`

### OBO Token Exchange Fails

1. Verify federated credential is configured correctly
2. Check the managed identity principal ID matches
3. Ensure audience is `api://AzureADTokenExchange`
4. Verify issuer URL uses your tenant ID

### Image Pull Failures

1. Verify managed identity has `AcrPull` role on the registry
2. Check ACR exists and image tag is correct
3. Review container app system logs

### Authentication Issues

1. Verify `ENABLE_AUTH` is `true` in production
2. Check app registration has correct redirect URIs
3. Ensure API permissions are granted (User.Read for Graph)

### OAuth Metadata Returns Wrong Values

If `/.well-known/oauth-protected-resource` returns incorrect values:

1. **Resource shows `localhost`**: Set `RESOURCE_SERVER_URL` environment variable:
   ```bash
   azd env set RESOURCE_SERVER_URL "https://your-app.azurecontainerapps.io"
   azd provision
   ```

2. **Scopes use wrong ID (tenant ID instead of client ID)**: Verify `AZURE_CLIENT_ID` is set to your App Registration's **Application (Client) ID**, not the Tenant ID:
   ```bash
   # Check current value
   azd env get-values | grep CLIENT_ID

   # Fix if wrong
   azd env set AZURE_CLIENT_ID "your-correct-client-id"
   azd provision
   ```

3. **Cached responses**: Use cache-busting headers to verify:
   ```bash
   curl -H "Cache-Control: no-cache" \
     https://your-app/.well-known/oauth-protected-resource | jq .
   ```

See [Troubleshooting Guide](../src/docs/05-troubleshooting.md) for more solutions.
