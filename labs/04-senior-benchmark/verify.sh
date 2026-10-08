#!/usr/bin/env bash
set -euo pipefail
[[ $(uname -s) == Linux ]] || { echo 'Verify only on Linux; Mac is SSH/client only.' >&2; exit 64; }
lab_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$lab_dir"
mkdir -p build
./build.sh > build/build.log 2>&1
python3 bench.py --report build/report.json --trace-dir build/traces
python3 bench.py --report build/replay.json --trace-dir build/replay-traces
python3 - <<'PYTHON'
import json
from pathlib import Path
first=json.loads(Path('build/report.json').read_text())
second=json.loads(Path('build/replay.json').read_text())
a={c['case']:c['trace_sha256'] for c in first['cases']}
b={c['case']:c['trace_sha256'] for c in second['cases']}
assert a == b, 'deterministic replay drift'
print('Deterministic replay: 15/15 byte-identical traces')
PYTHON
python3 mutations.py
compiler=$(./setup-linux.sh)
python3 - <<'PYTHON'
from pathlib import Path
s=Path('cell.st').read_text().replace('AcceptedSeq := ReqSeq;', 'AcceptedSeq := MissingSequence;')
Path('build/compile-error.st').write_text(s)
PYTHON
status=0
timeout 30 "$compiler" build/compile-error.st -o build/compile-error.cpp --no-default-libs > build/compile-error.log 2>&1 || status=$?
[[ $status -ne 0 && $status -ne 124 ]] || { echo 'Compiler negative control did not fail correctly' >&2; exit 1; }
rg 'MissingSequence|MISSINGSEQUENCE' build/compile-error.log >/dev/null
printf 'Compiler negative control: rejected undeclared symbol (exit=%s)\n' "$status"
python3 test-cli.py
python3 collect-evidence.py
