#!/bin/sh
set -e

# Fly.io mounts a persistent volume at /data (configured in fly.toml).
# Symlink /app/data → /data so SQLite + menu.json survive restarts.
if [ -d "/data" ] && [ ! -L "/app/data" ]; then
    rm -rf /app/data
    ln -s /data /app/data
fi

mkdir -p /app/data

# menu.json is repo-managed — scripts/build_menu.py and scripts/merge_petpooja.py
# are the only writers, nothing touches it at runtime. So always sync the bundled
# copy over the volume's, or the first boot's copy never updates (new items and
# half_price fields silently go stale on every future release).
cp /app/menu.json.bundled /app/data/menu.json

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
