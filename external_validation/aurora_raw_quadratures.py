"""Independent numerical statistics from trusted, non-object optical .npy exports.

No assumption that an arbitrary file in a vendor repository is a particular
Aurora published quadrature dataset. Explicit source and unit verification is
needed before physics interpretation.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def analyze(path:Path,units:str):
    if not units or units=='unknown':raise ValueError('explicit source quadrature units needed')
    if path.stat().st_size>500_000_000:raise ValueError('work on a chunked export for files above 500 MB')
    import numpy as np
    x=np.load(path,allow_pickle=False)
    if not isinstance(x,np.ndarray) or x.ndim not in (1,2) or x.size>20_000_000:
        raise ValueError('numeric 1D or 2D array at most 20M entries required')
    if x.dtype.kind!='f' or not np.all(np.isfinite(x)):
        raise ValueError('real finite quadratures required; object/pickle or complex data refused')
    rows=x.reshape(-1,1) if x.ndim==1 else x
    if rows.shape[0]<2:raise ValueError('at least two observations required')
    values={'shape':list(x.shape),'units':units,'sample_count':rows.shape[0],
            'axis_means':[float(q) for q in rows.mean(axis=0)],
            'axis_standard_deviations':[float(q) for q in rows.std(axis=0,ddof=1)],
            'axis_sem':[float(q) for q in rows.std(axis=0,ddof=1)/(rows.shape[0]**.5)]}
    return {'schema':'ftqc.aurora.raw-quadrature-summary.v1','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'source_path':str(path),'numerical_summary':values,
            'status':'numerical_quadrature_characterization_only',
            'published_observable_reproduced':False,
            'limitations':['Mean, spread and SEM assume the supplied numeric columns and units are correctly identified.',
                           'Correlated optical pulses require autocorrelation-aware uncertainty, not IID SEM.',
                           'Authors measurement reduction, published plot/circuit mapping, and decoder must be validated separately.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--units',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=analyze(a.input,a.units);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Numeric optical moments computed, not physics reproduction:',a.output)
if __name__=='__main__':main()
