# AGENTS Guidelines for This Repository

This repository contains an MCP (Model Context Protocol) server with OAuth 2.1 authentication and On-Behalf-Of (OBO) flow, deployable to Azure Container Apps using Azure Developer CLI (azd). When working on this project interactively with an agent, please follow these guidelines.

## 1. Development Environment

* **Python Environment**: This is a Python 3.11+ project. Always work within the `src/` directory for server code.
* **Use Local Mode for Testing**: Run `python server.py --no-auth` during development to bypass authentication for faster iteration.
* **With Authentication**: Run `python server.py` to test with full OAuth 2.1 + OBO flow.
* **Environment Configuration**: Copy `src/.env.example` to `src/.env` and configure Azure AD settings before running with auth.

## 2. Development Server, **not** Production Build

* **Never run `azd up` during active development sessions.** This deploys to Azure and is for production deployment only.
* **Use local Python server** with `python server.py --no-auth` for rapid iteration and testing.
* For testing with authentication, ensure your `.env` file is properly configured with:
  - `AZURE_CLIENT_ID`
  - `AZURE_TENANT_ID`
  - `RESOURCE_ID` (Microsoft Graph API)

## 3. Testing and Validation

* **Run tests before committing**: `pytest tests/ -v`
* **Check server health**: `curl http://localhost:8000/health`
* **Test MCP endpoints**: Use the MCP protocol to test tools via `/mcp` endpoint
* **Verify auth flow**: Check token verification and OBO flow with `whoami` tool

## 4. Code Structure and Conventions

* **Authentication code**: Located in `src/auth/` (verifier.py, obo.py)
* **Business logic**: Add new tools in `src/services/`
* **Configuration**: Use `src/config/` for environment and settings
* **Infrastructure**: Bicep templates in `infra/` - only modify if changing Azure resources
* Follow existing patterns for token verification and OBO flows

## 5. Available MCP Tools

| Tool | Description | Auth Required |
|------|-------------|---------------|
| `greet_test` | Simple greeting | No |
| `get_mcp_server_status` | Server status info | No |
| `whoami` | User profile from Graph API | Yes (OBO) |

## 6. Useful Commands

| Command | Purpose |
|---------|---------|
| `python server.py --no-auth` | Start server without authentication (dev mode) |
| `python server.py` | Start server with OAuth 2.1 + OBO flow |
| `pytest tests/ -v` | Run test suite with verbose output |
| `azd up` | **Production deployment – _do not run during dev sessions_** |
| `azd env set AZURE_CLIENT_ID <id>` | Configure environment variables |
| `docker build -t mcp-server .` | Build container image (from src/ directory) |

## 7. Dependencies

* **Install dependencies**: `pip install -r src/requirements.txt`
* **Update dependencies**: Edit `src/requirements.txt` and re-run pip install
* Key dependencies:
  - `fastmcp` - MCP server framework
  - `msal` - Microsoft Authentication Library
  - `pyjwt`, `cryptography` - JWT token verification
  - `httpx` - HTTP client for Graph API calls

## 8. Azure Deployment Notes

* **Deployment is via azd**: Uses Bicep templates in `infra/`
* **Secretless architecture**: Uses Managed Identity with Federated Credentials
* **Post-deployment step required**: Configure federated credential on Azure AD app registration
* See `src/docs/02-azure-setup.md` for detailed deployment instructions

## 9. Documentation Structure

* `src/docs/01-introduction.md` - Overview and prerequisites
* `src/docs/02-azure-setup.md` - App registration and deployment
* `src/docs/03-server-implementation.md` - Code walkthrough
* `src/docs/04-running-and-testing.md` - Usage guide
* `src/docs/05-troubleshooting.md` - Common issues

## 10. Standards Compliance

This project implements:
- MCP Authorization Specification
- OAuth 2.1 (Draft 13)
- RFC 9728 - Protected Resource Metadata
- RFC 8707 - Resource Indicators
- RFC 8414 - Authorization Server Metadata

---

Following these guidelines ensures smooth agent-assisted development. When in doubt, use local mode (`--no-auth`) for faster iteration, and only test full auth flow when specifically working on authentication features.

## fs2 MCP Tools

Use flowspace tools for code exploration (see `.github/copilot-instructions.md`):
- `flowspace-tree(pattern=".")` - explore structure
- `flowspace-search(pattern="...", mode="semantic")` - find code
- `flowspace-get_node(node_id="...")` - get source code

## Rules

- Use conventional commits for commit messages. (https://www.conventionalcommits.org/en/v1.0.0/#specification)
  - always co-author your commits with the model's name.
- always write tests for new features or bug fixes.
- ensure code passes linting and tests before committing.
- document any new functionality or changes in the relevant documentation files. (src/docs/)
- do not commit till user has approved the changes.
- never use python virtual envrionments. we use devcontainers for environment management.
