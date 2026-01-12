// =============================================================================
// User-Assigned Managed Identity Module
// =============================================================================
// This managed identity is used for:
// 1. Pulling images from Azure Container Registry
// 2. Secretless OBO (On-Behalf-Of) flow with federated credentials
// =============================================================================

@description('The name of the Managed Identity')
param name string

@description('The Azure region for the resource')
param location string

@description('Tags to apply to the resource')
param tags object = {}

// =============================================================================
// Resources
// =============================================================================

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

// =============================================================================
// Outputs
// =============================================================================

@description('The resource ID of the Managed Identity')
output id string = managedIdentity.id

@description('The name of the Managed Identity')
output name string = managedIdentity.name

@description('The principal ID (Object ID) of the Managed Identity')
output principalId string = managedIdentity.properties.principalId

@description('The client ID of the Managed Identity')
output clientId string = managedIdentity.properties.clientId

@description('The tenant ID of the Managed Identity')
output tenantId string = managedIdentity.properties.tenantId
