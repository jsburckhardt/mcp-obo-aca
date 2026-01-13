// =============================================================================
// Log Analytics Workspace Module
// =============================================================================

@description('The name of the Log Analytics Workspace')
param name string

@description('The Azure region for the resource')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('The SKU of the Log Analytics Workspace')
@allowed([
  'Free'
  'PerGB2018'
  'PerNode'
  'Premium'
  'Standalone'
  'Standard'
])
param sku string = 'PerGB2018'

@description('Retention period in days')
param retentionInDays int = 30

// =============================================================================
// Resources
// =============================================================================

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: sku
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: -1
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// =============================================================================
// Outputs
// =============================================================================

@description('The resource ID of the Log Analytics Workspace')
output id string = logAnalyticsWorkspace.id

@description('The name of the Log Analytics Workspace')
output name string = logAnalyticsWorkspace.name

@description('The customer ID (Workspace ID) of the Log Analytics Workspace')
output customerId string = logAnalyticsWorkspace.properties.customerId
