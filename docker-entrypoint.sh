#!/bin/sh
set -e

# Fly.io mounts a persistent volume at /data (configured in fly.toml).
# Symlink /app/data → /data so SQLite + menu.json survive restarts.
if [ -d "/data" ] && [ ! -L "/app/data" ]; then
    rm -rf /app/data
    ln -s /data /app/data
fi

mkdir -p /app/data

# Seed menu from bundled file on first boot (works on both Fly and Railway).
if [ ! -f /app/data/menu.json ]; then
    cp /app/menu.json.bundled /app/data/menu.json
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
