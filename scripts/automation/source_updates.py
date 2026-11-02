#!/usr/bin/env python3
"""Track approved upstream source revisions; never execute downloaded upstream code.

Only the revision metadata is committed to GitHub. External raw archives stay local.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'analysis'/'upstream_revisions.json'
SOURCES={
    'aurora': 'https://github.com/XanaduAI/xanadu-aurora-data.git',
    'gkp': 'https://github.com/XanaduAI/xanadu-gkp-data.git',
    'helios': 'https://github.com/Quantinuum/Helios-paper-data.git',
    'ion-specs': 'https://github.com/Quantinuum/quantinuum-hardware-specifications.git',
    'neutral-code': 'https://github.com/oscars47/RydSFF.git',
}

def remote_rev(url):
    p=subprocess.run(['git','ls-remote',url,'HEAD'],capture_output=True,text=True,timeout=60)
    if p.returncode:raise RuntimeError(f'Cannot query source {url}: {p.stderr.strip()}')
    match=re.fullmatch(r'([0-9a-f]{40})\s+HEAD\s*',p.stdout)
    if not match:raise RuntimeError(f'Unexpected Git response from {url}: {p.stdout[:100]}')
    return match.group(1)

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--refresh',action='store_true',help='Query approved repositories and update source revision record')
    ap.add_argument('--output',type=Path,default=DEST)
    args=ap.parse_args(argv)
    previous={}
    if args.output.exists():
        previous=json.loads(args.output.read_text()).get('sources',{})
    sources={}
    for name,url in SOURCES.items():
        if args.refresh:rev=remote_rev(url)
        else:rev=previous.get(name,{}).get('head_revision')
        sources[name]={'url':url,'head_revision':rev,'mode':'revision-monitor-only'}
    obj={'schema':'ftqc.external-revisions.v1','sources':sources,
         'scope':'Observed Git HEAD revisions are external-source alerts, not verified experimental claims. Review authors, license, files, and benchmark protocol before analysis.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    print('Wrote',args.output)
    print('Changes:',', '.join(n for n in SOURCES if previous.get(n,{}).get('head_revision')!=sources[n]['head_revision']) or 'none')

if __name__=='__main__':
    try:main()
    except (RuntimeError,subprocess.TimeoutExpired) as e:
        print('Source refresh FAILED, no partial source lock accepted:',e,file=sys.stderr)
        sys.exit(1)
