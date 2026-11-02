"""Non-executing, no-extraction inventory of Bluvstein/Geim neutral-atom QEC source.

This is a data schema inventory, not published loss-aware ML decoding.
"""
from __future__ import annotations
import argparse,hashlib,json,zipfile
from pathlib import Path,PurePosixPath

EXPECTED_MD5='4c45c542b63a9bbcda7f2fbd85577eb8'

def inspect(path:Path,out:Path,*,require_published_hash=True):
    if not path.is_file():raise FileNotFoundError(path)
    h=hashlib.md5();sha=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(2*1024*1024),b''):h.update(part);sha.update(part)
    if require_published_hash and h.hexdigest()!=EXPECTED_MD5:
        raise ValueError('Neutral-atom ZIP does not match recorded Zenodo MD5')
    with zipfile.ZipFile(path) as z:
        members=[]
        for info in z.infolist():
            name=info.filename;p=PurePosixPath(name)
            if p.is_absolute() or '\\' in name or '..' in p.parts or name.startswith('/'):
                raise ValueError('Archive unsafe path: '+name)
            if info.is_dir():continue
            ext=p.suffix.lower()
            category=('potential_sample_data' if ext in ('.npy','.npz','.csv','.parquet','.h5','.hdf5','.json') else
                      'analysis_code' if ext in ('.ipynb','.py') else
                      'executable_serialization_unsafe' if ext in ('.p','.pkl','.pickle') else 'other')
            members.append({'name':name,'bytes':info.file_size,'category':category})
    summary={'status':'schema_inventory_only','doi':'10.5281/zenodo.15685795',
             'archive_md5':h.hexdigest(),'archive_sha256':sha.hexdigest(),
             'member_count':len(members),'members':members,
             'paper_target':{'observable':'four-round d=3 versus d=5 logical-error-per-round ratio, loss-aware ML decoder',
                             'published_ratio':2.14,'published_standard_uncertainty':0.13,
                             'verified_against_local_data':False},
             'limitations':['No archive members are executed or extracted by this tool.',
                            'A Figure 2d reproduction requires the authors\' exact loss-aware decoder and original data definitions.',
                            'Paper-reported 2.14(13) is a target/reference, not an independently derived output.']}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('outputs/external_validation/neutral_source_archive.json'))
    p.add_argument('--skip-hash-check',action='store_true',help='Inventory a synthetic/fixture archive only; not evidence')
    a=p.parse_args()
    try:
        x=inspect(a.input,a.output,require_published_hash=not a.skip_hash_check)
        print(json.dumps({'status':x['status'],'files':x['member_count'],'report':str(a.output)}))
    except Exception as exc:p.exit(2,'ERROR: '+str(exc)+'\n')
if __name__=='__main__':main()
