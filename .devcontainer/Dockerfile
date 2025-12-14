# Development Container for Game Scheduler
# Optimized for VS Code Dev Containers with full tooling
FROM python:3.13-slim

# Install system dependencies and development tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    postgresql-client \
    curl \
    git \
    vim \
    less \
    sudo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies (including dev dependencies if they exist)
RUN uv pip install --system .

# Create non-root user with sudo access for development
RUN groupadd --gid 1000 vscode && \
    useradd --uid 1000 --gid 1000 -m -s /bin/bash vscode && \
    echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/vscode && \
    chmod 0440 /etc/sudoers.d/vscode

# Set up workspace ownership
RUN chown -R vscode:vscode /app

# Create common directories with proper permissions
RUN mkdir -p \
    /home/vscode/.cache \
    /home/vscode/.vscode-server \
    /home/vscode/.vscode-server/extensions \
    /home/vscode/.vscode-server/bin && \
    chown -R vscode:vscode /home/vscode && \
    chmod -R 755 /home/vscode

USER vscode

# Default command (will be overridden by dev container)
CMD ["sleep", "infinity"]
