#!/usr/bin/env python3
import argparse
from pathlib import Path
import shutil
import sys
p=argparse.ArgumentParser(); p.add_argument('--confirm',action='store_true'); args=p.parse_args()
if sys.platform != 'linux': raise SystemExit('Linux only; Mac is SSH/client only')
lab=Path(__file__).resolve().parent
if lab.name != '04-senior-benchmark' or lab.parent.name != 'labs': raise SystemExit('Unexpected lab location')
for name in ('.cache','build'):
 target=lab/name
 if target.is_symlink() or target.resolve().parent != lab: raise SystemExit('Refusing symlink/outside-lab target')
 if args.confirm:
  if target.exists(): shutil.rmtree(target)
  print(f'Removed task-generated directory: {target}')
 else: print(f'Would remove only: {target}; rerun with --confirm')
