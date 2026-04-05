# Development Container for Game Scheduler
# Optimized for VS Code Dev Containers with full tooling
FROM ubuntu:24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install prerequisites for adding PPAs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gnupg \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Add git-core PPA (git 2.48+ for relative worktree path support) and deadsnakes PPA (Python 3.13)
RUN add-apt-repository -y ppa:git-core/ppa \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update

# Install system dependencies and development tools
RUN apt-get install -y --no-install-recommends \
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
    python3.13 \
    python3.13-venv \
    python3.13-dev \
    && sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with sudo access for development
# ubuntu:24.04 ships a default 'ubuntu' user at UID/GID 1000; remove it first.
RUN userdel -r ubuntu 2>/dev/null || true \
    && groupdel ubuntu 2>/dev/null || true \
    && groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid 1000 -m -s /bin/bash vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode

# Set locale environment variables
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Set python3.13 as the default python3/python and bootstrap pip
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.13 1 \
    && python3.13 -m ensurepip --upgrade

# Install nektos/act for local GitHub Actions testing
ARG ACT_VERSION=0.2.87
RUN curl -L "https://github.com/nektos/act/releases/download/v${ACT_VERSION}/act_Linux_x86_64.tar.gz" \
    | tar xz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/act

WORKDIR /app

# Install uv for dependency management
ARG UV_VERSION=0.11.3
RUN python3.13 -m pip install --no-cache-dir uv==${UV_VERSION}

# Create common directories with proper permissions
RUN mkdir -p \
    /home/vscode/.cache \
    /home/vscode/.vscode-server \
    /home/vscode/.vscode-server/extensions \
    /home/vscode/.vscode-server/bin && \
    chown -R vscode:vscode /home/vscode && \
    chmod -R 755 /home/vscode

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies including dev dependencies
RUN uv pip install --system . && \
    uv pip install --system --group dev

# Set up workspace ownership
RUN chown -R vscode:vscode /app

# Configure bash to start in workspace directory and enable git wrapper
RUN echo '# Enable git wrapper for quality check enforcement' >> /home/vscode/.bashrc_devcontainer && \
    echo 'if [ -z "$WORKSPACE_ROOT" ]; then' >> /home/vscode/.bashrc_devcontainer && \
    echo '    echo "WARNING: WORKSPACE_ROOT not set - git wrapper will not be active" >&2' >> /home/vscode/.bashrc_devcontainer && \
    echo 'elif [ -d "$WORKSPACE_ROOT/scripts/wrappers" ]; then' >> /home/vscode/.bashrc_devcontainer && \
    echo '    export PATH="$WORKSPACE_ROOT/scripts/wrappers:$PATH"' >> /home/vscode/.bashrc_devcontainer && \
    echo 'fi' >> /home/vscode/.bashrc_devcontainer && \
    chown vscode:vscode /home/vscode/.bashrc_devcontainer && \
    echo '' >> /home/vscode/.bashrc && \
    echo '# Source devcontainer-specific configuration' >> /home/vscode/.bashrc && \
    echo 'if [ -f ~/.bashrc_devcontainer ]; then' >> /home/vscode/.bashrc && \
    echo '    . ~/.bashrc_devcontainer' >> /home/vscode/.bashrc && \
    echo 'fi' >> /home/vscode/.bashrc

USER vscode

# Default command (will be overridden by dev container)
CMD ["sleep", "infinity"]
