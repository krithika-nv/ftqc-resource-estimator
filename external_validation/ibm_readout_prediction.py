"""Measured-parameter IBM *readout-only* majority-decoding prediction.

This is an independently specified baseline derived from device calibration
p(measured 1|prepared 0) or p(measured 0|prepared 1), not an FTQC logical-noise
model. Unlike empirical fits to observed code failures, predictions do not use
experimental logical outcomes as model parameters. Decoherence, CZ, syndrome
faults, and correlations are deliberately excluded and identified as residuals.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,tarfile
from collections import defaultdict
from pathlib import Path
from .core import wilson

MEASURE = re.compile(r'\b(c_data_[\w]+)\s*\[\s*(\d+)\s*\]\s*=\s*measure\s+\$(\d+)\s*;')

def majority_error(probabilities):
    """Poisson-binomial majority tail, no IID approximation."""
    if len(probabilities)%2!=1 or not probabilities:raise ValueError('odd-distance data register required')
    dp=[1.0]+[0.0]*len(probabilities)
    for p in probabilities:
        if not 0<=p<=1:raise ValueError('invalid calibrated readout probability')
        for k in range(len(probabilities),0,-1):dp[k]=dp[k]*(1-p)+dp[k-1]*p
        dp[0]*=(1-p)
    return sum(dp[(len(probabilities)//2)+1:])

def data_map(qasm):
    out=defaultdict(dict)
    for name,bit,qubit in MEASURE.findall(qasm):
        bit=int(bit);qubit=int(qubit)
        if bit in out[name]:raise ValueError('duplicate data-bit measurement')
        out[name][bit]=qubit
    if not out:raise ValueError('no physical-to-classical data mapping')
    return {n:[bits[i] for i in range(len(bits))] for n,bits in out.items() if set(bits)==set(range(len(bits)))}

def extract_readout(calibration,state,qubits):
    key=('prob_meas1_prep0' if state==0 else 'prob_meas0_prep1')
    out=[]
    for q in qubits:
        entries={e.get('name'):e.get('value') for e in calibration['qubits'][q] if isinstance(e,dict)}
        p=entries.get(key)
        if not isinstance(p,(int,float)) or not 0<=p<=1:raise ValueError(f'no calibrated {key} for qubit {q}')
        out.append(float(p))
    return out

def predict(archive:Path,decoded_csv:Path,output:Path,max_jobs=None):
    # Use explicit original source shots only to assess the pre-specified calibration model.
    grouped=defaultdict(lambda:[0,0]); seen_decoders=set()
    with decoded_csv.open(newline='') as f:
        for r in csv.DictReader(f):
            seen_decoders.add(r['decoder'])
            snapshot=r['snapshot_id'];state=int(r['initial_state']);chain=r['chain']
            if state not in (0,1):raise ValueError('invalid prepared state')
            key=(snapshot,state,chain)
            grouped[key][1]+=1
            grouped[key][0]+=int(r['logical_failure'])
    if seen_decoders != {'majority'}:raise ValueError('readout-only prediction requires majority-decoded observations, not MWPM')
    by_snapshot=defaultdict(list)
    for key in grouped:by_snapshot[key[0]].append(key)
    predictions=[];skipped=[]
    # Single streaming pass through original compressed evidence, avoiding
    # repeated random gzip seeks on ~567 MB of decompressed records.
    cached=defaultdict(dict)
    selected=set(sorted(by_snapshot)[:max_jobs])
    with tarfile.open(archive,'r|gz') as tf:
        for member in tf:
            if not member.isfile() or '/' not in member.name:continue
            prefix,name=member.name.rsplit('/',1)
            if prefix in selected and name in ('calibration.json','circuit_state0.qasm','circuit_state1.qasm'):
                if member.size>8_000_000:raise ValueError('unexpectedly large calibration/QASM member')
                cached[prefix][name]=tf.extractfile(member).read()
    for snap in sorted(selected):
        try:
            cal=json.loads(cached[snap]['calibration.json'])
            for state in (0,1):
                qasm=cached[snap][f'circuit_state{state}.qasm'].decode()
                mapping=data_map(qasm)
                for _,s,chain in by_snapshot[snap]:
                    if s!=state:continue
                    if chain.startswith('c_data_'):
                        register=chain
                    elif chain.isdecimal():
                        declaration_order=re.findall(r'\bbit\s*\[\s*\d+\s*\]\s*(c_data_\w+)\s*;',qasm)
                        if int(chain)>=len(declaration_order):raise ValueError('chain index outside QASM registers')
                        register=declaration_order[int(chain)]
                    else: raise ValueError('unmapped chain key')
                    if register not in mapping:raise ValueError('missing or ambiguous chain mapping '+register)
                    qubits=mapping[register]
                    probabilities=extract_readout(cal,state,qubits)
                    expected=majority_error(probabilities)
                    failures,shots=grouped[(snap,state,chain)]
                    bounds=wilson(failures,shots)
                    predictions.append({'snapshot_id':snap,'chain':chain,'state':state,'qubits':qubits,
                      'measured_majority_failure':failures/shots,'failures':failures,'shots':shots,
                      'observed_wilson95':bounds['ci95'],
                      'calibration_readout_only_prediction':expected,
                      'residual_observed_minus_readout_only':failures/shots-expected})
        except (KeyError,ValueError) as exc:skipped.append({'snapshot_id':snap,'reason':str(exc)})
    h=hashlib.sha256(archive.read_bytes()).hexdigest()
    report={'schema':'ftqc.ibm.readout-only-calibration-prediction.v1','source_archive_sha256':h,
      'comparison_count':len(predictions),'skipped_snapshots':skipped,
      'status':'measured_parameter_readout_only_baseline_NOT_circuit_matched_QEC',
      'experimental_observables_used_as_fit_parameters':False,
      'limitations':['QASM physical data mapping validated; syndrome decoding not used as physical-noise prediction.',
                     'Assumes independent calibrated terminal readout flips; no CZ, midcircuit measurement, idle, leakage or correlated faults.',
                     'Same-epoch calibration is not an independently time-held-out noise model.',
                     'Comparison uses majority-decoded hardware observations, not MWPM logical failure.'],
      'comparisons':predictions}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--decoded',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--max-jobs',type=int)
    a=p.parse_args();r=predict(a.archive,a.decoded,a.output,max_jobs=a.max_jobs)
    print('Readout-only calibrated predictions:',r['comparison_count'],'excluded:',len(r['skipped_snapshots']))
if __name__=='__main__':main()
