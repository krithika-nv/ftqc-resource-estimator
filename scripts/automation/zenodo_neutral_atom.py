#!/usr/bin/env python3
"""Zenodo public neutral-atom QEC record metadata and strictly size-limited file downloads.

Never extracts untrusted archives or executes notebooks. Preserve source checksums.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import shutil
import urllib.request
from pathlib import PurePosixPath

ROOT=Path(__file__).resolve().parents[2]
RECORD_ID='15685795'
API=f'https://zenodo.org/api/records/{RECORD_ID}'

def request_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'FTQC-Analysis-Source-Audit/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=45) as r:
        if r.status!=200:raise RuntimeError(f'Unexpected HTTP status: {r.status}')
        raw=r.read(6*1024*1024+1)
        if len(raw)>6*1024*1024:raise RuntimeError('Record metadata exceeds safety limit')
    return json.loads(raw)

def summarize(meta):
    if str(meta.get('id'))!=RECORD_ID:raise RuntimeError('Zenodo record id mismatch')
    files=[]
    for x in meta.get('files',[]):
        key=x.get('key')
        if not isinstance(key,str) or not key or '\\' in key or PurePosixPath(key).is_absolute() or any(v in ('.','..') for v in PurePosixPath(key).parts):
            raise RuntimeError(f'Unexpected archive filename: {key}')
        size=x.get('size')
        if not isinstance(size,int) or size<0:raise RuntimeError('Missing positive size')
        checksum=x.get('checksum')
        url=x.get('links',{}).get('self')
        if not checksum or not url or not url.startswith('https://zenodo.org/'):
            raise RuntimeError('Source file lacks checksum or trusted Zenodo link')
        files.append({'filename':key,'size_bytes':size,'checksum':checksum,'url':url})
    return {'schema':'ftqc.zenodo-metadata.v1','record_id':RECORD_ID,
            'doi':meta.get('doi'),'title':meta.get('metadata',{}).get('title'),
            'license':meta.get('metadata',{}).get('license',{}),
            'files':sorted(files,key=lambda f:f['filename']),
            'note':'Metadata only: not decoder reconstruction, hardware validation, or permission to redistribute raw files.'}

def download(file,out,max_bytes):
    if file['size_bytes']>max_bytes:
        print('SKIP oversized:',file['filename'],file['size_bytes']);return
    out.mkdir(parents=True,exist_ok=True)
    path=out/file['filename']
    path.parent.mkdir(parents=True,exist_ok=True)
    checksum=file['checksum']
    alg,sep,expected=checksum.partition(':')
    if not sep or alg not in ('md5','sha256'):
        raise RuntimeError('Unknown checksum algorithm: '+checksum)
    if path.exists():
        if path.stat().st_size != file['size_bytes']:
            raise RuntimeError('Previously downloaded source has wrong size: '+str(path))
        current=hashlib.new(alg)
        with path.open('rb') as existing:
            for chunk in iter(lambda:existing.read(1024*1024),b''):
                current.update(chunk)
        if current.hexdigest().lower()!=expected.lower():
            raise RuntimeError('Previously downloaded source checksum mismatch: '+str(path))
        print('Verified existing file:',path)
        return
    temp=out/(file['filename']+'.part')
    if temp.exists():raise RuntimeError('Incomplete previous download; inspect before retry: '+str(temp))
    h=hashlib.new(alg)
    try:
        req=urllib.request.Request(file['url'],headers={'User-Agent':'FTQC-Analysis-Source-Audit/1.0'})
        with urllib.request.urlopen(req,timeout=60) as r, temp.open('wb') as f:
            if not r.url.startswith('https://zenodo.org/'):
                raise RuntimeError('Unexpected download redirect domain: '+r.url)
            size=0
            while True:
                chunk=r.read(min(1024*1024,max_bytes-size+1))
                if not chunk:break
                size+=len(chunk)
                if size>max_bytes:raise RuntimeError('Download exceeds maximum byte count')
                h.update(chunk);f.write(chunk)
        if size!=file['size_bytes']:raise RuntimeError('Downloaded length mismatch')
        if h.hexdigest().lower()!=expected.lower():raise RuntimeError('Checksum mismatch')
        temp.rename(path)
        print('Verified:',path,'bytes:',size)
    finally:
        if temp.exists():temp.unlink()

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT/'evidence/neutral_atom_zenodo_metadata.json')
    p.add_argument('--download-small',action='store_true')
    p.add_argument('--download-large',action='store_true',help='Explicit opt-in: download the ~1 GB official experimental archive')
    p.add_argument('--max-megabytes',type=int,default=10)
    p.add_argument('--max-total-megabytes',type=int,default=50)
    p.add_argument('--file-directory',type=Path,default=ROOT/'data/external_hardware/neutral_atom_qec')
    args=p.parse_args(argv)
    if not 1<=args.max_megabytes<=200:p.error('max-megabytes must be 1 to 200')
    if not 1<=args.max_total_megabytes<=500:p.error('max-total-megabytes must be 1 to 500')
    info=summarize(request_json(API))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(info,indent=2,sort_keys=True)+'\n')
    print('Verified Zenodo metadata for',len(info['files']),'files; manifest:',args.output)
    if args.download_large:
        args.file_directory.mkdir(parents=True,exist_ok=True)
        for f in info['files']:
            available=shutil.disk_usage(args.file_directory).free
            if available<max(2*1024**3,f['size_bytes']*2):
                raise RuntimeError('Insufficient disk space for opt-in source archive')
            download(f,args.file_directory,max(f['size_bytes'],1))
    elif args.download_small:
        budget=args.max_total_megabytes*1024*1024
        for f in info['files']:
            if f['size_bytes']>budget:
                print('SKIP total byte budget:',f['filename'],f['size_bytes']);continue
            if f['size_bytes']<=args.max_megabytes*1024*1024:
                path=args.file_directory/f['filename']
                if not path.exists():budget-=f['size_bytes']
            download(f,args.file_directory,args.max_megabytes*1024*1024)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('ERROR: Zenodo source audit failed:',e,file=sys.stderr);sys.exit(1)
