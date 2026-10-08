#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux ]] || { echo 'Build only on bauhinia/Linux; no Mac simulation.' >&2; exit 64; }
lab_dir=$(cd -- "$(dirname -- "$0")" && pwd)
compiler=$("$lab_dir/setup-linux.sh")
source=${1:-"$lab_dir/cell.st"}
out=${2:-"$lab_dir/build"}
mkdir -p "$out"
timeout 30 "$compiler" "$source" -o "$out/cell.cpp" --no-default-libs
timeout 30 g++ -std=c++17 -O0 -Wall -Wextra -I"$out" \
  -I"$lab_dir/.cache/strucpp-node-0.6.0/package/src/runtime/include" \
  "$lab_dir/driver.cpp" "$out/cell.cpp" -o "$out/cell-cli"
printf 'Native ST scan driver: %s\n' "$out/cell-cli"
