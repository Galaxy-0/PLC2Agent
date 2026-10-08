#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'Linux x86_64 only; Mac is SSH/client only.' >&2; exit 64; }
lab_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cache="$lab_dir/.cache"
archive="$cache/strucpp-0.6.0.tgz"
pkg="$cache/strucpp-node-0.6.0/package"
expected=e59b876031b8e9f5d1431ec93d5cd630b2455b79bf1b2f3da224808028294ab0
mkdir -p "$cache"
if [[ ! -f "$archive" || $(stat -c %s "$archive") -lt 2243645 ]]; then
  rc=0
  curl --proto '=https' --proto-redir '=https' --tlsv1.2 --fail --location \
    --silent --show-error --connect-timeout 10 --max-time 45 --max-filesize 2243645 \
    --continue-at - -H 'Accept: application/octet-stream' \
    https://api.github.com/repos/Autonomy-Logic/STruCpp/releases/assets/479332927 \
    -o "$archive" || rc=$?
  [[ $rc -eq 0 ]] || { echo "Download incomplete (curl=$rc); rerun to resume; nothing executed." >&2; exit 75; }
fi
printf '%s  %s\n' "$expected" "$archive" | sha256sum -c - >&2
if [[ ! -f "$pkg/dist/node/cli.js" ]]; then
  mkdir -p "$cache/strucpp-node-0.6.0"
  tar -xzf "$archive" -C "$cache/strucpp-node-0.6.0" --no-same-owner
fi
mkdir -p "$cache/node-deps"
lock_sha=$(sha256sum "$lab_dir/toolchain/package-lock.json" | cut -d ' ' -f 1)
if [[ ! -d "$cache/node-deps/node_modules" || ! -f "$cache/node-deps/.installed-lock-sha256" || $(cat "$cache/node-deps/.installed-lock-sha256") != "$lock_sha" ]]; then
  cp "$lab_dir/toolchain/package.json" "$lab_dir/toolchain/package-lock.json" "$cache/node-deps/"
  (cd "$cache/node-deps"; timeout 90 npm ci --ignore-scripts --omit=dev --no-audit --no-fund \
    --registry https://registry.npmjs.org --fetch-retries=0 --fetch-timeout=20000) >&2
  printf '%s\n' "$lock_sha" > "$cache/node-deps/.installed-lock-sha256"
fi
if [[ ! -e "$pkg/node_modules" ]]; then ln -s ../../node-deps/node_modules "$pkg/node_modules"; fi
cat > "$cache/compiler" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
cache=$(cd -- "$(dirname -- "$0")" && pwd)
exec node "$cache/strucpp-node-0.6.0/package/dist/node/cli.js" "$@"
WRAPPER
chmod +x "$cache/compiler"
"$cache/compiler" --version >&2
printf '%s\n' "$cache/compiler"
