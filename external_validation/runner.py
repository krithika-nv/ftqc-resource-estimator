"""Analysis-validation CLI. Normalized data always require source-field provenance."""
import argparse, collections, csv, json, math, sys
from pathlib import Path
from .core import digest, integer, read_csv, source_manifest, wilson, write_json


def ibm(args):
    """Report actual repetition-code failure rates and genuinely disjoint holdouts.

    Calibration epochs are NEVER synthesized from shot indices. For single-epoch
    records, a predeclared within-job *physical-chain* split estimates transfer
    to another chain; it is not temporal generalization or a calibrated noise
    prediction. Temporal comparisons require the identical protocol at two
    distinct, source-declared calibration timestamps.
    """
    required={'epoch','shot_id','distance','observed_logical','predicted_logical'}
    grouped=collections.defaultdict(lambda:[0,0])
    protocol_epoch=collections.defaultdict(lambda:[0,0])
    chain_counts=collections.defaultdict(lambda:[0,0])
    seen=set(); nrows=0
    with open(args.input,newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('missing required decoded-shot columns: '+str(sorted(required-set(reader.fieldnames or []))))
        has_chains={'snapshot_id','rounds','basis','initial_state','chain','decoder'}.issubset(reader.fieldnames)
        for r in reader:
            nrows+=1
            key=(r['epoch'],r['shot_id'])
            if key in seen:raise ValueError(f'duplicate shot: {key}')
            seen.add(key)
            d=integer(r['distance'],'distance')
            if d<2:raise ValueError('distance must be >=2')
            obs=integer(r['observed_logical'],'observed_logical')
            pred=integer(r['predicted_logical'],'predicted_logical')
            if obs not in (0,1) or pred not in (0,1):raise ValueError('logical bits must be 0 or 1')
            epoch=integer(r['epoch'],'epoch')
            fail=int(obs!=pred)
            grouped[(epoch,d)][0]+=fail;grouped[(epoch,d)][1]+=1
            if has_chains:
                rounds=integer(r['rounds'],'rounds')
                init=integer(r['initial_state'],'initial_state')
                chain=integer(r['chain'],'chain')
                if rounds<1 or init not in (0,1) or chain<0:raise ValueError('invalid physical protocol attributes')
                basis=r['basis']; decoder=r['decoder']; snapshot=r['snapshot_id']
                if not basis or not decoder or not snapshot:raise ValueError('missing source protocol identifier')
                # Calibration comparison must use SAME circuit/decoder protocol.
                protocol=(r.get('backend','unspecified'),d,rounds,basis,init,decoder,
                          r.get('decoder_model','unspecified'))
                protocol_epoch[(epoch,protocol)][0]+=fail
                protocol_epoch[(epoch,protocol)][1]+=1
                # Strictly disjoint hardware acquisition chain, not a shot split.
                chain_counts[(snapshot,epoch,protocol,chain)][0]+=fail
                chain_counts[(snapshot,epoch,protocol,chain)][1]+=1
    if not nrows:raise ValueError('empty dataset')
    epochs=sorted({e for e,d in grouped})
    results=[{'epoch':e,'distance':d,**wilson(fail,n)} for (e,d),(fail,n) in sorted(grouped.items())]
    training=[];heldout=[];temporal=[]
    if len(epochs)>=2 and has_chains:
        cutoff=max(1,math.floor(len(epochs)*(1-args.holdout_fraction)))
        cutoff=min(cutoff,len(epochs)-1)
        training=epochs[:cutoff];heldout=epochs[cutoff:]
        # Predeclare epoch holdout using ONLY earlier epoch data for fitting.
        train_by_protocol=collections.defaultdict(lambda:[0,0])
        for (epoch,proto),(fail,n) in protocol_epoch.items():
            if epoch in training:
                train_by_protocol[proto][0]+=fail;train_by_protocol[proto][1]+=n
        for (epoch,proto),(fail,n) in sorted(protocol_epoch.items()):
            if epoch not in heldout or proto not in train_by_protocol:continue
            tf,tn=train_by_protocol[proto]
            p=(tf+0.5)/(tn+1.0)  # Jeffreys smoothing, fixed in advance
            temporal.append({'holdout_epoch':epoch,'protocol':{'distance':proto[1],'rounds':proto[2],
                'basis':proto[3],'initial_state':proto[4],'decoder':proto[5],
                            'backend':proto[0],'decoder_model':proto[6]},
                'training':wilson(tf,tn),'holdout':wilson(fail,n),
                'prediction':p,'residual':fail/n-p,
                'meaning':'historically distinct calibration epochs for same decoded protocol; not a circuit-matched noise prediction'})
    # Support legacy synthetic test fixture lacking full protocol fields: display
    # epochs but refuse to call unmatched-configuration holdout predictive.
    elif len(epochs)>=2:
        cutoff=max(1,math.floor(len(epochs)*(1-args.holdout_fraction)))
        cutoff=min(cutoff,len(epochs)-1)
        training=epochs[:cutoff];heldout=epochs[cutoff:]
    for rec in results:
        rec['split']='train' if rec['epoch'] in training else 'holdout' if rec['epoch'] in heldout else 'descriptive'
    physical=collections.defaultdict(dict)
    for (snapshot,epoch,protocol,chain),counts in chain_counts.items():
        physical[(snapshot,epoch,protocol)][chain]=counts
    spatial=[]
    for (snapshot,epoch,proto),chains in sorted(physical.items()):
        if len(chains)<2:continue
        # Rule fixed by index, never selected for a favorable observed rate.
        hold_chain=max(chains)
        hf,hn=chains[hold_chain]
        tf=sum(v[0] for k,v in chains.items() if k!=hold_chain)
        tn=sum(v[1] for k,v in chains.items() if k!=hold_chain)
        p=(tf+0.5)/(tn+1.0)
        spatial.append({'snapshot_id':snapshot,'epoch':epoch,
            'protocol':{'backend':proto[0],'distance':proto[1],'rounds':proto[2],
                        'basis':proto[3],'initial_state':proto[4],'decoder':proto[5],
                        'decoder_model':proto[6]},
            'train_chains':sorted(k for k in chains if k!=hold_chain),
            'holdout_chain':hold_chain,'training':wilson(tf,tn),
            'holdout':wilson(hf,hn),'prediction':p,'residual':hf/hn-p})
    per_protocol=[{'epoch':e,'protocol':{'backend':p[0],'distance':p[1],'rounds':p[2],
                     'basis':p[3],'initial_state':p[4],'decoder':p[5],'decoder_model':p[6]},
                     **wilson(*v)} for (e,p),v in sorted(protocol_epoch.items())]
    out={'analysis':'ibm_decoded_repetition_shots','data_level':'source-mapped-decoded-shots-not-vendor-raw',
        'source':source_manifest([args.input]),'total_rows':nrows,
        'calibration_epoch_count':len(epochs),'calibration_epochs':epochs,
        'held_out_epochs':heldout,'training_epochs':training,'by_epoch_distance':results,
        'by_epoch_protocol':per_protocol,
        'by_epoch_distance_caveat':'These aggregate different bases, rounds and prepared states; use by_epoch_protocol for matched scientific comparisons.',
        'temporal_holdout':{'status':'matched_protocol_evaluation_available' if temporal else
            'unavailable_no_matched_decoded_protocol_across_epochs' if len(epochs)>1 else
            'unavailable_single_decoded_calibration_epoch',
            'matched_protocol_evaluations':temporal,
            'method':'fit on earlier calibration epochs; test on later epochs only with identical (backend, distance, rounds, basis, prepared state, decoder and model)',
            'caveat':'Distinct calibration timestamps do not prove distinct execution times; verify source chronology and decoder training independently.'},
        'cross_chain_holdout':{'status':'evaluated' if spatial else 'unavailable_no_source_verified_chain_identity',
            'evaluated_conditions':len(spatial),'evaluations':spatial,
            'method':'predeclared highest chain index held out; other chains within same source job used to fit empirical failure probability',
            'caveat':'This is observed out-of-chain empirical error-rate generalization on the same device/calibration, NOT an independent later-epoch test or calibrated circuit-level physical model. Physical chains can share correlated noise.'},
        'scientific_scope':'hardware repetition-code decoded-error analysis only; not demonstrated surface-code memory, logical gates or universal FTQC prediction'}
    write_json(args.output,out)


def neutral(args):
    rows=read_csv(args.input,{'shot_id','distance','rounds','logical_failure','atom_loss','decoder'})
    if not rows:raise ValueError('empty dataset')
    groups=collections.defaultdict(lambda:[0,0]); seen=set()
    for r in rows:
        dist=integer(r['distance'],'distance'); rounds=integer(r['rounds'],'rounds')
        if rounds<=0 or dist<=0:raise ValueError('rounds/distance must be positive')
        lf=integer(r['logical_failure'],'logical_failure');loss=integer(r['atom_loss'],'atom_loss')
        if lf not in (0,1) or loss not in (0,1):raise ValueError('binary fields must be 0/1')
        k=(r['shot_id'],dist,rounds,r['decoder'])
        if k in seen:raise ValueError(f'duplicate neutral shot+decoder: {k}')
        seen.add(k)
        groups[(dist,rounds,r['decoder'],'loss' if loss else 'no_loss')][0]+=lf
        groups[(dist,rounds,r['decoder'],'loss' if loss else 'no_loss')][1]+=1
    result=[{'distance':d,'rounds':n,'decoder':decoder,'loss_stratum':stratum,**wilson(*counts)} for (d,n,decoder,stratum),counts in sorted(groups.items())]
    out={'analysis':'neutral_atom_source_decoded_logical_shots','data_level':'verified-decoder-outputs-required',
         'source':source_manifest([args.input]),'groups':result,
         'warning':'No atom-loss-aware maximum-likelihood or neural decoder is implemented here. No distance-5/distance-3 per-round suppression factor can be inferred from mixed round-count or conditioning strata.'}
    write_json(args.output,out)


def helios(args):
    rows=read_csv(args.input,{'benchmark','condition','successes','trials','source_file','source_key'})
    if not rows:raise ValueError('empty dataset')
    groups=collections.defaultdict(lambda:[0,0]); records=[]
    for r in rows:
        a=integer(r['successes'],'successes'); b=integer(r['trials'],'trials')
        if not 0<=a<=b or b==0:raise ValueError('invalid counts')
        if not all(r[x].strip() for x in ('benchmark','condition','source_file','source_key')):raise ValueError('source provenance missing')
        groups[(r['benchmark'],r['condition'])][0]+=a;groups[(r['benchmark'],r['condition'])][1]+=b
        records.append({'benchmark':r['benchmark'],'condition':r['condition'],'source_file':r['source_file'],'source_key':r['source_key']})
    out={'analysis':'helios_verified_trial_counts','source':source_manifest([args.input]),'source_records':records,
         'groups':[{'benchmark':b,'condition':c,**wilson(counts[0],counts[1]),'successes':counts[0]} for (b,c),counts in sorted(groups.items())],
         'warning':'Counts must be independently verified against exact paper records; success rate is not interchangeable with physical gate fidelity.'}
    write_json(args.output,out)


def aurora(args):
    try:import openpyxl
    except ImportError as e:raise RuntimeError('install openpyxl using python3 -m pip install openpyxl') from e
    wb=openpyxl.load_workbook(args.input,read_only=True,data_only=True)
    sheets=[]
    for ws in wb:
        samples=[]; nonempty=0
        for row in ws.iter_rows(values_only=True):
            if not any(v is not None for v in row):continue
            nonempty+=1
            if len(samples)<args.preview_rows:samples.append([str(v)[:120] if v is not None else None for v in row[:15]])
        sheets.append({'sheet':ws.title,'nonempty_rows':nonempty,'preview':samples})
    out={'analysis':'aurora_workbook_schema_inventory','source':source_manifest([args.input]),'sheets':sheets,
         'warning':'This is workbook inspection, not published-figure reproduction; precise figure sheet, axes, units, and chart transformation must be confirmed.'}
    write_json(args.output,out)


def inspect(args):
    p=Path(args.input)
    if p.is_dir():
        files=sorted(x for x in p.rglob('*') if x.is_file())
        out={'analysis':'source_inventory','files':[{'path':str(x.relative_to(p)),'bytes':x.stat().st_size,'sha256':digest(x) if x.stat().st_size<=args.max_hash_bytes else None} for x in files[:args.max_files]],'total_files':len(files)}
    else:out={'analysis':'source_inventory','source':source_manifest([p])}
    write_json(args.output,out)


def main():
    p=argparse.ArgumentParser(description='External hardware analysis validation')
    sub=p.add_subparsers(dest='command',required=True)
    for name,fn in [('ibm',ibm),('neutral',neutral),('helios',helios),('aurora',aurora),('inspect',inspect)]:
        x=sub.add_parser(name);x.add_argument('--input',required=True);x.add_argument('--output',required=True)
        if name=='ibm':x.add_argument('--holdout-fraction',type=float,default=.25)
        if name=='aurora':x.add_argument('--preview-rows',type=int,default=8)
        if name=='inspect':x.add_argument('--max-files',type=int,default=300);x.add_argument('--max-hash-bytes',type=int,default=100000000)
        x.set_defaults(run=fn)
    args=p.parse_args()
    if args.command=='ibm' and not 0<args.holdout_fraction<1:p.error('holdout fraction must be between 0 and 1')
    try:args.run(args)
    except (ValueError,RuntimeError,FileNotFoundError) as e:print(f'ERROR: {e}',file=sys.stderr);sys.exit(2)

if __name__=='__main__':main()
