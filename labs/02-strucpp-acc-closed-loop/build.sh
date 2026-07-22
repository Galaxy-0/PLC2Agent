#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STRUCPP=$($SCRIPT_DIR/setup-strucpp.sh)
BUILD_DIR="$SCRIPT_DIR/build"

mkdir -p "$BUILD_DIR"

"$STRUCPP" "$SCRIPT_DIR/conveyor.st" --test "$SCRIPT_DIR/test_conveyor.st"
"$STRUCPP" "$SCRIPT_DIR/conveyor.st" -o "$BUILD_DIR/conveyor.cpp" --build

printf 'Runtime: %s\n' "$BUILD_DIR/conveyor"
