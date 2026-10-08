#!/usr/bin/env python3
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

lab=Path(__file__).resolve().parent
build=lab/'build'
evidence=lab/'evidence'
evidence.mkdir(exist_ok=True)
def read(name): return json.loads((build/name).read_text())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def command(*args): return subprocess.check_output(args,text=True).strip()
reference=read('report.json'); replay=read('replay.json'); mutations=read('mutations.json'); cli=read('cli-summary.json')
assert reference['passed']==reference['total']==15
assert mutations['detected']==mutations['total']==5
assert cli['passed']
assert {x['case']:x['trace_sha256'] for x in reference['cases']}=={x['case']:x['trace_sha256'] for x in replay['cases']}
for source,destination in [('report.json','reference-report.json'),('mutations.json','mutations.json'),
                           ('compile-error.log','compile-error.log'),('cli-transcript.ndjson','cli-transcript.ndjson'),
                           ('cli-summary.json','cli-summary.json'),('build.log','build.log')]:
 shutil.copyfile(build/source,evidence/destination)
 if source == 'compile-error.log':
  (evidence/destination).write_text((build/source).read_text().rstrip()+'\n')
excerpts=[]
def excerpt(path,label):
 records=[json.loads(s) for s in path.read_text().splitlines()]
 indices=set(range(min(2,len(records)))) | set(range(max(0,len(records)-3),len(records)))
 for index,r in enumerate(records):
  if r['outputs_commanded']['FaultLatched']:
   indices |= {max(0,index-1),index}
   break
 excerpts.append({'case':label,'complete_trace_sha256':digest(path),'complete_record_count':len(records),
                  'excerpt_only':True,'records':[records[i] for i in sorted(indices)]})
for c in reference['cases']: excerpt(build/'traces'/f"{c['case']}.ndjson",c['case'])
negatives=[]
for m in mutations['mutations']:
 directory=build/'mutants'/m['mutation']
 r=json.loads((directory/'report.json').read_text())
 failures=[{k:c[k] for k in ['case','error','scans','trace_sha256','final','receiver_ledger']} for c in r['cases'] if not c['pass']]
 negatives.append({'mutation':m['mutation'],'compiled_successfully':True,'build_log_sha256':digest(directory/'build.log'),
                   'passed':r['passed'],'total':r['total'],'failures':failures})
 for c in failures: excerpt(directory/'traces'/f"{c['case']}.ndjson",m['mutation']+'/'+c['case'])
(evidence/'negative-reports.json').write_text(json.dumps(negatives,indent=2)+'\n')
lines=[]
for group in excerpts:
 for record in group['records']:
  lines.append(json.dumps({'case':group['case'],'complete_trace_sha256':group['complete_trace_sha256'],
                           'complete_record_count':group['complete_record_count'],'excerpt_only':True,'record':record},sort_keys=True))
(evidence/'trace-excerpts.ndjson').write_text('\n'.join(lines)+'\n')
(evidence/'trace-excerpts.json').unlink(missing_ok=True)
files=['cell.st','driver.cpp','bench.py','setup-linux.sh','build.sh','verify.sh','mutations.py','test-cli.py',
       'collect-evidence.py','toolchain/package.json','toolchain/package-lock.json']
lock=json.loads((lab/'toolchain/package-lock.json').read_text())
packages={k:{'version':v['version'],'integrity':v['integrity']} for k,v in lock['packages'].items() if k}
assert all(v.get('resolved','').startswith('https://registry.npmjs.org/') for k,v in lock['packages'].items() if k)
manifest={'schema_version':1,'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'baseline_commit':command('git','-C',str(lab),'rev-parse','ca62cf1^{commit}'),
 'verification_kind':'reference_environment; no independent AI model evaluation; no field safety validation',
 'environment':{'hostname':platform.node(),'platform':platform.platform(),'os_release':Path('/etc/os-release').read_text(),
                'architecture':platform.machine(),'cpu_count':os.cpu_count(),'python':platform.python_version(),
                'node':command('node','--version'),'npm':command('npm','--version'),
                'gcc':command('gcc','--version').splitlines()[0],
                'compiler':command(str(lab/'.cache/compiler'),'--version')},
 'toolchain':{'official_asset_url':'https://api.github.com/repos/Autonomy-Logic/STruCpp/releases/assets/479332927',
              'tag':'v0.6.0','release_published_at':'2026-07-16T15:35:52Z',
              'asset_sha256':digest(lab/'.cache/strucpp-0.6.0.tgz'),
              'compiler_cli_sha256':digest(lab/'.cache/strucpp-node-0.6.0/package/dist/node/cli.js'),
              'npm_packages':packages,'npm_lifecycle_scripts_enabled':False},
 'build_outputs_sha256':{name:digest(build/name) for name in ['cell.cpp','cell.hpp','cell-cli']},
 'diagnostic_raw_sha256':digest(build/'compile-error.log'),
 'diagnostic_review_normalization':'trailing blank lines removed; complete raw diagnostic retained in build/',
 'input_sha256':{name:digest(lab/name) for name in files},
 'results':{'reference':[15,15],'deterministic_replay':[15,15],'negative_controls_detected':[5,5],
            'compile_error_rejected':True,'ndjson_interface':cli},
 'artifact_sha256':{str(p.relative_to(evidence)):digest(p) for p in sorted(evidence.iterdir()) if p.is_file() and p.name!='manifest.json'}}
(evidence/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Saved small reviewable evidence pack; complete raw traces remain in build/ and are reproducible')
