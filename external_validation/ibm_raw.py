"""Auditable IBM repetition-code raw-shot decoder (Zenodo 20768087).

Experimental source: Stein et al., doi:10.5281/zenodo.20768087.
Uses QASM-declared registers; never infers physical FTQC performance from a
phenomenological decoder. The tested baseline is *unweighted* majority or
phenomenological MWPM, NOT the authors' calibrated MWPM/FiLM model.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import re
import tarfile
import gzip
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .core import wilson, write_json

REQUIRED = ('info.json', 'calibration.json', 'bitstrings.json', 'circuit_state0.qasm', 'circuit_state1.qasm')
COLUMNS = ['epoch','shot_id','distance','observed_logical','predicted_logical',
           'snapshot_id','backend','rounds','basis','initial_state','chain',
           'decoder','decoder_model','logical_failure','calibration_utc']
MD5 = {'ibm_fez':'27ce2827dde0713a436179121bfd7173',
       'ibm_kingston':'7ed09b461e962c174cedb6c7ee44018b',
       'ibm_pittsburgh':'be1614be0ab19664517b760a8b2bf5bd'}


def sha(b:bytes):return hashlib.sha256(b).hexdigest()


def qasm_registers(source:str)->dict:
    """Require explicit c_data and c_syndrome registers in original QASM."""
    # Remove line/block comments before reading declarations.
    clean=re.sub(r'/\*.*?\*/','',source,flags=re.S)
    clean=re.sub(r'//[^\n]*','',clean)
    decls=[]
    for m in re.finditer(r'\bcreg\s+([\w]+)\s*\[\s*(\d+)\s*\]\s*;|\bbit\s*\[\s*(\d+)\s*\]\s+([\w]+)\s*;',clean):
        name=m[1] or m[4];size=int(m[2] or m[3]);decls.append((name,size))
    if not decls: raise ValueError('executed QASM has no recognizable classical-register declarations')
    found={}
    for name,size in decls:
        if name in found:raise ValueError('duplicate classical register in executed QASM')
        found[name]=size
    return found


def _declared_pairs(qasm:str,d:int,rounds:int,n_chains:int):
    decl=qasm_registers(qasm)
    data=[n for n in decl if n.startswith('c_data_')]
    syndrome=[n for n in decl if n.startswith('c_syndrome_')]
    if len(data)!=n_chains or len(syndrome)!=n_chains:
        raise ValueError(f'QASM register pairs {len(data)}/{len(syndrome)} != n_chains {n_chains}')
    # When source register names use the same physical-chain suffix, match
    # explicitly; older regression fixtures instead distinguish data/ancilla
    # qubit lists and retain their declared pair order.
    syndrome_by_chain={name.removeprefix('c_syndrome_'):name for name in syndrome}
    if {name.removeprefix('c_data_') for name in data}==set(syndrome_by_chain):
        pairs=[(name,syndrome_by_chain[name.removeprefix('c_data_')]) for name in data]
    else:
        pairs=list(zip(data,syndrome))  # nonmatching suffix pairing remains unverified
    if len(set(pairs))!=n_chains:raise ValueError('ambiguous QASM pairing')
    for dn,sn in pairs:
        if decl[dn]!=d or decl[sn]!=(d-1)*rounds:
            raise ValueError(f'QASM register widths not compatible with repetition d={d}, rounds={rounds}: {dn}={decl[dn]} {sn}={decl[sn]}')
    # Inspect actual OpenQASM 2 and 3 measurement assignments. IBM hardware
    # execution QASM 3 uses `$127` physical qubit identifiers, not q[127].
    # Preserve register bit indices, independent of statement interleaving.
    measurements=[]
    physical=r'(?:\$\d+|[A-Za-z_]\w*\s*\[\s*\d+\s*\])'
    for statement in qasm.split(';'):
        if 'measure' not in statement:continue
        a=re.search(r'\bmeasure\s+'+physical+r'\s*->\s*(\w+)\s*\[\s*(\d+)\s*\]',statement)
        b=re.search(r'(\w+)\s*\[\s*(\d+)\s*\]\s*=\s*measure\s+'+physical,statement)
        if a or b:
            m=a or b;measurements.append((m[1],int(m[2])))
    for dn,sn in pairs:
        for name,expected in ((dn,d),(sn,(d-1)*rounds)):
            indexes=[idx for reg,idx in measurements if reg==name]
            if sorted(indexes)!=list(range(expected)):
                raise ValueError(f'QASM must measure each {name} bit exactly once; observed {len(indexes)} assignments')
        time_order=[idx for reg,idx in measurements if reg==sn]
        if time_order!=list(range((d-1)*rounds)):
            raise ValueError(f'QASM syndrome measurement order for {sn} is not time-major; refusing unsound detector mapping')
        last_syn=max(i for i,(reg,_) in enumerate(measurements) if reg==sn)
        first_data=min(i for i,(reg,_) in enumerate(measurements) if reg==dn)
        if first_data<last_syn:raise ValueError('QASM data readout occurs before final syndrome; unsupported protocol')
    return pairs


def _state_objects(blob):
    """Parse prepared-state records without guessing order or shot encoding.

    Real Stein/IBM data are two records with metadata.logical_state and
    per_shot_cregs. Named fixtures remain supported for backward compatibility.
    """
    candidates=(('0','1'),('state0','state1'),('state_0','state_1'),
                ('circuit_state0','circuit_state1'))
    if isinstance(blob,dict):
        for k0,k1 in candidates:
            if k0 in blob and k1 in blob and isinstance(blob[k0],dict) and isinstance(blob[k1],dict):
                return [(0,blob[k0]),(1,blob[k1])]
        for nested in ('states','circuits','results','data'):
            if nested in blob and isinstance(blob[nested],(dict,list)):
                try:return _state_objects(blob[nested])
                except ValueError:pass
    if isinstance(blob,list) and len(blob)==2:
        # Authenticated physical data use explicit *per-record* metadata.
        keyed={}
        for item in blob:
            if not isinstance(item,dict):break
            meta=item.get('metadata')
            state=(meta or {}).get('logical_state') if isinstance(meta,dict) else None
            if str(state) not in ('0','1'):break
            regs=item.get('per_shot_cregs')
            if not isinstance(regs,dict) or not any(k.startswith('c_data_') for k in regs):break
            if int(state) in keyed:raise ValueError('duplicate physical prepared-state metadata')
            keyed[int(state)]=regs
        if set(keyed)=={0,1}:return sorted(keyed.items())
        if any(isinstance(item,dict) and 'per_shot_cregs' in item for item in blob):
            raise ValueError('physical shot records require explicit, distinct metadata.logical_state')
        if all(isinstance(item,dict) and any(k.startswith('c_data_') for k in item)
               and any(k.startswith('c_syndrome_') for k in item) for item in blob):
            return [(0,blob[0]),(1,blob[1])]
        keyed={}
        for item in blob:
            if not isinstance(item,dict):break
            raw_state=item.get('state',item.get('prepared_state',item.get('logical_state')))
            if str(raw_state) not in ('0','1'):break
            registers=item.get('registers',item.get('data'))
            if not isinstance(registers,dict):break
            keyed[int(raw_state)]=registers
        if set(keyed)=={0,1}:return sorted(keyed.items())
    raise ValueError('unrecognized state partition in bitstrings.json (inspect source-schema preview)')


def _structure_preview(value,depth=0):
    """Safe JSON structure summary, with examples of keys and shapes only."""
    if depth>=3:return {'type':type(value).__name__}
    if isinstance(value,list):
        return {'type':'list','length':len(value),
                'first':_structure_preview(value[0],depth+1) if value else None,
                'second':_structure_preview(value[1],depth+1) if len(value)>1 else None}
    if isinstance(value,dict):
        keys=list(value)
        return {'type':'dict','length':len(keys),'keys':keys[:10],
                'first_value':_structure_preview(value[keys[0]],depth+1) if keys else None}
    return {'type':type(value).__name__}


def _coerce_array(value,name):
    if isinstance(value,dict):
        if set(value)=={'array'}:value=value['array']
        elif set(value)=={'bits'}:value=value['bits']
        else:raise ValueError(f'{name} has unrecognized register wrapper {list(value)[:8]}')
    if not isinstance(value,list) or not value:raise ValueError(f'{name} must be nonempty list of shot bit-arrays')
    return value


def _bits(value,width,name):
    # Qiskit bit-array rows are lists with c[0],c[1],... ordering; avoid
    # silently reversing a packed string which has display-big-endian order.
    if not isinstance(value,list) or len(value)!=width or any(type(b) is not int or b not in (0,1) for b in value):
        raise ValueError(f'{name}: expected explicit {width}-element 0/1 list (ambiguous packed bitstrings are refused)')
    return tuple(value)


def inspect_archive(archive:Path, backend:str, max_jobs:int|None=None):
    """Return safe structural preview without exporting individual shots."""
    jobs=[]
    with tarfile.open(archive,'r:*') as tf:
        members={m.name:m for m in tf if m.isfile()}
        paths=sorted(x for x in members if x.endswith('/info.json') and backend in x.split('/'))
        for info_path in paths[:max_jobs]:
            prefix=info_path[:-len('info.json')]
            if any(prefix+n not in members for n in REQUIRED):raise ValueError(f'incomplete evidence job {prefix}')
            info=json.load(tf.extractfile(members[info_path]))
            blob=json.load(tf.extractfile(members[prefix+'bitstrings.json']))
            preview={'snapshot_id':prefix.rstrip('/'),'info_keys':sorted(info),
                     'raw_root_keys':list(blob)[:12] if isinstance(blob,dict) else f'root={type(blob).__name__}',
                     'raw_structure':_structure_preview(blob)}
            try:
                states=_state_objects(blob)
                preview['state_keys']={str(state):list(raw)[:16] for state,raw in states}
                preview['register_shapes']={str(state):{k:{'rows':len(v) if isinstance(v,list) else None,
                    'first_row_type':type(v[0]).__name__ if isinstance(v,list) and v else type(v).__name__,
                    'first_row_width':len(v[0]) if isinstance(v,list) and isinstance(v[0],list) else None}
                    for k,v in raw.items() if k.startswith(('c_data_','c_syndrome_'))}
                    for state,raw in states}
            except ValueError as exc:preview['schema_issue']=str(exc)
            for state in (0,1):
                q=tf.extractfile(members[prefix+f'circuit_state{state}.qasm']).read().decode('utf-8')
                try:preview[f'qasm_state{state}_registers']=qasm_registers(q)
                except ValueError as exc:preview[f'qasm_state{state}_issue']=str(exc)
            jobs.append(preview)
    return {'source':'https://doi.org/10.5281/zenodo.20768087','backend':backend,'inspected_jobs':len(jobs),'jobs':jobs}


def _matching(d,rounds,data_p,syndrome_p):
    try:import pymatching
    except ImportError as exc:raise RuntimeError('PyMatching is required: install into your existing Python interpreter') from exc
    m=pymatching.Matching()
    weight_data=math.log((1-data_p)/data_p)
    weight_meas=math.log((1-syndrome_p)/syndrome_p)
    checks=d-1
    def node(t,j):return t*checks+j
    # d*(rounds+1) data-error edges at post-initial time slices.
    for t in range(rounds+1):
        for i in range(d):
            if i==0:m.add_boundary_edge(node(t,0),weight=weight_data,fault_ids={0})
            elif i==d-1:m.add_boundary_edge(node(t,d-2),weight=weight_data)
            else:m.add_edge(node(t,i-1),node(t,i),weight=weight_data)
    # Noisily measured syndrome at each round creates adjacent-time detectors.
    for t in range(rounds):
        for j in range(checks):m.add_edge(node(t,j),node(t+1,j),weight=weight_meas)
    return m


def _detection_events(data,syndrome,d,rounds):
    checks=d-1
    if len(data)!=d or len(syndrome)!=checks*rounds:raise ValueError('logical observation width mismatch')
    prev=(0,)*checks;events=[]
    for t in range(rounds):
        now=syndrome[t*checks:(t+1)*checks]
        events.extend(a^b for a,b in zip(prev,now));prev=now
    final=tuple(data[j]^data[j+1] for j in range(checks))
    events.extend(a^b for a,b in zip(prev,final))
    return events


def _majority(data):return int(sum(data)>len(data)//2)


def _logical(matching,data,syndrome,d,rounds,mode):
    if mode=='majority':return _majority(data)
    correction=matching.decode(_detection_events(data,syndrome,d,rounds))
    if len(correction)!=1:raise ValueError('matching returned unexpected number of logical corrections')
    return data[0]^int(correction[0])


def _process_original(archive:Path,backend:str,output:Path,summary:Path,*,uncompressed_tar:Path,decoder='mwpm',
            data_p=.01,syndrome_p=.02,max_jobs=None,schema_only=False,skip_unsupported=False):
    if backend not in MD5:raise ValueError('unsupported backend')
    if not (0<data_p<.5 and 0<syndrome_p<.5):raise ValueError('phenomenological priors must be in (0,0.5)')
    if decoder not in ('mwpm','majority'):raise ValueError('unknown decoder')
    if max_jobs is not None and max_jobs<1:raise ValueError('max_jobs must be positive')
    structural=inspect_archive(uncompressed_tar,backend,max_jobs=max_jobs if schema_only else min(3,max_jobs or 3))
    structural_path=summary.with_name('IBM_SOURCE_SCHEMA.json')
    write_json(structural_path,structural)
    if schema_only:return {'status':'schema_inspected','schema_file':str(structural_path)}
    # MD5 is verified on fetch; recheck to ensure an unmodified downloaded archive.
    md5=hashlib.md5()
    with archive.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):md5.update(chunk)
    if md5.hexdigest()!=MD5[backend]:
        raise ValueError('archive MD5 mismatch against Zenodo release: refusing untrusted raw evidence')
    from ftqc_resource_estimator.modern_calibration import normalize_backend_properties,parse_timestamp
    output.parent.mkdir(parents=True,exist_ok=True)
    counts=Counter(); jobmeta=[]; skipped_jobs=[];source_hash=hashlib.sha256(archive.read_bytes()).hexdigest()
    matching_cache={}
    temp_output=output.with_suffix(output.suffix+'.partial')
    try:
        with tarfile.open(archive,'r:gz') as tf, temp_output.open('w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,fieldnames=COLUMNS);writer.writeheader()
            members={m.name:m for m in tf if m.isfile()}
            jobs=sorted(x for x in members if x.endswith('/info.json') and backend in x.split('/'))
            if not jobs:raise ValueError('no IBM jobs found in archive')
            for info_path in jobs[:max_jobs]:
                prefix=info_path[:-len('info.json')]
                if any(prefix+n not in members for n in REQUIRED):raise ValueError('incomplete experimental record: '+prefix)
                def getfile(name):return tf.extractfile(members[prefix+name]).read()
                info=json.loads(getfile('info.json'))
                if info.get('backend',info.get('device'))!=backend:raise ValueError('backend mismatch '+prefix)
                d=int(info.get('d',info.get('distance')));r=int(info['rounds']);shots=int(info['shots']);n=int(info['n_chains'])
                if d<3 or d%2!=1 or r<1 or n<1 or shots<1:raise ValueError('invalid repetition experiment metadata')
                props=normalize_backend_properties(json.loads(getfile('calibration.json')),backend_override=backend)
                date=parse_timestamp(props['calibration_timestamp_utc'])
                epoch=int(date.timestamp())
                blob=json.loads(getfile('bitstrings.json'))
                states=_state_objects(blob)
                if isinstance(blob,list):
                    logical=info.get('logical_states')
                    if logical not in ('0;1',[0,1],['0','1']):
                        raise ValueError('indexed state-list root requires explicit info.logical_states ordered 0;1')
                if {k for k,_ in states}!={0,1}:raise ValueError('both prepared logical states required')
                # Preflight both state circuits BEFORE writing any rows for a job.
                # This prevents a rejected protocol from contributing partial data.
                protocol_error=None
                for state,_ in states:
                    try:_declared_pairs(getfile(f'circuit_state{state}.qasm').decode('utf-8'),d,r,n)
                    except ValueError as exc:
                        protocol_error=str(exc);break
                if protocol_error is not None:
                    if not skip_unsupported:raise ValueError(f'{prefix}: {protocol_error}')
                    skipped_jobs.append({'snapshot_id':prefix.rstrip('/'),'reason':protocol_error})
                    continue
                all_counts=0
                for state,reg in states:
                    qasm=getfile(f'circuit_state{state}.qasm').decode('utf-8')
                    pairs=_declared_pairs(qasm,d,r,n)
                    recognized=set(sum(([a,b] for a,b in pairs),[]))
                    actual={k for k in reg if k.startswith(('c_data_','c_syndrome_'))}
                    if recognized!=actual:
                        raise ValueError(f'state{state} QASM/raw register mismatch: {sorted(recognized^actual)[:12]}')
                    for chain,(dn,sn) in enumerate(pairs):
                        dr=_coerce_array(reg[dn],dn);sr=_coerce_array(reg[sn],sn)
                        if len(dr)!=shots or len(sr)!=shots:
                            raise ValueError(f'shot counts do not match source info for {dn}/{sn}: {len(dr)}/{len(sr)} vs {shots}')
                        key=(d,r)
                        if decoder=='mwpm' and key not in matching_cache:
                            matching_cache[key]=_matching(d,r,data_p,syndrome_p)
                        m=matching_cache.get(key)
                        for shot,(dv,sv) in enumerate(zip(dr,sr)):
                            data=_bits(dv,d,dn);syndrome=_bits(sv,r*(d-1),sn)
                            estimated=_logical(m,data,syndrome,d,r,decoder)
                            error=int(estimated!=state)
                            writer.writerow(dict(epoch=epoch,shot_id=f'{prefix}|state{state}|chain{chain}|shot{shot}',
                                distance=d,observed_logical=state,predicted_logical=estimated,
                                snapshot_id=prefix.rstrip('/'),backend=backend,rounds=r,basis=info['basis'],
                                initial_state=state,chain=chain,decoder=decoder,decoder_model=('uniform_phenomenological' if decoder=='mwpm' else 'majority_baseline'),
                                logical_failure=error,calibration_utc=date.isoformat()))
                            counts[(d,r,info['basis'],state)]+=error
                            counts[(d,r,info['basis'],state,'trials')]+=1
                            all_counts+=1
                if all_counts!=shots*n*2:raise ValueError('per-job trial-count reconciliation failed')
                jobmeta.append({'snapshot_id':prefix.rstrip('/'),'calibration_utc':date.isoformat(),
                                'indexed_states':isinstance(blob,list),
                                'state_identity_from_metadata':isinstance(blob,list) and all(isinstance(x,dict) and isinstance(x.get('metadata'),dict) and 'logical_state' in x['metadata'] for x in blob),
                                'shots_per_circuit':shots,'chains':n,'samples':all_counts,
                                'raw_sha256':sha(getfile('bitstrings.json'))})
        temp_output.replace(output)
    finally:
        if temp_output.exists():temp_output.unlink()
    if not jobmeta:raise ValueError('no supported IBM jobs decoded')
    rows=[]
    for (d,r,basis,state),failures in sorted((k,v) for k,v in counts.items() if len(k)==4):
        trials=counts[(d,r,basis,state,'trials')]
        rows.append(dict(distance=d,rounds=r,basis=basis,initial_state=state,**wilson(failures,trials)))
    res={'status':'decoded_supported_subset' if skipped_jobs else 'decoded','decoder':decoder,'decoder_model':'uniform_phenomenological_not_calibration_matched' if decoder=='mwpm' else 'syndrome_independent_majority',
         'error_priors':{'data':data_p,'syndrome_measurement':syndrome_p} if decoder=='mwpm' else None,
         'source_doi':'10.5281/zenodo.20768087','source_archive_sha256':source_hash,
         'source_archive_md5':md5.hexdigest(),'output_csv':str(output),
         'csv_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
         'jobs':jobmeta,'skipped_jobs':skipped_jobs,'all_jobs_processed':not skipped_jobs and max_jobs is None,'total_decoded_chain_shots':sum(j['samples'] for j in jobmeta),
         'by_config':rows,'calibration_conditioned':False,
         'indexed_state_order_assumed':any(j.get('indexed_states',False) and not j.get('state_identity_from_metadata') for j in jobmeta),

         'matched_physical_noise_prediction_validated':False,
         'limitations':['QASM register width, per-register measurement order and raw metadata are checked; author preprocessing and qubit-to-check parity remain to be independently reproduced.',
          'MWPM uses explicitly stated uniform phenomenological weights, not circuit-derived detector error model or authors FiLM decoder.',
          'Decoded repetition-code failure rates do not validate surface-code or FTQC architecture estimates.']}
    write_json(summary,res);return res


def process(archive:Path,backend:str,output:Path,summary:Path,*,decoder='mwpm',
            data_p=.01,syndrome_p=.02,max_jobs=None,schema_only=False,skip_unsupported=False):
    """Spool an uncompressed TAR once to avoid repeated gzip seeks.

    The original checksum-verified archive remains untouched. The temporary
    data file is deleted on exit; an inflated-size cap limits storage risk.
    """
    if not archive.is_file():raise FileNotFoundError(archive)
    with tempfile.NamedTemporaryFile(prefix='ftqc_ibm_index_',suffix='.tar') as cache:
        size=0
        with gzip.open(archive,'rb') as raw:
            while True:
                block=raw.read(4*1024*1024)
                if not block:break
                size+=len(block)
                if size>1_500_000_000:raise ValueError('source TAR exceeds safe uncompressed size')
                cache.write(block)
        cache.flush()
        return _process_original(archive,backend,output,summary,uncompressed_tar=Path(cache.name),
                   decoder=decoder,data_p=data_p,syndrome_p=syndrome_p,max_jobs=max_jobs,
                   schema_only=schema_only,skip_unsupported=skip_unsupported)


def main(argv=None):
    p=argparse.ArgumentParser(description='Decode real IBM Zenodo raw repetition-code shots via QASM-mapped registers')
    p.add_argument('--archive',type=Path,default=Path('data/public_calibrations/2026/ibm_fez.tar.gz'))
    p.add_argument('--backend',choices=sorted(MD5),default='ibm_fez')
    p.add_argument('--output',type=Path,default=Path('data/verified/ibm_decoded_shots.csv'))
    p.add_argument('--summary',type=Path,default=Path('outputs/external_validation/ibm_raw_decode_summary.json'))
    p.add_argument('--decoder',choices=['mwpm','majority'],default='mwpm')
    p.add_argument('--data-error-prior',type=float,default=.01)
    p.add_argument('--syndrome-error-prior',type=float,default=.02)
    p.add_argument('--max-jobs',type=int)
    p.add_argument('--schema-only',action='store_true')
    p.add_argument('--skip-unsupported',action='store_true',help='Explicitly exclude jobs with incompatible QASM protocols, recording each exclusion')
    a=p.parse_args(argv)
    try:
        out=process(a.archive,a.backend,a.output,a.summary,decoder=a.decoder,data_p=a.data_error_prior,
                    syndrome_p=a.syndrome_error_prior,max_jobs=a.max_jobs,schema_only=a.schema_only,skip_unsupported=a.skip_unsupported)
        print(json.dumps({'status':out['status'],'source_schema':str(a.summary.with_name('IBM_SOURCE_SCHEMA.json')),
                          'decoded_chain_shots':out.get('total_decoded_chain_shots'),
                          'summary':str(a.summary),'csv':str(a.output)},indent=2))
    except (OSError,ValueError,RuntimeError,KeyError,tarfile.TarError) as exc:
        p.exit(2,f'ERROR: {exc}\nCheck outputs/external_validation/IBM_SOURCE_SCHEMA.json; no claims should be published.\n')

if __name__=='__main__':main()
