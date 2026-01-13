# Troubleshooting

Common issues and solutions for the Demo MCP Server.

## Authentication Errors

### 401 Unauthorized - Token Validation Failed

**Symptoms**: All authenticated requests fail with 401.

**Common Causes**:

1. **Wrong Audience**
   - Ensure `AUDIENCE` matches your app's client ID
   - Check the `aud` claim in your token matches `CLIENT_ID`

2. **Wrong Issuer**
   - Ensure `ISSUER` matches your tenant
   - Format: `https://login.microsoftonline.com/{tenant-id}/v2.0`

3. **Expired Token**
   - Azure AD tokens typically expire in 1 hour
   - Get a fresh token and try again

**Debug**: Enable debug logging to see token validation details:
```bash
python server.py --debug
```

### AADSTS65001 - User Has Not Consented

**Symptoms**: OBO flow fails with consent error.

**Solution**:
1. Go to Azure Portal > App registrations > Your app
2. Navigate to API permissions
3. Ensure `Microsoft Graph > User.Read` is listed
4. Click "Grant admin consent" or have users consent individually

### OBO Failed - Token Expiring Soon

**Symptoms**: `RuntimeError: Assertion token expiring soon (< 5 minutes)`

**Cause**: The user's access token is about to expire.

**Solution**: 
- Re-authenticate to get a fresh token
- Ensure your client refreshes tokens before expiry

## Configuration Errors

### ConfigurationError - Missing Required Configuration

**Symptoms**: Server fails to start with missing config error.

**Solution**: Ensure all required environment variables are set:

```bash
ENABLE_AUTH=true
TENANT_ID=...
CLIENT_ID=...
CLIENT_SECRET=...  # or FEDERATED_CREDENTIAL_OID
JWKS_URI=...
ISSUER=...
AUDIENCE=...
```

### JWKS Fetch Failed

**Symptoms**: `RuntimeError: JWKS fetch failed`

**Common Causes**:

1. **Network Issues**
   - Ensure the server can reach Azure AD
   - Check firewall/proxy settings

2. **Wrong JWKS URI**
   - Verify `JWKS_URI` format: `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`

## OBO Flow Errors

### OBO Network Error

**Symptoms**: `RuntimeError: OBO network error`

**Solution**: Check network connectivity to Azure AD token endpoint.

### Missing access_token in Response

**Symptoms**: `RuntimeError: OBO response missing access_token`

**Common Causes**:

1. **Invalid Client Secret**
   - Verify `CLIENT_SECRET` is correct
   - Secrets expire - check if it needs renewal

2. **Wrong Scope**
   - Verify `GRAPH_SCOPE` is correct (default: `User.Read`)

## Federated Credential Errors

### IMDS Endpoint Not Available

**Symptoms**: Federated credential fails locally.

**Cause**: Federated credentials require Azure's Instance Metadata Service (IMDS), which is only available in Azure.

**Solution**: Use `CLIENT_SECRET` for local development.

## Common Token Claim Issues

### No User Identifier in Token

**Symptoms**: `ValueError: No user identifier found in token`

**Cause**: The token doesn't contain expected claims (`sub`, `oid`, `email`).

**Solution**: 
- Ensure the token is an access token (not ID token)
- Verify API permissions include profile claims

## VS Code Integration Issues

### MCP Client Can't Connect

**Checklist**:
1. Server is running and accessible
2. OAuth metadata endpoints respond correctly
3. Client has correct server URL configured

### Token Not Passed to Server

**Symptoms**: Authorization header is empty.

**Solution**:
- Ensure the MCP client is configured to authenticate
- Check that the client has the correct scopes

## Debug Checklist

1. **Enable debug logging**: `python mcp_server.py --debug`
2. **Check health endpoint**: `curl http://localhost:9000/health`
3. **Verify OAuth metadata**: `curl http://localhost:9000/.well-known/oauth-protected-resource`
4. **Decode your token**: Use [jwt.io](https://jwt.io) to inspect claims
5. **Check Azure AD logs**: Azure Portal > Azure AD > Sign-in logs

## Getting Help

If issues persist:

1. Check the [FastMCP documentation](https://github.com/jlowin/fastmcp)
2. Review [Azure AD token documentation](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)
3. Review [OBO flow documentation](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
