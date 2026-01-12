# Azure AD Setup

This guide walks you through configuring Azure AD (Entra ID) for the Demo MCP Server.

## Step 1: Create an App Registration

1. Go to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: `Demo MCP Server`
   - **Supported account types**: Choose based on your needs (typically "Single tenant")
   - **Redirect URI**: Leave blank for now
5. Click **Register**

## Step 2: Note Your IDs

After registration, note down:

- **Application (client) ID**: This is your `CLIENT_ID`
- **Directory (tenant) ID**: This is your `TENANT_ID`

## Step 3: Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Delegated permissions**
5. Add: `User.Read`
6. Click **Add permissions**

For the OBO flow to work, users will need to consent to these permissions. Optionally, click **Grant admin consent** to pre-approve for all users.

## Step 4: Create a Client Secret

For local development:

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description and choose an expiry
4. Click **Add**
5. **Copy the secret value immediately** (it won't be shown again)

This is your `CLIENT_SECRET`.

## Step 5: Expose an API (Optional)

If you want clients to request specific scopes:

1. Go to **Expose an API**
2. Click **Set** next to Application ID URI
3. Accept the default (`api://{client-id}`) or customize
4. Click **Add a scope**
5. Create scopes like:
   - `access_as_user`
   - `MCP.Tools`
   - `MCP.Resources`

## Step 6: Pre-authorize Client Applications

To allow MCP clients (like VS Code) without user consent prompts:

1. Go to **Expose an API**
2. Click **Add a client application**
3. Add the client ID of your MCP client
4. Select the scopes you want to authorize

### Common MCP Client IDs

- VS Code: Check the extension documentation for the client ID

## Environment Variables

After setup, you'll have these values for your `.env` file:

```bash
TENANT_ID=your-tenant-id-here
CLIENT_ID=your-client-id-here
CLIENT_SECRET=your-client-secret-here
JWKS_URI=https://login.microsoftonline.com/your-tenant-id/discovery/v2.0/keys
ISSUER=https://login.microsoftonline.com/your-tenant-id/v2.0
AUDIENCE=your-client-id-here
```

## Federated Identity Credentials (Production)

For production deployments in Azure, consider using Federated Identity Credentials instead of client secrets:

1. Create a User-Assigned Managed Identity in Azure
2. In your app registration, go to **Certificates & secrets**
3. Click **Federated credentials** > **Add credential**
4. Choose **Managed identity**
5. Select your managed identity
6. Set the audience to `api://AzureADTokenExchange`

Then use `FEDERATED_CREDENTIAL_OID` instead of `CLIENT_SECRET`.

## Next Steps

Continue to [03-server-implementation.md](03-server-implementation.md) for a code walkthrough.
