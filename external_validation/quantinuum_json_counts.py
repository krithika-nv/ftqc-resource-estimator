"""Independent count reanalysis of official Quantinuum hardware-specification JSON.

It is *not* Helios unless the source explicitly declares Helios. H2, H1,
REIMEI measurements are kept under their own device IDs. Averages of raw RB
survival do not directly estimate per-gate infidelity without a protocol fit.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from .core import wilson

def extract(path:Path,source_family='Quantinuum'):
    data=json.loads(path.read_text())
    shots=data.get('shots');survival=data.get('survival')
    if type(shots)!=int or shots<1 or not isinstance(survival,dict):raise ValueError('invalid public benchmark JSON')
    if path.stem not in ('SPAM','SQ_RB','TQ_RB','Memory_RB','Measurement_crosstalk','MCMR_crosstalk'):
        raise ValueError('unknown benchmark protocol')
    rows=[]
    for qubits,part in survival.items():
        if not isinstance(part,dict):raise ValueError('invalid survival nested dictionary')
        # SPAM: qubit -> prepared state -> success count.
        # RB: qubit -> sequence length -> repetition -> success count.
        for label,item in part.items():
            items=([('prepared_'+str(label),item)] if type(item)==int else
                   [(str(label)+'_rep_'+str(rep),count) for rep,count in item.items()] if isinstance(item,dict) else None)
            if items is None:raise ValueError('unexpected survival hierarchy')
            for experiment_key,count in items:
                if type(count)!=int or not 0<=count<=shots:raise ValueError('invalid shot count')
                ci=wilson(count,shots)
                rows.append({'qubits':str(qubits),'condition':experiment_key,'successes':count,
                             'shots':shots,'success_fraction':count/shots,'wilson95':ci['ci95']})
    if not rows:raise ValueError('no measured counts')
    return {'schema':'ftqc.quantinuum.public-json-counts.v1','provider':source_family,
            'device':path.parent.parent.name,'measurement_date':path.parent.name,
            'benchmark_protocol':path.stem,'data_kind':'public_executed_hardware_shots',
            'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'n_conditions':len(rows),'rows':rows,
            'limitations':['A protocol-specific RB/SPAM fit is required to infer gate errors.',
                           'These data may describe H-series or REIMEI, NOT Helios; device identities must not be conflated.',
                           'Not an independently reproduced Helios paper figure or logical-QEC validation.']}

def run(source:Path,out:Path):
    paths=sorted(source.rglob('SPAM.json'))+sorted(source.rglob('TQ_RB.json'))
    reports=[]
    for p in paths:
        if 'quantinuum' not in str(source).lower() and source.is_dir():
            pass  # Source path is user-configured; device is derived from directory structure.
        reports.append(extract(p))
    if not reports:raise ValueError('no public Quantinuum numeric benchmark JSON found')
    result={'schema':'ftqc.quantinuum.public-counts-collection.v1','n_experiments':len(reports),
            'reports':reports,'helios_independently_reproduced':False}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=run(a.source,a.output);print('Quantinuum public numerical experiments:',r['n_experiments'])
if __name__=='__main__':main()
