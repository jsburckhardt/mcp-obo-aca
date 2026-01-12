#!/bin/bash
set -e

echo "🚀 Setting up development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "/home/vscode/.venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv /home/vscode/.venv
fi

# Activate virtual environment
source /home/vscode/.venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
cd /workspaces/mcp-obo-aca/src
uv pip install -r requirements.txt

# Install dev dependencies
uv pip install pytest pytest-asyncio ruff

# Copy .env.example if .env doesn't exist
if [ ! -f "/workspaces/mcp-obo-aca/src/.env" ]; then
    if [ -f "/workspaces/mcp-obo-aca/src/.env.example" ]; then
        echo "📄 Creating .env from .env.example..."
        cp /workspaces/mcp-obo-aca/src/.env.example /workspaces/mcp-obo-aca/src/.env
    fi
fi

echo "✅ Development environment setup complete!"
echo ""
echo "To run the MCP server:"
echo "  cd src && python server.py --no-auth"
echo ""
echo "To run tests:"
echo "  cd src && pytest tests/ -v"
echo ""
echo "To deploy to Azure:"
echo "  azd up"
