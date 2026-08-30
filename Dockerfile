FROM python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast deterministic dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create non-root application user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /home/appuser/.youtube_research_mcp && \
    chown -R appuser:appuser /home/appuser

# Copy configuration and source code
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies into system Python
RUN uv pip install --system --no-cache -e . && \
    chown -R appuser:appuser /app

# Set default production environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_SERVER_NAME="youtube-research-mcp"
ENV MCP_HOST="0.0.0.0"
ENV MCP_PORT="8000"
ENV MCP_TRANSPORT="http"
ENV CACHE_BACKEND="sqlite"
ENV CACHE_DB_PATH="/home/appuser/.youtube_research_mcp/cache.db"
ENV LOG_LEVEL="INFO"

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["youtube-research-mcp", "--transport", "http", "--host", "0.0.0.0"]

