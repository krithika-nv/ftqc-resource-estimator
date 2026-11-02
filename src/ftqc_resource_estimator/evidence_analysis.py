"""Numerical study primitives shared by hardware-*specific* experiments.

This module makes no device calibration or quantum-hardware equivalence claim.
"""
from __future__ import annotations
import csv
from hashlib import sha256
import json
from math import sqrt, isfinite
from pathlib import Path


def file_hash(path: str | Path) -> str:
    h=sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):
            h.update(block)
    return h.hexdigest()


def read_csv(path:Path, mandatory:tuple[str,...]):
    with open(path,newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or not set(mandatory).issubset(reader.fieldnames):
            raise ValueError('CSV needs columns '+', '.join(mandatory))
        rows=list(reader)
    if not rows: raise ValueError('empty experiment table')
    return rows


def integer(s, field, minimum=0):
    try:
        v=int(s)
        if str(v)!=str(s).strip() and not (isinstance(s,int)):
            raise ValueError
    except (ValueError,TypeError):
        raise ValueError(field+' must be an integer') from None
    if v<minimum: raise ValueError(field+f' must be >= {minimum}')
    return v


def number(s, field):
    try:v=float(s)
    except (TypeError,ValueError): raise ValueError(field+' must be numerical') from None
    if not isfinite(v):raise ValueError(field+' must be finite')
    return v


def wilson(successes:int, trials:int, z=1.959963984540054):
    if not (0<=successes<=trials and trials>0): raise ValueError('invalid binomial data')
    p=successes/trials; zz=z*z; den=1+zz/trials
    mid=(p+zz/(2*trials))/den
    half=z*sqrt(p*(1-p)/trials+zz/(4*trials*trials))/den
    return (max(0.0,0.0 if successes==0 else mid-half),min(1.0,1.0 if successes==trials else mid+half))


def save_report(output:Path, name:str, result:dict, explanation:str):
    output.mkdir(parents=True,exist_ok=True)
    (output/(name+'.json')).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    (output/(name+'.md')).write_text('# '+name.replace('_',' ')+'\n\n'+explanation+'\n\n'
        +'```json\n'+json.dumps(result,indent=2,sort_keys=True)+'\n```\n')
    return result
