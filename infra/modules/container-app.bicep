// =============================================================================
// Container App Module
// =============================================================================

@description('The name of the Container App')
param name string

@description('The Azure region for the resource')
param location string

@description('Tags to apply to the resource')
param tags object = {}

@description('The resource ID of the Container Apps Environment')
param containerAppsEnvironmentId string

@description('The login server of the Container Registry')
param containerRegistryLoginServer string

@description('The container image name (without registry prefix)')
param containerImageName string

@description('The container image tag')
param containerImageTag string

@description('The port the container listens on')
param containerPort int = 9000

@description('The resource ID of the managed identity')
param managedIdentityId string

@description('The client ID of the managed identity (reserved for future use)')
#disable-next-line no-unused-params
param managedIdentityClientId string

@description('The principal ID of the managed identity (reserved for future use)')
#disable-next-line no-unused-params
param managedIdentityPrincipalId string

@description('Environment variables for the container')
param envVars array = []

@description('Secret environment variables for the container')
param secretEnvVars array = []

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

// Build secrets array from secretEnvVars
var secrets = [for secret in secretEnvVars: {
  name: secret.secretName
  value: secret.secretValue
}]

// Build environment variables including secret references
var secretEnvReferences = [for secret in secretEnvVars: {
  name: secret.name
  secretRef: secret.secretName
}]

var allEnvVars = concat(envVars, secretEnvReferences)

// =============================================================================
// Resources
// =============================================================================

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    workloadProfileName: 'Consumption'
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'http'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          exposeHeaders: ['*']
          maxAge: 3600
        }
      }
      registries: [
        {
          server: containerRegistryLoginServer
          identity: managedIdentityId
        }
      ]
      secrets: secrets
    }
    template: {
      containers: [
        {
          name: containerImageName
          image: '${containerRegistryLoginServer}/${containerImageName}:${containerImageTag}'
          resources: {
            cpu: json(containerCpuCores)
            memory: containerMemory
          }
          env: allEnvVars
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: containerPort
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// =============================================================================
// Outputs
// =============================================================================

@description('The resource ID of the Container App')
output id string = containerApp.id

@description('The name of the Container App')
output name string = containerApp.name

@description('The FQDN of the Container App')
output fqdn string = containerApp.properties.configuration.ingress.fqdn

@description('The latest revision FQDN of the Container App')
output latestRevisionFqdn string = containerApp.properties.latestRevisionFqdn
