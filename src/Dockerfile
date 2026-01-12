FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye AS base
WORKDIR /app

FROM base AS builder

# Copy uv binaries from astral-sh image
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Copy lock and project files first for caching
COPY pyproject.toml /app/

# Create requirements file for pip-based installation
COPY requirements.txt /app/

# Install dependencies using pip (simpler for demo)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/demo_mcp_server
WORKDIR /app/demo_mcp_server

# Final stage
FROM base

WORKDIR /app/demo_mcp_server
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Add app directory to Python path
ENV PYTHONPATH="/app/demo_mcp_server:${PYTHONPATH}"

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app
WORKDIR /app/demo_mcp_server

# Expose port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Run script
CMD ["python", "server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9000"]
