# CI/CD Pipeline

This document describes the Continuous Integration and Continuous Deployment (CI/CD) setup for the Demo MCP Server project.

## Overview

The project uses GitHub Actions for CI/CD with two workflows:

| Workflow | File | Purpose |
|----------|------|---------|
| **CI** | `.github/workflows/ci.yml` | Linting, formatting, type checking, and testing |
| **Deploy** | `.github/workflows/deploy.yml` | Deploy to Azure Container Apps via `azd` |

## CI Pipeline

### Triggers

The CI workflow runs on:
- **Pull requests** to the `main` branch
- **Pushes** to `main` and `feat/*` branches

### Steps

1. **Checkout code** - Clones the repository
2. **Set up Python 3.11** - Installs Python runtime
3. **Cache pip dependencies** - Speeds up subsequent runs
4. **Install dependencies** - Installs `requirements.txt` and `requirements-dev.txt`
5. **Lint with ruff** - Static code analysis for errors and style issues
6. **Check formatting with black** - Ensures consistent code formatting
7. **Type check with mypy** - Static type analysis
8. **Run tests with coverage** - Executes pytest with coverage reporting

### Running Locally

You can run the same checks locally using the justfile:

```bash
# Run all checks
just check

# Individual checks
just lint          # Run ruff
just fmt-check     # Check black formatting
just typecheck     # Run mypy
just test          # Run pytest
just test-cov      # Run pytest with coverage
```

## Deploy Pipeline

### Triggers

The Deploy workflow runs automatically when:
- The **CI workflow succeeds** on the `main` branch

This ensures that only tested and validated code is deployed to Azure.

### Steps

1. **Checkout code** - Clones the repository
2. **Install Azure Developer CLI** - Installs `azd`
3. **Log in with Azure** - Authenticates using OIDC (Federated Credentials)
4. **Provision Infrastructure** - Runs `azd provision --no-prompt`
5. **Deploy Application** - Runs `azd deploy --no-prompt`

## GitHub Repository Configuration

### Required Variables

Configure these in your GitHub repository:
**Settings → Secrets and variables → Actions → Variables**

| Variable | Description | Example |
|----------|-------------|---------|
| `AZURE_CLIENT_ID` | Azure AD app registration client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_TENANT_ID` | Azure AD tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_ENV_NAME` | Environment name for azd | `prod` |
| `AZURE_LOCATION` | Azure region for resources | `eastus` |

### Setting Variables via GitHub CLI

```bash
# Set repository variables
gh variable set AZURE_CLIENT_ID --body "your-client-id"
gh variable set AZURE_TENANT_ID --body "your-tenant-id"
gh variable set AZURE_SUBSCRIPTION_ID --body "your-subscription-id"
gh variable set AZURE_ENV_NAME --body "prod"
gh variable set AZURE_LOCATION --body "eastus"
```

## Azure AD Federated Credential Setup

The deploy workflow uses OpenID Connect (OIDC) for passwordless authentication to Azure. This requires configuring a federated credential on your Azure AD app registration.

### Step 1: Get Your Repository Details

Your repository: `jsburckhardt/mcp-obo-aca`

### Step 2: Configure Federated Credential

1. Go to **Azure Portal** → **Azure Active Directory** → **App registrations**
2. Select your app registration (the one with `AZURE_CLIENT_ID`)
3. Navigate to **Certificates & secrets** → **Federated credentials**
4. Click **Add credential**
5. Select **GitHub Actions deploying Azure resources**
6. Configure:

| Field | Value |
|-------|-------|
| Organization | `jsburckhardt` |
| Repository | `mcp-obo-aca` |
| Entity type | `Branch` |
| Branch name | `main` |
| Name | `github-actions-main` |

7. Click **Add**

### Using Azure CLI

```bash
# Create federated credential for main branch
az ad app federated-credential create \
  --id <app-object-id> \
  --parameters '{
    "name": "github-actions-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:jsburckhardt/mcp-obo-aca:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                                │
│                     jsburckhardt/mcp-obo-aca                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Push to feat/*  ──────┐                                                │
│                        │                                                │
│  Push to main    ──────┼──────►  ┌─────────────────────┐                │
│                        │         │      CI Workflow     │                │
│  PR to main      ──────┘         │  (.github/workflows/ │                │
│                                  │   ci.yml)            │                │
│                                  ├─────────────────────┤                │
│                                  │ • Lint (ruff)       │                │
│                                  │ • Format (black)    │                │
│                                  │ • Type check (mypy) │                │
│                                  │ • Test (pytest)     │                │
│                                  │ • Coverage report   │                │
│                                  └──────────┬──────────┘                │
│                                             │                           │
│                                             │ (on success, main only)   │
│                                             ▼                           │
│                                  ┌─────────────────────┐                │
│                                  │   Deploy Workflow   │                │
│                                  │  (.github/workflows/ │                │
│                                  │   deploy.yml)        │                │
│                                  ├─────────────────────┤                │
│                                  │ • Azure OIDC login  │                │
│                                  │ • azd provision     │                │
│                                  │ • azd deploy        │                │
│                                  └──────────┬──────────┘                │
│                                             │                           │
│                                             ▼                           │
│                                  ┌─────────────────────┐                │
│                                  │  Azure Container    │                │
│                                  │       Apps          │                │
│                                  └─────────────────────┘                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### CI Failures

#### Linting Errors (ruff)
```bash
# Auto-fix linting issues
just lint-fix
# Or: ruff check src/ --fix
```

#### Formatting Errors (black)
```bash
# Auto-format code
just fmt
# Or: black src/
```

#### Type Errors (mypy)
Review the error messages and add type hints or `# type: ignore` comments where appropriate.

#### Test Failures
```bash
# Run tests locally with verbose output
just test
# Or: cd src && pytest tests/ -v
```

### Deploy Failures

#### "AZURE_CLIENT_ID is not set"
Ensure you've configured the repository variables. See [Required Variables](#required-variables).

#### "AADSTS700024: Client assertion is not within its valid time range"
The federated credential subject doesn't match. Verify:
- Repository name is correct
- Branch name matches (should be `main`)
- Entity type is `Branch`

#### "azd provision failed"
Check the Azure subscription has sufficient quota and permissions. Review the deployment logs in GitHub Actions for specific error messages.

### Manual Deployment

If you need to deploy manually (bypassing CI/CD):

```bash
# Login to Azure
azd auth login

# Set environment
azd env select prod

# Deploy
azd up
```

## Security Considerations

1. **OIDC Authentication**: Uses federated credentials instead of storing secrets in GitHub
2. **Minimal Permissions**: Workflows request only necessary permissions
3. **Branch Protection**: Consider enabling branch protection rules for `main`
4. **Environment Secrets**: Sensitive values are stored as GitHub variables/secrets, not in code

## Related Documentation

- [Azure Setup](02-azure-setup.md) - App registration and Azure configuration
- [Running and Testing](04-running-and-testing.md) - Local development guide
- [Azure Developer CLI Docs](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/)
- [GitHub Actions OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
