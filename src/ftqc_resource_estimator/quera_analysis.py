"""Randomized-measurement two-copy kernel for neutral-atom experiments.

The purity formula assumes independent local 2-design randomizations. QuEra
Aquila's disorder/randomized-measurement protocol does NOT automatically match
this assumption; default output is therefore kernel diagnostic, not physical
entanglement/purity measured from the paper.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from .evidence_analysis import read_csv, integer,file_hash,save_report


def estimate_two_copy_kernel(path:Path, *, validated_design=False) -> dict:
    rows=read_csv(path,('randomization_id','bitstring','count'))
    sets=defaultdict(lambda:defaultdict(int));length=None
    for r in rows:
        bits=r['bitstring'];rid=r['randomization_id']
        if not rid or not bits or any(c not in '01' for c in bits):raise ValueError('expected bitstrings, must be 0/1')
        if length is None:length=len(bits)
        if len(bits)!=length or length>20:raise ValueError('inconsistent bitstring length or too many qubits')
        sets[rid][bits]+=integer(r['count'],'count',1)
    per=[]
    for rid,hist in sorted(sets.items()):
        n=sum(hist.values())
        if n<2:raise ValueError('at least two shots needed per randomization')
        acc=0.0
        for a,na in hist.items():
            for b,nb in hist.items():
                # ordered distinct shots (remove self-pairs)
                ordered=na*(nb-(a==b))
                dist=sum(x!=y for x,y in zip(a,b))
                acc+=ordered*((-0.5)**dist)
        purity=(2**length)*acc/(n*(n-1))
        per.append({'randomization_id':rid,'n_shots':n,'two_copy_kernel_value':purity})
    mean=sum(r['two_copy_kernel_value'] for r in per)/len(per)
    return {'scope': 'CONDITIONAL_LOCAL_2DESIGN_PURITY_ESTIMATOR' if validated_design else 'KERNEL_DIAGNOSTIC_ONLY_PROTOCOL_NOT_VERIFIED',
      'source_file_sha256':file_hash(path),'num_qubits':length,'randomization_settings':len(per),
      'mean_kernel':mean,'per_setting':per,'entanglement_measurement_claim_authorized':False,
      'requires':['same randomization defines identical local controls','randomization ensemble shown to be a local unitary 2-design',
       'shot counts represent independent executions of that setting','bias/cross-talk/SPAM and finite-randomization uncertainty evaluated'],
      'citation':'https://arxiv.org/abs/2604.24854'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--normalized-counts',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    out=estimate_two_copy_kernel(a.normalized_counts)
    save_report(a.output_dir,'NEUTRAL_ATOM_RANDOMIZED_MEASUREMENTS',out,
      'This is an independently computed second-moment kernel. The QuEra protocol cannot be declared equivalent to local 2-design measurements without protocol validation.')
    print('Neutral-atom kernel:',out['mean_kernel'],'scope:',out['scope'])
if __name__=='__main__':main()
