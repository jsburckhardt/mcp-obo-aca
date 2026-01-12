# Infrastructure Deployment Guide

This guide explains how to deploy the Demo MCP Server to Azure using Azure Developer CLI (azd) and the Bicep templates in this folder.

## Prerequisites

- **Azure CLI**: [Install Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
- **Azure Developer CLI (azd)**: [Install azd](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- **Docker**: [Install Docker](https://docs.docker.com/get-docker/) (for local builds)
- **Azure Subscription**: With permissions to create resources

## Architecture

The infrastructure deploys the following Azure resources:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Resource Group                            │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────────────────────┐   │
│  │  Log Analytics   │◄───│   Container Apps Environment      │   │
│  │    Workspace     │    │                                    │   │
│  └──────────────────┘    │  ┌──────────────────────────────┐ │   │
│                          │  │     Demo MCP Server          │ │   │
│  ┌──────────────────┐    │  │     Container App            │ │   │
│  │ User-Assigned    │────┤  │                              │ │   │
│  │ Managed Identity │    │  │  - OAuth 2.1 Auth            │ │   │
│  └──────────────────┘    │  │  - OBO Flow for Graph API    │ │   │
│           │              │  │  - Health Checks             │ │   │
│           │              │  └──────────────────────────────┘ │   │
│           ▼              └──────────────────────────────────────┘   │
│  ┌──────────────────┐                                            │
│  │ Azure Container  │◄── Container images pushed here            │
│  │    Registry      │                                            │
│  └──────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │    Azure AD / Entra  │
                    │                      │
                    │  - App Registration  │
                    │  - Federated Cred    │
                    │  - OAuth Tokens      │
                    └──────────────────────┘
```

## Bicep Template Structure

```
infra/
├── main.bicep                  # Entry point - orchestrates all modules
├── main.parameters.json        # Parameter values (uses azd env vars)
├── abbreviations.json          # Resource naming abbreviations
└── modules/
    ├── log-analytics.bicep     # Log Analytics Workspace
    ├── managed-identity.bicep  # User-Assigned Managed Identity
    ├── container-registry.bicep # Azure Container Registry
    ├── container-apps-environment.bicep # Container Apps Environment
    └── container-app.bicep     # Container App for MCP Server
```

## Quick Start with Azure Developer CLI (azd)

### 1. Initialize the Environment

```bash
cd src/demo_mcp_server

# Initialize azd (first time only)
azd init

# Or configure an existing environment
azd env new dev
```

### 2. Set Required Environment Variables

```bash
# Set your Azure AD app registration client ID
azd env set AZURE_CLIENT_ID "your-client-id-here"

# Optional: Set client secret (for local dev - prefer managed identity in prod)
azd env set AZURE_CLIENT_SECRET "your-client-secret-here"

# Optional: Disable auth for testing
azd env set ENABLE_AUTH false
```

### 3. Deploy Everything

```bash
# Provision infrastructure and deploy the app
azd up
```

This single command will:
1. Create all Azure resources (Container Registry, Container Apps, etc.)
2. Build the Docker image
3. Push it to Azure Container Registry
4. Deploy to Azure Container Apps

### 4. Configure Federated Credential

After deployment, you need to create a federated credential on your Azure AD app registration to enable secretless OBO flow:

1. Note the **Managed Identity Principal ID** from the deployment output
2. Go to Azure Portal > Azure AD > App Registrations > Your App
3. Go to **Certificates & secrets** > **Federated credentials** > **Add credential**
4. Select **Customer Managed Keys**
5. Enter the Managed Identity Principal ID
6. Add audience: `api://AzureADTokenExchange`

See [docs/02-azure-setup.md](docs/02-azure-setup.md) for detailed instructions.

## Manual Deployment with Azure CLI

If you prefer not to use azd, you can deploy manually:

### 1. Create Resource Group

```bash
az group create \
  --name rg-demo-mcp-server \
  --location eastus
```

### 2. Deploy Bicep Template

```bash
az deployment group create \
  --resource-group rg-demo-mcp-server \
  --template-file infra/main.bicep \
  --parameters \
    name=demo-mcp-server \
    clientId=your-client-id-here \
    enableAuth=true
```

### 3. Build and Push Container Image

```bash
# Get ACR login server from output
ACR_NAME=$(az deployment group show \
  --resource-group rg-demo-mcp-server \
  --name main \
  --query properties.outputs.containerRegistryName.value -o tsv)

ACR_LOGIN_SERVER=$(az acr show \
  --name $ACR_NAME \
  --query loginServer -o tsv)

# Login to ACR
az acr login --name $ACR_NAME

# Build and push
docker build -t $ACR_LOGIN_SERVER/demo-mcp-server:latest .
docker push $ACR_LOGIN_SERVER/demo-mcp-server:latest
```

### 4. Restart Container App

```bash
CA_NAME=$(az deployment group show \
  --resource-group rg-demo-mcp-server \
  --name main \
  --query properties.outputs.containerAppName.value -o tsv)

az containerapp update \
  --name $CA_NAME \
  --resource-group rg-demo-mcp-server
```

## Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | required | Base name for all resources |
| `location` | string | resource group location | Azure region |
| `clientId` | string | required | Azure AD app client ID |
| `clientSecret` | string | '' | Client secret (optional) |
| `tenantId` | string | subscription tenant | Azure AD tenant ID |
| `enableAuth` | bool | true | Enable OAuth authentication |
| `containerPort` | int | 9000 | Container port |
| `minReplicas` | int | 0 | Minimum container replicas |
| `maxReplicas` | int | 3 | Maximum container replicas |
| `containerCpuCores` | string | '0.5' | CPU cores per container |
| `containerMemory` | string | '1Gi' | Memory per container |

## Outputs

After deployment, the following outputs are available:

| Output | Description |
|--------|-------------|
| `containerRegistryLoginServer` | ACR login server URL |
| `containerAppFqdn` | Container App FQDN |
| `mcpServerUrl` | Full MCP server URL |
| `mcpEndpoint` | MCP protocol endpoint |
| `oauthMetadataUrl` | OAuth metadata endpoint |
| `managedIdentityPrincipalId` | Principal ID for federated credential |

Get outputs after deployment:

```bash
# Using azd
azd env get-values

# Using Azure CLI
az deployment group show \
  --resource-group rg-demo-mcp-server \
  --name main \
  --query properties.outputs
```

## Scaling

The Container App is configured with HTTP-based autoscaling:

- **Min replicas**: 0 (scales to zero when idle)
- **Max replicas**: 3
- **Scale trigger**: 100 concurrent requests

Modify in `main.bicep`:

```bicep
minReplicas: 1  // Always keep 1 instance running
maxReplicas: 10 // Allow up to 10 instances
```

## Monitoring

Logs are sent to Log Analytics Workspace. View logs:

```bash
# Using Azure CLI
az monitor log-analytics query \
  --workspace $WORKSPACE_ID \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerName_s == 'demo-mcp-server' | order by TimeGenerated desc | take 100"
```

Or use Azure Portal > Container App > Logs.

## Cleanup

Remove all deployed resources:

```bash
# Using azd
azd down

# Using Azure CLI
az group delete --name rg-demo-mcp-server --yes
```

## Troubleshooting

### Container Won't Start

Check container logs:
```bash
az containerapp logs show \
  --name $CA_NAME \
  --resource-group rg-demo-mcp-server \
  --follow
```

### Authentication Issues

1. Verify `ENABLE_AUTH` is set correctly
2. Check federated credential configuration
3. Ensure app registration permissions are correct

### Image Pull Failures

1. Verify managed identity has AcrPull role
2. Check ACR is accessible
3. Verify image tag exists

See [docs/05-troubleshooting.md](docs/05-troubleshooting.md) for more solutions.
