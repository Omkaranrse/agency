# ==============================================================================
# Agency Backend Production Container Image
# Multi-stage build targeting Python 3.12 with non-root security isolation.
# ==============================================================================

# --- Stage 1: Build Dependencies ---
FROM python:3.12-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml .
# Install production dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# --- Stage 2: Runtime Image ---
FROM python:3.12-slim-bookworm AS runner

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    HOST=0.0.0.0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root unprivileged group and user
RUN groupadd -g 1001 agency && \
    useradd -u 1001 -g agency -m -d /home/agency agency

# Copy virtualenv from builder
COPY --from=builder --chown=agency:agency /opt/venv /opt/venv

# Copy application source
COPY --chown=agency:agency src/ ./src/
COPY --chown=agency:agency evals/ ./evals/
COPY --chown=agency:agency pyproject.toml .

# Install package editable/wheel in runner environment
RUN pip install --no-cache-dir --no-deps -e .

# Provision directories for sqlite checkpoints, workspaces, and artifacts
RUN mkdir -p /app/data /app/artifacts && \
    chown -R agency:agency /app/data /app/artifacts

USER agency

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["uvicorn", "agency.interfaces.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
