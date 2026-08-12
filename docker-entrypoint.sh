#!/bin/sh
set -e
mkdir -p /app/data
# The Railway volume mounts over /app/data (hiding the image's copy), so seed
# the menu from the bundled file on first boot.
if [ ! -f /app/data/menu.json ]; then
    cp /app/menu.json.bundled /app/data/menu.json
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
