#!/bin/sh
set -eu

VERSION="0.6.0"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CACHE_DIR="$SCRIPT_DIR/.cache"
INSTALL_DIR="$CACHE_DIR/strucpp-$VERSION"
ARCHIVE="$CACHE_DIR/strucpp-darwin-arm64-$VERSION.zip"
URL="https://github.com/Autonomy-Logic/STruCpp/releases/download/v$VERSION/strucpp-darwin-arm64.zip"

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo "This setup script currently targets Apple Silicon macOS." >&2
  exit 1
fi

mkdir -p "$CACHE_DIR"

if [ ! -x "$INSTALL_DIR/strucpp/strucpp" ]; then
  rm -rf "$INSTALL_DIR"
  curl --fail --location --silent --show-error "$URL" --output "$ARCHIVE"
  mkdir -p "$INSTALL_DIR"
  ditto -x -k "$ARCHIVE" "$INSTALL_DIR"
fi

"$INSTALL_DIR/strucpp/strucpp" --version >&2
printf '%s\n' "$INSTALL_DIR/strucpp/strucpp"
