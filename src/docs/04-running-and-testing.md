# Running and Testing

This guide shows how to run and test the Demo MCP Server.

## Environment Setup

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` with your Azure AD values:

```bash
ENABLE_AUTH=true
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret
JWKS_URI=https://login.microsoftonline.com/your-tenant-id/discovery/v2.0/keys
ISSUER=https://login.microsoftonline.com/your-tenant-id/v2.0
AUDIENCE=your-client-id
GRAPH_SCOPE=User.Read
```

## Running the Server

### Without Authentication (Testing)

```bash
python server.py --no-auth
```

Output:
```
Starting Demo MCP Server
Transport: STREAMABLE-HTTP
Debug: False
Auth: Disabled
Host: 127.0.0.1
Port: 9000
--------------------------------------------------
```

### With Authentication

```bash
python server.py
```

### With Debug Logging

```bash
python server.py --debug
```

### Custom Host/Port

```bash
python server.py --host 0.0.0.0 --port 8080
```

## Testing Endpoints

### Health Check

```bash
curl http://localhost:9000/health
```

Response:
```json
{"status": "healthy", "service": "demo-mcp-server"}
```

### OAuth Protected Resource Metadata (RFC 9728)

```bash
curl http://localhost:9000/.well-known/oauth-protected-resource
```

Response:
```json
{
  "resource": "http://localhost:9000",
  "bearer_methods_supported": ["header"],
  "authorization_servers": ["https://login.microsoftonline.com/{tenant}/v2.0"],
  "scopes_supported": ["api://{client-id}/access_as_user", ...]
}
```

### Authorization Server Metadata

```bash
curl http://localhost:9000/.well-known/oauth-authorization-server
```

## Testing Tools (No Auth)

With `--no-auth`, you can test tools without a token:

### greet_test

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "greet_test",
      "arguments": {"name": "World"}
    },
    "id": 1
  }'
```

### get_mcp_server_status

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_mcp_server_status",
      "arguments": {}
    },
    "id": 1
  }'
```

## Testing Tools (With Auth)

When auth is enabled, you need a valid Azure AD token:

```bash
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {your-access-token}" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "whoami",
      "arguments": {}
    },
    "id": 1
  }'
```

## Getting a Test Token

Use the Azure CLI to get a token:

```bash
# Login first
az login

# Get a token for your app
az account get-access-token \
  --resource api://{your-client-id} \
  --query accessToken -o tsv
```

Or use MSAL in Python:

```python
from msal import PublicClientApplication

app = PublicClientApplication(
    client_id="{client-id}",
    authority="https://login.microsoftonline.com/{tenant-id}"
)

result = app.acquire_token_interactive(
    scopes=["api://{client-id}/access_as_user"]
)
print(result["access_token"])
```

## Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio cryptography

# Run tests
pytest tests/ -v
```

## Docker

Build and run with Docker:

```bash
# Build
docker build -t demo-mcp-server .

# Run
docker run -p 9000:9000 --env-file .env demo-mcp-server
```

## Next Steps

If you encounter issues, see [05-troubleshooting.md](05-troubleshooting.md).
