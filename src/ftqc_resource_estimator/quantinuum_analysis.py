"""Quantinuum trusted numeric benchmark analyser, with exact binomial intervals.

Unsafe serialized (.p/.pickle) upstream files are never deserialized. Export
trusted files to a transparent CSV in a separately controlled workflow.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from .evidence_analysis import read_csv, integer, file_hash, wilson,save_report


def analyze_benchmark_csv(path:Path, *, expected_provider='Quantinuum', heldout_required=False):
    rows=read_csv(path,('source_id','processor','experiment','successes','shots','data_kind','provider'))
    groups=defaultdict(lambda:[0,0,0])
    for r in rows:
        if r['provider']!=expected_provider:raise ValueError('provider mismatch')
        kind=r['data_kind']
        if kind!='executed_hardware_shots':
            raise ValueError('This binomial analyser accepts measured executed shots only; specifications must be analyzed separately')
        if heldout_required and kind!='executed_hardware_shots':raise ValueError('held-out outcome requires hardware shots')
        shots=integer(r['shots'],'shots',1); success=integer(r['successes'],'successes')
        if success>shots:raise ValueError('successes exceed shots')
        if not all(r.get(k) for k in ('source_id','experiment','processor')):
            raise ValueError('need source_id/processor/experiment')
        key=(r['source_id'],r['processor'],r['experiment'],kind)
        val=groups[key];val[0]+=success;val[1]+=shots;val[2]+=1
    results=[]
    for (source,device,exp,kind), (success,shots,n) in sorted(groups.items()):
        low,high=wilson(success,shots)
        results.append({'source_id':source,'processor':device,'experiment':exp,'kind':kind,
            'successes':success,'shots':shots,'records':n,'empirical_success_rate':success/shots,
            'wilson95':[low,high]})
    return {'scope':'TRUSTED_NUMERIC_HELIOS_BENCHMARK_ANALYSIS_NO_CLAIM_OF_REPRODUCED_FIGURE',
      'input_sha256':file_hash(path),'benchmarks':results,
      'warnings':['Published specifications are not independent hardware trials.',
          'The CSV must be independently verified against source measurements and definitions.',
          'Do not treat opaque upstream Python pickle files as numeric data.'],
      'citation':'https://github.com/Quantinuum/Helios-paper-data'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--trusted-csv',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    result=analyze_benchmark_csv(a.trusted_csv)
    save_report(a.output_dir,'ION_BENCHMARK_ANALYSIS',result,'Numerical binomial statistics computed from a source-verified flat CSV. No opaque pickle objects are executed; input provenance must be checked.')
    print('Trapped-ion benchmark analysis generated:',a.output_dir)
if __name__=='__main__':main()
