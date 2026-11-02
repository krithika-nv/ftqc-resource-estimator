"""Inspect verified neutral-atom Zenodo ZIP numerical file schemas, never execute code.

Unknown array conventions are reported explicitly; we do not invent atom-loss
labels or decoding semantics. A future source-specific adapter requires author
notebook protocol agreement and test vectors.
"""
from __future__ import annotations
import argparse,hashlib,io,json,zipfile
from pathlib import Path
from .neutral_archive import EXPECTED_MD5

def survey(path:Path,output:Path,*,verify_hash=True,max_member=2_000_000,max_preview=12):
    md5=hashlib.md5()
    if verify_hash:
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(2**20),b''):md5.update(chunk)
        if md5.hexdigest()!=EXPECTED_MD5:raise ValueError('Zenodo neutral source checksum mismatch')
    items=[]
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir() or len(items)>=max_preview:break
            ext=Path(info.filename).suffix.lower()
            if ext not in ('.csv','.json','.npy','.npz'):continue
            row={'source_member':info.filename,'uncompressed_bytes':info.file_size,'type':ext,'executable_code_loaded':False}
            if info.file_size>max_member:row['status']='too_large_for_safe_preview'
            elif ext in ('.csv','.json'):
                data=z.read(info)
                if ext=='.csv':row['csv_header']=data.splitlines()[0].decode('utf8','replace')[:600]
                else:
                    try:
                        obj=json.loads(data);row['root_type']=type(obj).__name__
                        if isinstance(obj,dict):row['root_keys']=list(obj)[:24]
                    except (ValueError,UnicodeError):row['status']='not_plain_json'
            else:
                try:
                    import numpy as np
                    arr=np.load(io.BytesIO(z.read(info)),allow_pickle=False)
                    if isinstance(arr,np.ndarray):row.update(shape=list(arr.shape),dtype=str(arr.dtype))
                    else:
                        with arr:row['npz_arrays']={n:{'shape':list(arr[n].shape),'dtype':str(arr[n].dtype)} for n in arr.files[:16]}
                except (ValueError,ImportError,zipfile.BadZipFile) as exc:row['status']='unsafe_or_unrecognized_numeric_array:'+str(exc)[:120]
            items.append(row)
    result={'schema':'ftqc.neutral-source-schemas.v1','doi':'10.5281/zenodo.15685795','source_md5':md5.hexdigest() if verify_hash else None,
      'inspected':items,'loss_aware_decoder_verified':False,'original_paper_reproduced':False,
      'next_requirement':'Match exact author shot schema, loss/erasure markers, decoder weights and distance definitions before computing a published result.'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print('Neutral atom numeric schema samples:',len(survey(a.archive,a.output)['inspected']))
if __name__=='__main__':main()
