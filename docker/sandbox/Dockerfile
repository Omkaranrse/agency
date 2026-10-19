# ==============================================================================
# Agency Sandbox Container Image
# Provides an isolated environment for AI-generated web applications.
# Includes Node.js 20, pnpm, Git, and Playwright Chromium.
# ==============================================================================

FROM node:20.18.0-bookworm-slim

# Avoid interactive prompts during apt operations
ENV DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PNPM_HOME="/home/sandbox/.local/share/pnpm" \
    PATH="/home/sandbox/.local/share/pnpm:$PATH"

# Install Git and ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Rename existing uid 1000 user to 'sandbox'
RUN usermod -l sandbox -d /home/sandbox -m node && \
    groupmod -n sandbox node

# Enable pnpm via corepack and install Playwright CLI
RUN corepack enable && corepack prepare pnpm@9.12.2 --activate && \
    npm install -g playwright@1.48.2

# Install Chromium and system dependencies required for headless execution
RUN npx playwright install --with-deps chromium

# Provision isolated workspace directory with unprivileged ownership
RUN mkdir -p /workspace /ms-playwright && \
    chown -R sandbox:sandbox /workspace /ms-playwright /home/sandbox

WORKDIR /workspace
USER sandbox

# Keep container idle awaiting isolated exec commands
CMD ["sleep", "infinity"]
