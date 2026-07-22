#!/bin/sh
set -eu

LAB_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CACHE_DIR="$LAB_DIR/.cache/acc-modbus-bridge"
ARCHIVE="$LAB_DIR/.cache/acc-modbus-bridge.zip"

mkdir -p "$LAB_DIR/.cache"

if [ ! -f "$CACHE_DIR/acc-modbus-bridge.js" ]; then
  curl -fsSL \
    https://accautomation.ca/simulator/acc-modbus-bridge.zip \
    -o "$ARCHIVE"
  mkdir -p "$CACHE_DIR"
  unzip -q -o "$ARCHIVE" -d "$CACHE_DIR"
fi

if [ ! -d "$CACHE_DIR/node_modules/ws" ]; then
  npm install --prefix "$CACHE_DIR" --ignore-scripts --no-audit --no-fund >&2
fi

printf '%s\n' "$CACHE_DIR"
