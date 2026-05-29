#!/bin/bash
set -e

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

exec python /app/server.py
