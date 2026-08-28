FROM python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for ultra-fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy configuration and pyproject
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies into system Python
RUN uv pip install --system -e .

# Create cache directory
RUN mkdir -p /root/.youtube_research_mcp

ENV MCP_SERVER_NAME="youtube-research-mcp"
ENV CACHE_BACKEND="sqlite"
ENV CACHE_DB_PATH="/root/.youtube_research_mcp/cache.db"
ENV LOG_LEVEL="INFO"

EXPOSE 8000

CMD ["youtube-research-mcp"]
