#!/usr/bin/env python3
"""Shallow approved source-code checkouts; keeps upstream material out of Git history.

Does not download massive experimental artifacts or execute foreign notebooks/pickles.
"""
from __future__ import annotations
import argparse, json, os, pathlib, shutil, subprocess, sys
from source_updates import SOURCES, ROOT, DEST

TARGET=ROOT/'data'/'external_hardware'
ALIAS={'aurora':'xanadu_aurora','gkp':'xanadu_gkp','helios':'quantinuum_helios',
       'ion-specs':'quantinuum_specifications','neutral-code':'quera_aquila_2026_code'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',choices=[*SOURCES,'all'],default='aurora')
    p.add_argument('--max-megabytes',type=int,default=200,
                   help='Max checked-out folder size after clone (not a network download limit)')
    p.add_argument('--replace',action='store_true',help='Replace old source checkout only after successful new clone')
    args=p.parse_args()
    if args.max_megabytes<1:p.error('positive size limit required')
    TARGET.mkdir(parents=True,exist_ok=True)
    source_lock=json.loads(DEST.read_text()).get('sources',{}) if DEST.exists() else {}
    selected= list(SOURCES) if args.source=='all' else [args.source]
    for key in selected:
        dest=TARGET/ALIAS[key]
        if dest.exists() and not args.replace:
            print(f'{key}: already present; use --replace to refresh clean checkout')
            continue
        tmp=TARGET/(ALIAS[key]+'.incoming')
        if tmp.exists():raise RuntimeError(f'Unremoved incoming checkout exists: {tmp}')
        expected=source_lock.get(key,{}).get('head_revision')
        if expected:
            # Refuse to silently import a different commit than reviewed metadata.
            subprocess.run(['git','clone','--depth=1','--filter=blob:none','--no-checkout',SOURCES[key],str(tmp)],check=True)
            subprocess.run(['git','-C',str(tmp),'fetch','--depth=1','origin',expected],check=True)
            subprocess.run(['git','-C',str(tmp),'checkout','--detach',expected],check=True)
        else:
            subprocess.run(['git','clone','--depth=1','--filter=blob:none',SOURCES[key],str(tmp)],check=True)
        try:
            if any(f.is_symlink() for f in tmp.rglob('*')):
                raise RuntimeError(f'{key}: unexpected symlink in upstream checkout')
            size=sum(f.stat().st_size for f in tmp.rglob('*') if f.is_file())
            if size>args.max_megabytes*1024*1024:
                raise RuntimeError(f'{key}: source checkout {size} bytes exceeds local size budget')
            if dest.exists():
                backup=TARGET/(ALIAS[key]+'.previous')
                if backup.exists():raise RuntimeError(f'Existing backup: {backup}; inspect before replacing')
                dest.rename(backup)
            tmp.rename(dest)
            print(f'{key}: downloaded, commit',subprocess.check_output(['git','-C',str(dest),'rev-parse','HEAD'],text=True).strip(),'bytes',size)
        except Exception:
            if tmp.exists():shutil.rmtree(tmp)
            raise
if __name__=='__main__':
    try: main()
    except (RuntimeError,subprocess.CalledProcessError) as e:
        for name in ALIAS.values():
            tmp=TARGET/(name+'.incoming')
            if tmp.exists():shutil.rmtree(tmp)
        print('ERROR:',e,file=sys.stderr);sys.exit(1)
