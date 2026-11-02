"""Independent measured hardware outcome vs *readout-only* prediction benchmark.

Input CSV is source-normalized from paired hardware calibration/info/QASM/
bitstrings; ORIGINAL raw format cannot safely be guessed. Counts are actual
final-data measurements, not fabricated decoder event predictions. The null
predictor assumes independent identical readout flips and perfect state prep;
we DO NOT call it a calibrated QEC logical-error predictor.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from math import comb,sqrt
from .evidence_analysis import file_hash,read_csv,integer,number,wilson,save_report


def independent_majority_error(d:int,p:float)->float:
    if d<=0 or d%2==0 or not 0<=p<=1:raise ValueError('odd positive d and 0<=p<=1 needed')
    return sum(comb(d,k)*p**k*(1-p)**(d-k) for k in range(d//2+1,d+1))


def compare_from_verified_flat_table(path:Path,*,backend:str='ibm_fez', min_epochs=2)->dict:
    mandatory=('snapshot_id','backend','calibration_utc','calibration_sha256',
         'executed_qasm_sha256','bitstrings_sha256','code_family','distance','logical_state',
         'final_data_bitstring','count','readout_flip_probability')
    rows=read_csv(path,mandatory)
    snapshots=defaultdict(lambda:{'shots':0,'majority_failures':0,'p':None,'d':None,
                                   'time':None,'scope':set(),'hashes':None})
    for r in rows:
        if r['backend']!=backend or r['code_family']!='repetition':raise ValueError('backend or code family mismatch')
        sid=r['snapshot_id'];d=integer(r['distance'],'distance',1)
        if d%2==0:raise ValueError('repetition length must be odd')
        state=r['logical_state'];bits=r['final_data_bitstring']
        if state not in ('0','1') or len(bits)!=d or any(v not in '01' for v in bits):
            raise ValueError('explicit logical state and d final data bits required')
        n=integer(r['count'],'count',1)
        p=number(r['readout_flip_probability'],'readout probability')
        if not 0<=p<=1:raise ValueError('invalid readout flip probability')
        try:dt=datetime.fromisoformat(r['calibration_utc'].replace('Z','+00:00'))
        except ValueError:raise ValueError('invalid timestamp') from None
        if dt.tzinfo is None:raise ValueError('calibration timestamp must include timezone')
        hashes=tuple(r[k] for k in ('calibration_sha256','executed_qasm_sha256','bitstrings_sha256'))
        if any(len(h)!=64 or any(c not in '0123456789abcdef' for c in h.lower()) for h in hashes):
            raise ValueError('source SHA256 hashes required, not placeholder ids')
        s=snapshots[sid]
        if s['d'] is None: s.update(d=d,p=p,time=dt.isoformat(),hashes=hashes)
        elif (s['d'],s['p'],s['time'],s['hashes'])!=(d,p,dt.isoformat(),hashes):
            raise ValueError('inconsistent snapshot metadata')
        s['shots']+=n
        # final-data majority vote is a baseline, not a syndrome MWPM decoder
        s['majority_failures']+=n*(int(bits.count('1')>d//2)!=int(state))
    dates=sorted({s['time'] for s in snapshots.values()})
    if len(dates)<min_epochs:raise ValueError('not enough distinct calibration epochs for temporal evaluation')
    pivot=dates[max(0,min(len(dates)-2,int(len(dates)*.7)-1))]
    evals=[]
    for sid,s in sorted(snapshots.items()):
        pred=independent_majority_error(s['d'],s['p'])
        obs=s['majority_failures']/s['shots']
        ci=wilson(s['majority_failures'],s['shots'])
        evals.append({'snapshot_id':sid,'split':'train_epoch' if s['time']<=pivot else 'heldout_epoch',
         'calibration_utc':s['time'],'shots':s['shots'],'failures':s['majority_failures'],
         'observed_final_bit_majority_failure':obs,'wilson95':ci,
         'independent_readout_only_prediction':pred,'residual_observed_minus_proxy':obs-pred,
         'prediction_outside_observed_wilson_interval':not(ci[0]<=pred<=ci[1])})
    return {'scope':'HARDWARE_FINAL_BITSTRING_BASELINE_VS_READOUT_ONLY_NULL_MODEL_NOT_QEC_DECODER_VALIDATION',
       'input_sha256':file_hash(path),'backend':backend,'epoch_split_cutoff':pivot,
       'method':'majority of final data bits vs expected prepared state; independent identical readout Bernoulli flips',
       'temporal_holdout':'Based on calibration epochs only; verification of experiment execution time is still required.',
       'results':evals,'limitations':['Cannot deduce syndrome order or corrections from final-only data.',
          'Initialization/gate/storage/readout errors are confounded in observed final outcomes.',
          'Readout probabilities must be independently obtained from same-device same-time calibration for mapped qubits.',
          'The null predictor is NOT a matched circuit-level noise simulation, and is not a calibrated surface-code prediction.'],
       'citation':'https://doi.org/10.5281/zenodo.20768087'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--verified-flat-csv',type=Path,required=True)
    p.add_argument('--backend',default='ibm_fez');p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    r=compare_from_verified_flat_table(a.verified_flat_csv,backend=a.backend)
    save_report(a.output_dir,'IBM_HARDWARE_NULL_COMPARISON',r,
       'Explicitly a final-bit majority baseline against a readout-only independent-flip null model; does NOT decode physical syndrome or validate logical-memory prediction.')
    print('Hardware baseline records:',len(r['results']), 'source scope:',r['scope'])
if __name__=='__main__':main()
