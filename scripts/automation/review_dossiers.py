#!/usr/bin/env python3
"""Prepare inspectable gate dossiers, never approve or register science automatically."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
try:
    from .audit_ftqc_end_to_end import REQUIRED
except ImportError:
    from audit_ftqc_end_to_end import REQUIRED

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE={
 'superconducting':{
   'device_calibration':['evidence/verified/IBM_FEZ_READOUT_ONLY_SMOKE.json','outputs/matched_hardware_evidence/ibm_fez/EVIDENCE_MANIFEST.json','outputs/external_validation/IBM_CALIBRATION_EPOCHS.json'],
   'syndrome_decoder':['outputs/external_validation/ibm_raw_decode_summary.json','outputs/external_validation/ibm_decoded_shots.json'],
   'independent_holdout':['outputs/external_validation/ibm_decoded_shots.json'],
   'circuit_level_noise':['evidence/verified/IBM_FEZ_READOUT_ONLY_SMOKE.json','outputs/external_validation/IBM_READOUT_ONLY_CALIBRATION.json'],
 },
 'photonic':{
   'loss_squeezing_gkp_characterization':['evidence/verified/AURORA_WORKBOOK_REPRODUCTION.json','outputs/external_validation/aurora_reproduction/REPORT.json'],
   'physical_resource_accounting':['outputs/external_validation/CONDITIONAL_FOUR_PLATFORM_WORKLOAD.json'],
 },
 'trapped_ion':{
   'gate_spam_leakage_calibration':['evidence/verified/HELIOS_MCMR_ORIGINAL_COUNTS_REPRODUCTION.json','evidence/verified/QUANTINUUM_H_SERIES_PUBLIC_COUNTS.json','outputs/external_validation/helios_raw_counts.json','outputs/external_validation/quantinuum_public_counts.json','outputs/external_validation/helios_mcmr_author_notebook.json'],
   'transport_and_crosstalk':['evidence/verified/HELIOS_MCMR_ORIGINAL_COUNTS_REPRODUCTION.json','outputs/external_validation/helios_mcmr_author_notebook.json']
 },
 'neutral_atom':{
   'erasure_aware_decoder':['outputs/external_validation/neutral_source_archive.json'],
   'gate_loss_rearrangement_calibration':['evidence/neutral_atom_zenodo_metadata.json']
 }
}
def build(root=ROOT, *, source_only=False):
    out={'schema':'ftqc.gate-review-candidates.v1','automatically_accepted':0,'families':{},
       'warning':'Evidence attachment is not independent scientific validation; none of these files automatically passes the strict 34 gates.'}
    for fam,gates in REQUIRED.items():
        cases={}
        for gate in gates:
            attachments=[]
            for rel in EVIDENCE.get(fam,{}).get(gate,[]):
                if source_only and not rel.startswith('evidence/verified/'):
                    continue
                p=root/rel
                if p.is_file():
                    attachments.append({'artifact':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
            cases[gate]={
                'status':'candidate_requires_scientific_review' if attachments else 'no_candidate_artifact',
                'candidate_artifacts':attachments,
                'review_requirements':['Verify original experimental source and method against paper',
                  'Confirm observable and platform match this gate, not a weaker proxy',
                  'Confirm source/holdout independence and confidence analysis',
                  'Confirm hardware-native logical operation or architecture scope',
                  'Obtain independent reviewer decision'],
                'accepted':False}
        out['families'][fam]=cases
    return out

def main():
    p=argparse.ArgumentParser(description='Generate a run-specific, non-accepting candidate evidence snapshot.')
    p.add_argument('--output',type=Path,default=ROOT/'outputs/external_validation/GATE_EVIDENCE_CANDIDATES.json')
    p.add_argument('--source-only',action='store_true',help='Only include checked-in evidence receipts')
    a=p.parse_args()
    result=build(source_only=a.source_only)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Generated 34 review-only candidate records:',a.output)
    print('Canonical written dossiers remain under evidence/gate_review_candidates/.')
if __name__=='__main__':main()
