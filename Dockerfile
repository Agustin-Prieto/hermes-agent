# ── Builder stage ────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Pin Hermes Agent to a specific release tag for reproducibility and auditability.
# Check https://github.com/NousResearch/hermes-agent/releases for latest.
ARG HERMES_REF=v2026.5.16

# Install system deps + Node.js (needed only at build time for Hermes dashboard).
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates git tini && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Hermes Agent and pre-build its React dashboard + TUI bundle.
# Extras mirror what the original template pre-installs.
RUN git clone --depth 1 --branch ${HERMES_REF} \
    https://github.com/NousResearch/hermes-agent.git /opt/hermes-agent && \
    cd /opt/hermes-agent && \
    uv pip install --system --no-cache \
      -e ".[all,messaging,tts-premium,honcho,bedrock,anthropic,edge-tts,hindsight]" && \
    cd /opt/hermes-agent/web && \
    npm install --silent && \
    npm run build && \
    cd /opt/hermes-agent/ui-tui && \
    npm install --silent --no-fund --no-audit --progress=false && \
    npm run build && \
    rm -rf /opt/hermes-agent/web /opt/hermes-agent/.git /root/.npm

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install runtime system deps: curl (for Hermes' Node.js auto-installer),
# ca-certificates (for HTTPS), and Node.js (for Hermes browser tools).
# The Debian bookworm nodejs package is sufficient for Hermes' needs and avoids
# the runtime curl-based nodesource installer that fails without curl.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy tini from builder (tiny init for zombie reaping + signal forwarding).
COPY --from=builder /usr/bin/tini /usr/bin/tini

# Copy pre-built Hermes assets.
COPY --from=builder /opt/hermes-agent /opt/hermes-agent

# Re-install Hermes in runtime image (wheel already built, just register the path).
RUN cd /opt/hermes-agent && \
    uv pip install --system --no-cache \
      -e ".[all,messaging,tts-premium,honcho,bedrock,anthropic,edge-tts,hindsight]" && \
    rm -rf /root/.cache

# Install our own Python dependencies.
COPY requirements.txt /app/requirements.txt
RUN uv pip install --system --no-cache -r /app/requirements.txt && \
    rm -rf /root/.cache

# Copy app code and set permissions while still root.
COPY server.py /app/server.py
COPY templates/ /app/templates/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Install gosu for privilege dropping (used by start.sh to fix volume permissions).
RUN apt-get update && \
    apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user, data directory, and fix ownership of app files.
RUN groupadd -r hermes -g 1000 && \
    useradd -r -g hermes -u 1000 -d /data -s /bin/bash hermes && \
    mkdir -p /data/.hermes && \
    chown -R hermes:hermes /data /app /opt/hermes-agent

ENV HOME=/data
ENV HERMES_HOME=/data/.hermes
# Point Hermes at our pre-built TUI bundle to skip npm install on first use.
ENV HERMES_TUI_DIR=/opt/hermes-agent/ui-tui

WORKDIR /app

EXPOSE 8080

# tini runs as PID 1; -g propagates signals to the whole process group.
# start.sh runs as root, fixes volume permissions, then drops to hermes via gosu.
ENTRYPOINT ["/usr/bin/tini", "-g", "--"]
CMD ["/app/start.sh"]
