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
    locales \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# Set locale environment variables
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Install nektos/act for local GitHub Actions testing
ARG ACT_VERSION=0.2.83
RUN curl -L "https://github.com/nektos/act/releases/download/v${ACT_VERSION}/act_Linux_x86_64.tar.gz" \
    | tar xz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/act

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies including dev dependencies
RUN uv pip install --system . && \
    uv pip install --system --group dev

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

# Configure bash to start in workspace directory and enable git wrapper
RUN echo 'if [ -n "$REMOTE_CONTAINERS" ] && [ -d "/workspaces" ]; then' >> /home/vscode/.bashrc_devcontainer && \
    echo '    cd /workspaces/game-scheduler 2>/dev/null || cd $(find /workspaces -maxdepth 1 -type d | tail -1) 2>/dev/null || true' >> /home/vscode/.bashrc_devcontainer && \
    echo 'fi' >> /home/vscode/.bashrc_devcontainer && \
    echo '' >> /home/vscode/.bashrc_devcontainer && \
    echo '# Enable git wrapper for quality check enforcement' >> /home/vscode/.bashrc_devcontainer && \
    echo 'if [ -d "${WORKSPACE_ROOT:-/workspaces/game-scheduler}/scripts/wrappers" ]; then' >> /home/vscode/.bashrc_devcontainer && \
    echo '    export PATH="${WORKSPACE_ROOT:-/workspaces/game-scheduler}/scripts/wrappers:$PATH"' >> /home/vscode/.bashrc_devcontainer && \
    echo 'fi' >> /home/vscode/.bashrc_devcontainer && \
    chown vscode:vscode /home/vscode/.bashrc_devcontainer

USER vscode

# Default command (will be overridden by dev container)
CMD ["sleep", "infinity"]
