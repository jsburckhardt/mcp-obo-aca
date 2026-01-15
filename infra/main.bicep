// =============================================================================
// Demo MCP Server Infrastructure - Main Bicep Template
// =============================================================================
// This template deploys:
// - Azure Container Registry (ACR)
// - Azure Container Apps Environment
// - Azure Container App for the MCP Server
// - User-Assigned Managed Identity (for secretless OBO flow)
// - Log Analytics Workspace
// =============================================================================

targetScope = 'resourceGroup'

// =============================================================================
// Parameters
// =============================================================================

@description('The base name for all resources')
param name string

@description('The Azure region for all resources')
param location string = resourceGroup().location

@description('Tags to apply to all resources')
param tags object = {}

@description('The container image name (without registry prefix)')
param containerImageName string = 'demo-mcp-server'

@description('The container image tag')
param containerImageTag string = 'latest'

@description('The Azure AD tenant ID for authentication')
param tenantId string = subscription().tenantId

@description('The Azure AD client ID (Application ID) for the MCP server app registration')
param clientId string

@description('The Azure AD client secret (optional - use managed identity in production)')
@secure()
param clientSecret string = ''

@description('Enable authentication (set to false for testing)')
param enableAuth bool = true

@description('The port the container listens on')
param containerPort int = 9000

@description('The canonical resource server URL (set after first deployment with the Container App FQDN)')
param resourceServerUrl string = ''

@description('Minimum number of replicas')
param minReplicas int = 0

@description('Maximum number of replicas')
param maxReplicas int = 3

@description('CPU cores for the container')
param containerCpuCores string = '0.5'

@description('Memory for the container in Gi')
param containerMemory string = '1Gi'

// =============================================================================
// Variables
// =============================================================================

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, resourceGroup().id, name, location))
var containerAppName = '${abbrs.appContainerApp}${name}-${resourceToken}'
var containerRegistryName = '${abbrs.containerRegistry}${replace(name, '-', '')}${resourceToken}'
var containerAppsEnvironmentName = '${abbrs.appContainerAppsEnvironment}${name}-${resourceToken}'
var logAnalyticsWorkspaceName = '${abbrs.logAnalyticsWorkspace}${name}-${resourceToken}'
var managedIdentityName = '${abbrs.userAssignedIdentity}${name}-${resourceToken}'

// =============================================================================
// Modules
// =============================================================================

// Log Analytics Workspace
module logAnalytics './modules/log-analytics.bicep' = {
  name: 'log-analytics'
  params: {
    name: logAnalyticsWorkspaceName
    location: location
    tags: tags
  }
}

// User-Assigned Managed Identity (for secretless OBO flow)
module managedIdentity './modules/managed-identity.bicep' = {
  name: 'managed-identity'
  params: {
    name: managedIdentityName
    location: location
    tags: tags
  }
}

// Azure Container Registry
module containerRegistry './modules/container-registry.bicep' = {
  name: 'container-registry'
  params: {
    name: containerRegistryName
    location: location
    tags: tags
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
  }
}

// Container Apps Environment
module containerAppsEnvironment './modules/container-apps-environment.bicep' = {
  name: 'container-apps-environment'
  params: {
    name: containerAppsEnvironmentName
    location: location
    tags: tags
    logAnalyticsWorkspaceId: logAnalytics.outputs.id
  }
}

// Container App - Demo MCP Server
module containerApp './modules/container-app.bicep' = {
  name: 'container-app'
  params: {
    name: containerAppName
    location: location
    tags: union(tags, { 'azd-service-name': 'demo-mcp-server' })
    containerAppsEnvironmentId: containerAppsEnvironment.outputs.id
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    containerImageName: containerImageName
    containerImageTag: containerImageTag
    containerPort: containerPort
    managedIdentityId: managedIdentity.outputs.id
    managedIdentityClientId: managedIdentity.outputs.clientId
    managedIdentityPrincipalId: managedIdentity.outputs.principalId
    minReplicas: minReplicas
    maxReplicas: maxReplicas
    containerCpuCores: containerCpuCores
    containerMemory: containerMemory
    // Environment variables for the MCP server
    envVars: [
      {
        name: 'HOST'
        value: '0.0.0.0'
      }
      {
        name: 'PORT'
        value: string(containerPort)
      }
      {
        name: 'ENABLE_AUTH'
        value: string(enableAuth)
      }
      {
        name: 'TENANT_ID'
        value: tenantId
      }
      {
        name: 'CLIENT_ID'
        value: clientId
      }
      {
        name: 'JWKS_URI'
        value: '${environment().authentication.loginEndpoint}${tenantId}/discovery/v2.0/keys'
      }
      {
        name: 'ISSUER'
        value: '${environment().authentication.loginEndpoint}${tenantId}/v2.0'
      }
      {
        name: 'AUDIENCE'
        value: clientId
      }
      {
        name: 'GRAPH_SCOPE'
        value: 'User.Read'
      }
      {
        name: 'FEDERATED_CREDENTIAL_OID'
        value: managedIdentity.outputs.principalId
      }
      {
        name: 'SERVER_NAME'
        value: 'DemoMcpServer'
      }
      {
        name: 'DEBUG'
        value: 'false'
      }
      {
        name: 'RESOURCE_SERVER_URL'
        value: resourceServerUrl
      }
    ]
    // Only add client secret if provided (for local dev scenarios)
    secretEnvVars: !empty(clientSecret) ? [
      {
        name: 'CLIENT_SECRET'
        secretName: 'client-secret'
        secretValue: clientSecret
      }
    ] : []
  }
}

// =============================================================================
// Outputs
// =============================================================================

@description('The name of the Container Registry')
output containerRegistryName string = containerRegistry.outputs.name

@description('The login server of the Container Registry')
output containerRegistryLoginServer string = containerRegistry.outputs.loginServer

@description('The Azure Container Registry endpoint (used by azd for deployment)')
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer

@description('The name of the Container App')
output containerAppName string = containerApp.outputs.name

@description('The FQDN of the Container App')
output containerAppFqdn string = containerApp.outputs.fqdn

@description('The URL of the MCP Server')
output mcpServerUrl string = 'https://${containerApp.outputs.fqdn}'

@description('The MCP endpoint URL')
output mcpEndpoint string = 'https://${containerApp.outputs.fqdn}/mcp'

@description('The OAuth metadata URL')
output oauthMetadataUrl string = 'https://${containerApp.outputs.fqdn}/.well-known/oauth-protected-resource'

@description('The Managed Identity Principal ID (use this for federated credential configuration)')
output managedIdentityPrincipalId string = managedIdentity.outputs.principalId

@description('The Managed Identity Client ID')
output managedIdentityClientId string = managedIdentity.outputs.clientId

@description('The Log Analytics Workspace ID')
output logAnalyticsWorkspaceId string = logAnalytics.outputs.id
