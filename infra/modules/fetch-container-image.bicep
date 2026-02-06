// =============================================================================
// Fetch Container Image Module
// =============================================================================
// Retrieves the current container image from an existing Container App.
// Used during re-provisioning to preserve the deployed image reference.
// On first deployment (exists=false), returns an empty array so the caller
// can fall back to a placeholder image.
// =============================================================================

@description('Whether the Container App already exists')
param exists bool

@description('The name of the Container App')
param name string

resource existingApp 'Microsoft.App/containerApps@2024-03-01' existing = if (exists) {
  name: name
}

@description('The containers array from the existing app, or empty if it does not exist')
output containers array = exists ? existingApp!.properties.template.containers : []
