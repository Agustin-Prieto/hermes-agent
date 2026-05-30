#!/bin/bash
set -e

# ── Volume permissions fix ────────────────────────────────────────────────────
# Railway volumes are mounted as root. Our container runs as root during init
# and drops to 'hermes' (UID 1000) after setup. Create all directories FIRST,
# then fix ownership recursively so both /data and its contents are writable
# by the hermes user at runtime.
# This is a no-op on local Docker where the volume was already chowned at build.

# Prepare every directory Hermes expects on a fresh volume.
# Without these, hermes dashboard endpoints can fail opaquely.
mkdir -p /data/.hermes/cron \
         /data/.hermes/sessions \
         /data/.hermes/logs \
         /data/.hermes/memories \
         /data/.hermes/skills \
         /data/.hermes/pairing \
         /data/.hermes/hooks \
         /data/.hermes/image_cache \
         /data/.hermes/audio_cache \
         /data/.hermes/workspace \
         /data/.hermes/skins \
         /data/.hermes/plans \
         /data/.hermes/home

# Seed a default config.yaml if the volume is empty.
if [ ! -f /data/.hermes/config.yaml ] && \
   [ -f /opt/hermes-agent/cli-config.yaml.example ]; then
  cp /opt/hermes-agent/cli-config.yaml.example /data/.hermes/config.yaml
fi

# Ensure .env exists (empty is fine).
[ ! -f /data/.hermes/.env ] && touch /data/.hermes/.env

# Bootstrap OAuth tokens from env var (e.g. xAI Grok SuperGrok).
# Written only once — subsequent token refreshes update the file in place.
if [ ! -f /data/.hermes/auth.json ] && \
   [ -n "${HERMES_AUTH_JSON_BOOTSTRAP}" ]; then
  printf '%s' "${HERMES_AUTH_JSON_BOOTSTRAP}" > /data/.hermes/auth.json
  chmod 600 /data/.hermes/auth.json
fi

# Remove stale gateway PID file left over from a previous container restart.
# Hermes does not clean this on SIGTERM, so a persistent volume would
# cause every subsequent boot to exit with a PID-file race error.
rm -f /data/.hermes/gateway.pid

# ── Persist Google Sheets credentials to a file ──────────────────────────────
# MCP servers started by Hermes don't inherit all env vars, so we write the
# credential to a well-known path that google-sheets-server.py can read.
if [ -n "${GOOGLE_SHEETS_CREDENTIALS}" ]; then
  printf '%s' "${GOOGLE_SHEETS_CREDENTIALS}" > /data/.google-sheets-creds.json
  chmod 600 /data/.google-sheets-creds.json
fi

# ── Fix ownership of everything in /data ──────────────────────────────────────
# This runs AFTER mkdir/cp/touch so the hermes user can write to all files.
chown -R hermes:hermes /data 2>/dev/null || true

# Drop privileges from root to hermes and exec the Python server.
exec gosu hermes:hermes python /app/server.py
