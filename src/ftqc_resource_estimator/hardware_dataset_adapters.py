"""Scope-safe source-specific dataset inventory for four quantum hardware families.

This is ingestion of experimental files and metadata, NOT calibration fitting or a
hardware prediction. External data are never bundled and unsafe pickles are NEVER
loaded. A source ID is required; accidental cross-platform use fails closed.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import zipfile

from .evidence_catalog import validate_catalog

KNOWN_FORMATS={'.json','.csv','.tsv','.npy','.npz','.xlsx','.txt','.p','.pkl','.pickle','.zip','.gz','.qasm','.pdf'}
PICKLES={'.p','.pkl','.pickle'}
MAX_HASH_BYTES=32*1024*1024
MAX_METADATA_JSON=4*1024*1024


def catalog(root:Path|None=None)->dict:
    root=root or Path('data/hardware_evidence_sources.json')
    raw=json.loads(root.read_text())
    return {s['id']:s for s in validate_catalog(raw)}


def classify(source_id:str, rel:str)->str:
    s=rel.lower();name=Path(s).name
    if source_id=='xanadu_aurora':
        if name=='xanadu_aurora_plot_data.xlsx':return 'published_figure_table'
        if s.endswith('.npy') and ('quadratures' in name or 'vacuum' in name):return 'measured_optical_quadratures'
        if 'switch_settings' in name:return 'adaptive_optical_switch_settings'
        if 'decisions' in name:return 'optical_decoder_decisions'
        return 'photonic_source_supplement'
    if source_id=='xanadu_gkp':
        if name=='analysis_results.npy':return 'reconstructed_gkp_state_analysis'
        if name.endswith('.tar.gz'):return 'raw_gkp_archive_not_extracted'
        return 'gkp_source_supplement'
    if source_id=='quantinuum_helios':
        if name.endswith('.p'):return 'published_helios_serialized_data_UNSAFE_TO_DESERIALIZE'
        return 'helios_supplement'
    if source_id=='quantinuum_specifications':return 'published_device_specification_not_calibration' 
    if source_id=='quera_aquila_2026':
        if name.startswith('task_') and name.endswith('.json'):return 'neutral_atom_experiment_task'
        if name.endswith('.zip'):return 'oxford_neutral_atom_data_archive_not_extracted'
        if name.endswith('.npy'):return 'neutral_atom_experiment_or_simulated_array'
        return 'neutral_atom_source_supplement'
    if source_id.startswith('ibm_'):
        if name=='calibration.json':return 'per_execution_calibration_snapshot'
        if name=='info.json':return 'execution_protocol_metadata'
        if name=='bitstrings.json':return 'real_hardware_outcome_bitstrings'
        if name.endswith('.qasm'):return 'executed_quantum_circuit'
        return 'superconducting_backend_calibration_or_archive'
    raise ValueError('unrecognized source ID')


def _sha256(path:Path, *, big:bool=False)->str|None:
    if path.stat().st_size>MAX_HASH_BYTES and not big:return None
    h=sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def _inspect_file(path:Path, kind:str, *, require_numpy:bool=False)->dict:
    result={'kind':kind,'format':''.join(path.suffixes[-2:]) if path.name.endswith('.tar.gz') else path.suffix.lower(), 'extraction':'not_attempted'}
    suffix=path.suffix.lower()
    if suffix in PICKLES:
        result['inspection']='opaque_unsafe_pickle_do_not_load'
    elif suffix in ('.npy','.npz'):
        try:
            import numpy as np
        except ImportError:
            if require_numpy:raise
            result['inspection']='requires_numpy_for_array_header';return result
        try:
            arr=np.load(path,mmap_mode='r',allow_pickle=False)
            if suffix=='.npz':
                result['inspection']='npz_member_names_only';result['arrays']=list(arr.files)[:100];arr.close()
            else:
                result.update(inspection='npy_header',shape=list(arr.shape),dtype=str(arr.dtype))
                if arr.dtype.hasobject:raise ValueError('unsafe object arrays not supported')
        except ValueError as e:
            result['inspection']='unsupported_numpy_array_safely_rejected';result['reason']=str(e)[:180]
    elif suffix=='.zip':
        try:
            with zipfile.ZipFile(path) as f:
                names=f.namelist()
                if any(n.startswith('/') or '..' in Path(n).parts for n in names):
                    raise ValueError('unsafe zip member path')
                result.update(inspection='archive_directory_only_no_extraction',member_count=len(names),member_examples=names[:12])
        except zipfile.BadZipFile:raise ValueError('invalid zip archive: '+str(path))
    elif suffix=='.json' and path.stat().st_size<=MAX_METADATA_JSON:
        obj=json.loads(path.read_text())
        if isinstance(obj,dict):result.update(inspection='json_keys_only',keys=list(obj)[:35])
        elif isinstance(obj,list):result.update(inspection='json_array_length_only',count=len(obj))
        else:result['inspection']='json_scalar_metadata_only'
    elif suffix in ('.csv','.tsv') and path.stat().st_size<=MAX_METADATA_JSON:
        with path.open(newline='') as f:
            result.update(inspection='csv_header_only',columns=next(csv.reader(f,delimiter='\t' if suffix=='.tsv' else ','),[]))
    elif suffix=='.xlsx':result['inspection']='workbook_registered_not_parsed'
    else:result['inspection']='metadata_only'
    return result


def inspect(source_id:str, input_path:Path, *, catalog_path:Path|None=None, max_files:int=300, hash_large:bool=False)->dict:
    sources=catalog(catalog_path)
    if source_id not in sources:raise ValueError(f'Unknown source ID: {source_id}')
    if not input_path.exists():raise FileNotFoundError(input_path)
    if not input_path.is_file() and not input_path.is_dir():raise ValueError('regular file or directory required')
    if max_files<1:raise ValueError('max_files must be positive')
    files=sorted((p for p in input_path.rglob('*') if p.is_file()),key=str) if input_path.is_dir() else [input_path]
    files=[p for p in files if p.suffix.lower() in KNOWN_FORMATS]
    if not files:raise ValueError('no supported dataset files found')
    selected=files[:max_files]
    rows=[]
    for p in selected:
        rel=str(p.relative_to(input_path)) if input_path.is_dir() else p.name
        kind=classify(source_id,rel)
        row={'relative_path':rel,'bytes':p.stat().st_size,'sha256':_sha256(p,big=hash_large)}
        row.update(_inspect_file(p,kind))
        rows.append(row)
    source=sources[source_id]
    return {
      'source_id':source_id,'source_url':source['url'],'hardware_family':source['hardware_family'],
      'source_data_type':source['data_type'],'input_kind':'directory' if input_path.is_dir() else 'file',
      'inspected_utc':datetime.now(timezone.utc).isoformat(),
      'supported_files_found':len(files),'files_indexed':len(rows),'files_not_indexed':len(files)-len(rows),
      'total_bytes_indexed':sum(x['bytes'] for x in rows),
      'status':'REAL_SOURCE_FILES_INDEXED_NOT_HARDWARE_CALIBRATED',
      'read_only':True,'scientific_limits':[
        'Source-file indexing does not constitute a device-matched calibration or predicted logical-error validation.',
        'No cross-platform numerical ranking or physical parameter conversion is inferred.',
        'Calibration and execution timestamps must be checked separately from release dates.',
        'Large file hashes omitted unless --hash-large; a missing hash is not verified integrity.',
        'Serialized pickle .p files are treated as opaque; never unpickle untrusted experimental files.'
      ],'files':rows
    }


def write_report(manifest:dict,out:Path)->None:
    out.mkdir(parents=True,exist_ok=True)
    (out/'DATASET_EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with (out/'DATASET_FILES.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['relative_path','kind','format','bytes','sha256','inspection'])
        w.writeheader()
        for row in manifest['files']:w.writerow({k:row.get(k) for k in w.fieldnames})
    (out/'DATASET_REPORT.md').write_text(
      f"# {manifest['source_id']} - source-scoped file ingestion\n\n"
      f"- Family: **{manifest['hardware_family']}**\n- Original source: {manifest['source_url']}\n"
      f"- Files indexed: **{manifest['files_indexed']}** of {manifest['supported_files_found']} supported files.\n"
      f"- Total indexed bytes: {manifest['total_bytes_indexed']}.\n"
      f"- Status: **{manifest['status']}**\n"
      '- This is **file-level evidence ingestion only**, not calibrated hardware prediction.\n'
      '- Opaque `.p` files are indexed, never deserialized; large files are not extracted.\n'
      '- Hashes are null for files above 32 MiB unless explicitly requested with `--hash-large`.\n'
      '- Inspect `DATASET_EVIDENCE_MANIFEST.json` for the type and handling of each source file.\n'
    )


def main():
    ap=argparse.ArgumentParser(description='Index external hardware datasets safely, with platform provenance; no cross-family calibration')
    ap.add_argument('--source',required=True,help='exact ID in data/hardware_evidence_sources.json')
    ap.add_argument('--input',type=Path,required=True,help='downloaded source repository, file, or archive')
    ap.add_argument('--output-dir',type=Path,required=True)
    ap.add_argument('--catalog',type=Path,default=Path('data/hardware_evidence_sources.json'))
    ap.add_argument('--max-files',type=int,default=300)
    ap.add_argument('--hash-large',action='store_true',help='opt in to hashing large inputs, potentially many GiB')
    args=ap.parse_args()
    result=inspect(args.source,args.input,catalog_path=args.catalog,max_files=args.max_files,hash_large=args.hash_large)
    write_report(result,args.output_dir)
    print(f"Indexed {result['files_indexed']} {result['hardware_family']} source files for {args.source}; no hardware predictions claimed")
if __name__=='__main__':main()
