# Demo MCP Server - Justfile
# https://github.com/casey/just

# Default recipe - show available commands
default:
    @just --list

# =============================================================================
# Development
# =============================================================================

# Start server in development mode (no auth)
dev:
    cd src && python server.py --no-auth

# Start server with full OAuth 2.1 + OBO authentication
run:
    cd src && python server.py

# Start server with custom host and port
serve host="127.0.0.1" port="9000":
    cd src && python server.py --host {{ host }} --port {{ port }}

# Start server in debug mode
debug:
    cd src && DEBUG=true python server.py --no-auth

# =============================================================================
# Testing
# =============================================================================

# Run all tests
test:
    cd src && pytest tests/ -v

# Run tests with coverage
test-cov:
    cd src && pytest tests/ -v --cov=. --cov-report=term-missing

# Run only unit tests
test-unit:
    cd src && pytest tests/ -v -m unit

# Run only integration tests
test-integration:
    cd src && pytest tests/ -v -m integration

# Run tests matching a pattern
test-match pattern:
    cd src && pytest tests/ -v -k "{{ pattern }}"

# =============================================================================
# Dependencies
# =============================================================================

# Install dependencies
install:
    pip install -r src/requirements.txt

# Install development dependencies
install-dev:
    pip install -r src/requirements-dev.txt

# Update dependencies (edit requirements.txt first)
update-deps:
    pip install -r src/requirements.txt --upgrade

# =============================================================================
# Health & Status
# =============================================================================

# Check server health (assumes server is running on default port)
health port="9000":
    curl -s http://localhost:{{ port }}/health | python -m json.tool

# Get OAuth protected resource metadata
oauth-metadata port="9000":
    curl -s http://localhost:{{ port }}/.well-known/oauth-protected-resource | python -m json.tool

# =============================================================================
# Docker
# =============================================================================

# Build Docker image
docker-build:
    docker build -t mcp-server -f src/Dockerfile src/

# Run Docker container
docker-run:
    docker run -p 9000:9000 --env-file src/.env mcp-server

# Run Docker container in dev mode (no auth)
docker-run-dev:
    docker run -p 9000:9000 -e ENABLE_AUTH=false mcp-server

# Build and run Docker container
docker-up: docker-build docker-run

# Stop all running mcp-server containers
docker-stop:
    docker ps -q --filter ancestor=mcp-server | xargs -r docker stop

# =============================================================================
# Azure Deployment (Production)
# =============================================================================

# Initialize Azure Developer CLI
azd-init:
    azd init

# Provision Azure infrastructure
azd-provision:
    azd provision

# Deploy to Azure Container Apps
azd-deploy:
    azd deploy

# Full deployment (provision + deploy) - USE WITH CAUTION
azd-up:
    @echo "⚠️  Warning: This will deploy to Azure. Are you sure? (Ctrl+C to cancel)"
    @sleep 3
    azd up

# Show Azure deployment status
azd-status:
    azd show

# Set Azure environment variable
azd-env-set name value:
    azd env set {{ name }} {{ value }}

# List Azure environment variables
azd-env-list:
    azd env get-values

# =============================================================================
# Code Quality
# =============================================================================

# Format Python code with black
fmt:
    black src/

# Check formatting without making changes
fmt-check:
    black src/ --check

# Lint with ruff
lint:
    ruff check src/

# Lint and auto-fix
lint-fix:
    ruff check src/ --fix

# Type check with mypy
typecheck:
    mypy src/ --ignore-missing-imports

# Run all quality checks
check: fmt-check lint typecheck

# =============================================================================
# Setup & Configuration
# =============================================================================

# Setup local development environment
setup:
    @echo "Setting up development environment..."
    pip install -r src/requirements.txt
    pip install pytest pytest-asyncio cryptography black ruff mypy
    @if [ ! -f src/.env ]; then \
        cp src/.env.example src/.env; \
        echo "Created src/.env from .env.example - please configure it"; \
    else \
        echo "src/.env already exists"; \
    fi
    @echo "Setup complete!"

# Create .env from example
env-init:
    cp src/.env.example src/.env
    @echo "Created src/.env - please edit with your Azure AD settings"

# =============================================================================
# Documentation
# =============================================================================

# Open documentation in browser (macOS)
docs-open:
    open src/docs/01-introduction.md

# List all documentation files
docs-list:
    @ls -la src/docs/*.md

# =============================================================================
# Utilities
# =============================================================================

# Clean Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    @echo "Cleaned cache files"

# Show project structure
tree:
    @tree -I '__pycache__|*.pyc|.git|.pytest_cache|.mypy_cache|.ruff_cache' -L 3

# Watch for changes and run tests (requires entr)
watch-test:
    find src -name "*.py" | entr -c just test
