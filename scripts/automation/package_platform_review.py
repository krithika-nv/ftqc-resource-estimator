#!/usr/bin/env python3
"""Small four-platform analysis handoff without sharing raw vendor datasets."""
from __future__ import annotations
import argparse
import csv
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUTPUTS=[
    'outputs/matched_hardware_evidence/ibm_fez/EVIDENCE_MANIFEST.json',
    'outputs/matched_hardware_evidence/ibm_fez/EVIDENCE_REPORT.md',
    'outputs/external_validation/IBM_SOURCE_SCHEMA.json',
    'outputs/external_validation/FOUR_PLATFORM_FTQC_ACCEPTANCE.json',
    'outputs/external_validation/COMPONENT_PROGRESS.json',
    'outputs/external_validation/COMPONENT_PROGRESS.md',
    'outputs/external_validation/HARDWARE_EVIDENCE_GATES.json',
    'outputs/external_validation/ibm_raw_decode_summary.json',
    'outputs/external_validation/ibm_decoded_shots.json',
    'outputs/external_validation/ibm_majority_summary.json',
    'outputs/external_validation/IBM_READOUT_ONLY_CALIBRATION.json',
    'outputs/external_validation/quantinuum_public_counts.json',
    'outputs/external_validation/helios_pickle_audit.json',
    'outputs/external_validation/helios_raw_counts.json',
    'outputs/external_validation/neutral_source_schemas.json',
    'outputs/external_validation/MEASURED_PRIMITIVE_LEDGER.json',
    'outputs/external_validation/GATE_EVIDENCE_CANDIDATES.json',
    'outputs/external_validation/IBM_CALIBRATION_EPOCHS.json',
    'outputs/external_validation/aurora_workbook_schema.json',
    'outputs/external_validation/aurora_raw_quadratures.json',
    'outputs/external_validation/aurora_reproduction/REPORT.json',
    'outputs/external_validation/aurora_reproduction/Fig_3c_matrix_data.csv',
    'outputs/external_validation/aurora_reproduction/Fig_3d_matrix_data.csv',
    'outputs/external_validation/aurora_reproduction/Fig_3c_replot.png',
    'outputs/external_validation/aurora_reproduction/Fig_3d_replot.png',
    'outputs/external_validation/neutral_source_archive.json',
    'outputs/external_validation/gkp_source_inventory.json',
    'outputs/external_validation/helios_source_inventory.json',
    'outputs/external_validation/ion_specs_source_inventory.json',
    'outputs/external_validation/helios_counts.json',
    'outputs/external_validation/helios_mcmr_author_notebook.json',
    'outputs/external_validation/CONDITIONAL_FOUR_PLATFORM_WORKLOAD.json',
    'outputs/external_validation/neutral_source_inventory.json',
    'outputs/external_validation/neutral_atom_decoded_shots.json',
    'evidence/upstream_revisions.json',
    'evidence/neutral_atom_zenodo_metadata.json',
]
VERIFIED=['ibm_majority_shots.csv','ibm_decoded_shots.csv','helios_counts.csv','neutral_atom_decoded_shots.csv']

def generate(output:Path,run_dir:Path|None=None)->dict:
    output.parent.mkdir(parents=True,exist_ok=True)
    if run_dir is None:
        candidates=sorted((ROOT/'logs/runs').glob('*/run_manifest.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        run_dir=next((f.parent for f in candidates if json.loads(f.read_text()).get('profile') in ('all','evidence')),None)
    added=[];missing=[]
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
        if run_dir:
            for f in sorted(run_dir.iterdir()):
                if f.is_file() and f.suffix in ('.json','.md','.log') and f.stat().st_size<=2_000_000:
                    arc='logs/'+run_dir.name+'/'+f.name
                    z.write(f,arcname=arc);added.append(arc)
        for rel in OUTPUTS:
            f=ROOT/rel
            if f.is_file() and f.stat().st_size <= 5_000_000:
                z.write(f,rel);added.append(rel)
            else:missing.append(rel)
        # Human-readable candidate dossiers have one canonical location in Git.
        for fam in ('superconducting','photonic','trapped_ion','neutral_atom'):
            rel=f'evidence/gate_review_candidates/{fam}.md'
            path=ROOT/rel
            if path.is_file():
                z.write(path,rel);added.append(rel)
        rel='evidence/gate_review_candidates/INDEX.json'
        path=ROOT/rel
        if path.is_file():
            z.write(path,rel);added.append(rel)
        for name in VERIFIED:
            path=ROOT/'data/verified'/name
            if path.is_file():
                with path.open(newline='',encoding='utf8') as fh:
                    reader=csv.reader(fh)
                    out=io.StringIO();w=csv.writer(out)
                    for idx,row in enumerate(reader):
                        if idx>=26:break
                        w.writerow(row)
                    preview='previews/'+name
                    z.writestr(preview,out.getvalue());added.append(preview)
        status={'schema':'ftqc.platform-review.v1','run_dir':str(run_dir) if run_dir else None,'included':added,'unavailable_or_oversize':missing,
                'caveat':'No original raw hardware shots, big optical datasets, credentials or full normalized CSVs. Missing results are not inferred to be scientifically complete.'}
        z.writestr('REVIEW_INDEX.json',json.dumps(status,indent=2)+'\n')
    return status

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=ROOT/'outputs/FOUR_PLATFORM_REVIEW_BUNDLE.zip')
    p.add_argument('--run-dir',type=Path,default=None)
    args=p.parse_args()
    result=generate(args.output,args.run_dir)
    print('Review bundle:',args.output,'bytes:',args.output.stat().st_size)
    print('Included:',len(result['included']),'Missing or oversized:',len(result['unavailable_or_oversize']))
    if result['run_dir'] is None:print('WARNING: no all/evidence run manifest was found, run the pipeline first.')
if __name__=='__main__':main()
