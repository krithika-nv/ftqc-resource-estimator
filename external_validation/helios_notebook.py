"""Read *cached author notebook outputs* as provenance records, without executing pickle.

A cached output is NOT an independent reproduction or a calibration fit. This
function extracts the explicitly named Helios MCMR result and verifies its
unit scale and source identity. It never executes cells or unpickles objects.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path

PATTERN=re.compile(r'^Global per MCMR Crosstalk (.+?) \(1e-4\):\s*([\d.]+)\s*\+/-\s*([\d.]+)\s*$',re.M)

def extract(path:Path)->dict:
    raw=path.read_bytes();nb=json.loads(raw)
    if not isinstance(nb,dict) or 'cells' not in nb:raise ValueError('not an ipynb notebook')
    source='\n'.join(''.join(cell.get('source',[])) for cell in nb['cells'])
    identifier='exp_MCMR_Crosstalk_Helios-1_q[0,2,4,6,8,10,12,14]_2026_01_01.p'
    if identifier not in source:raise ValueError('source notebook does not identify expected Helios benchmark')
    lines=[]
    for cell in nb['cells']:
        for output in cell.get('outputs',[]):
            text=''.join(output.get('text',output.get('data',{}).get('text/plain',[])))
            lines.extend(text.splitlines())
    values={}
    for line in lines:
        m=PATTERN.fullmatch(line.strip())
        if m:
            name,amount,error=m.groups()
            values[name]={'published_notebook_value':float(amount)*1e-4,
                          'published_notebook_plus_minus':float(error)*1e-4,
                          'display_unit':'probability','source_scale':'1e-4'}
    if 'Infidelity' not in values or len(values)!=5:
        raise ValueError('expected named Helios MCMR statistics not found in cached notebook output')
    return {'schema':'ftqc.helios.cached_notebook_output.v1','experiment':'MCMR crosstalk',
      'hardware':'Helios-1','data_file_declared_in_author_notebook':identifier,
      'notebook_sha256':hashlib.sha256(raw).hexdigest(), 'values':values,
      'evidence_level':'published_author_notebook_output_extraction',
      'independent_reanalysis':False,'physical_noise_model_calibrated':False,
      'limitation':'Read-only extraction of saved author notebook output. Not recalculated from .p records; no pickles executed.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();result=extract(args.input);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('Helios author notebook output extracted without executing code:',args.output)
if __name__=='__main__':main()
