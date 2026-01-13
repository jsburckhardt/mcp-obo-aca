// =============================================================================
// Container Apps Environment Module
// =============================================================================

@description('The name of the Container Apps Environment')
param name string

@description('The Azure region for the resource')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('The resource ID of the Log Analytics Workspace')
param logAnalyticsWorkspaceId string

@description('Enable zone redundancy')
param zoneRedundant bool = false

// =============================================================================
// Resources
// =============================================================================

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    zoneRedundant: zoneRedundant
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// =============================================================================
// Outputs
// =============================================================================

@description('The resource ID of the Container Apps Environment')
output id string = containerAppsEnvironment.id

@description('The name of the Container Apps Environment')
output name string = containerAppsEnvironment.name

@description('The default domain of the Container Apps Environment')
output defaultDomain string = containerAppsEnvironment.properties.defaultDomain

@description('The static IP of the Container Apps Environment')
output staticIp string = containerAppsEnvironment.properties.staticIp
