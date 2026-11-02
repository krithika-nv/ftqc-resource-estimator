"""Non-executing opcode/namespace manifest of one Helios paper pickle.

No pickle.load(), object construction, or vendor Python module import. It does
NOT recover experiment counts. This artifact documents precisely what a
trusted, narrow source-to-count exporter must support.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,pickletools
from pathlib import Path

def audit(path:Path):
    counts=collections.Counter();globals_found=[];last_two=[]
    for op,arg,pos in pickletools.genops(path.read_bytes()):
        counts[op.name]+=1
        if op.name in ('GLOBAL','STACK_GLOBAL'):
            globals_found.append({'opcode':op.name,'position':pos,
               'stack_global_predecessors':last_two[-2:] if op.name=='STACK_GLOBAL' else str(arg)})
        if op.name in ('SHORT_BINUNICODE','BINUNICODE'):
            last_two.append(str(arg));last_two=last_two[-2:]
    return {'schema':'ftqc.helios.serialized-source-audit.v1',
       'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'filename':path.name,
       'opcode_histogram':dict(counts),'declared_globals':globals_found,
       'pickle_executed':False,'trial_counts_extracted':False,
       'limitation':'Static pickle opcode inspection is NOT independent numerical reconstruction; a reviewed format-specific numeric exporter is required.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=audit(a.input);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print('Static audit, pickles never executed:',len(r['declared_globals']))
if __name__=='__main__':main()
