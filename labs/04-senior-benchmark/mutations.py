#!/usr/bin/env python3
# Compileable negative controls validate the verifier, not an AI model.
import hashlib
import json
from pathlib import Path
import subprocess
import sys

lab = Path(__file__).resolve().parent
source = (lab / 'cell.st').read_text()
mutations = [
    ('ignore_communication_stale', 'ELSIF NOT CommFresh THEN', 'ELSIF FALSE THEN', 'communication_stale'),
    ('accept_duplicate_sequence', '(ReqSeq > LastAccepted)', '(ReqSeq >= LastAccepted)', 'duplicate_request'),
    ('accept_wrong_ack', '(AckSeq = AcceptedSeq)', 'TRUE', 'mismatched_ack'),
    ('accept_held_reset', 'ResetPb AND NOT PrevReset AND EStopOk', 'ResetPb AND EStopOk', 'reset_edge_and_reconcile'),
    ('disable_motion_timeout', 'StateTicks >= CycleTimeoutTicks', 'FALSE', 'extend_timeout'),
]
results = []
for name, before, after, expected in mutations:
    if before not in source:
        raise RuntimeError(f'mutation anchor missing: {name}')
    directory = lab / 'build/mutants' / name
    directory.mkdir(parents=True, exist_ok=True)
    mutated = source.replace(before, after)
    candidate = directory / 'candidate.st'
    candidate.write_text(mutated)
    with (directory / 'build.log').open('w') as log:
        subprocess.run([str(lab / 'build.sh'), str(candidate), str(directory)],
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    report = directory / 'report.json'
    completed = subprocess.run([sys.executable, str(lab / 'bench.py'), '--binary', str(directory / 'cell-cli'),
                                '--report', str(report), '--trace-dir', str(directory / 'traces')], timeout=30)
    r = json.loads(report.read_text())
    failures = [c['case'] for c in r['cases'] if not c['pass']]
    detected = completed.returncode == 1 and expected in failures
    results.append({'mutation': name, 'expected_failure': expected, 'detected': detected,
                    'exit_code': completed.returncode, 'failed_cases': failures,
                    'source_sha256': hashlib.sha256(mutated.encode()).hexdigest()})
summary = {'schema_version': 1, 'kind': 'verifier_negative_controls', 'detected': sum(r['detected'] for r in results),
           'total': len(results), 'mutations': results}
(lab / 'build/mutations.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
sys.exit(0 if summary['detected'] == summary['total'] else 1)
