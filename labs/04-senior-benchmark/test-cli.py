#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
lab=Path(__file__).resolve().parent
requests=[{'op':'reset','seed':17},{'op':'set_inputs','inputs':{'StartPb':1}},{'op':'step'},
{'op':'set_inputs','inputs':{'StartPb':0}},{'op':'step'},{'op':'set_inputs','inputs':{'ReqValid':1,'ReqSeq':11}},
{'op':'step','scans':30},{'op':'snapshot'},{'op':'set_inputs','inputs':{'StartPb':2}},
{'op':'set_inputs','inputs':{'AckSeq':999}},{'op':'set_inputs','inputs':[]},{'op':'step','scans':1001},
{'op':'inject_fault','fault':'unknown'},{'op':'snapshot'}]
p=subprocess.run(['python3',str(lab/'bench.py'),'--cli'],input=''.join(json.dumps(r)+'\n' for r in requests),
                 capture_output=True,text=True,timeout=15,check=True)
responses=[json.loads(line) for line in p.stdout.splitlines()]
assert len(responses)==len(requests)
assert responses[7]['outputs']['CompletedCount']==1 and responses[7]['receiver_ledger']==[11]
assert all(not responses[i]['ok'] for i in [8,9,10,11,12])
assert responses[13]['outputs']['CompletedCount']==1
(lab/'build/cli-transcript.ndjson').write_text(''.join(json.dumps({'request':req,'response':resp},sort_keys=True)+'\n' for req,resp in zip(requests,responses)))
(lab/'build/cli-summary.json').write_text(json.dumps({'passed':True,'frames':len(responses),'invalid_frames_rejected':5,'normal_transfer_completed':True},indent=2)+'\n')
print('NDJSON interface: normal transfer and five invalid frames passed')
