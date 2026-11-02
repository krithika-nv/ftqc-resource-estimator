#!/usr/bin/env python3
"""Fail-closed four-family science gates; never promote inventories to validation."""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REQUIRED={
 'superconducting': ('device_calibration','circuit_level_noise','syndrome_decoder','logical_memory','logical_clifford_gates','nonclifford_factory','routing_scheduler','physical_resource_accounting','independent_holdout'),
 'photonic': ('loss_squeezing_gkp_characterization','gkp_noise_and_decoder','logical_memory','logical_clifford_gates','nonclifford_factory','optical_routing_and_multiplexing','physical_resource_accounting','independent_holdout'),
 'trapped_ion': ('gate_spam_leakage_calibration','transport_and_crosstalk','native_logical_code_decoder','logical_memory','logical_clifford_gates','nonclifford_factory','routing_scheduler','physical_resource_accounting','independent_holdout'),
 'neutral_atom': ('gate_loss_rearrangement_calibration','erasure_aware_decoder','logical_memory','logical_clifford_gates','nonclifford_factory','replenishment_and_parallel_zones','physical_resource_accounting','independent_holdout'),
}

SOURCES={
 'superconducting':('IBM repetition-code shots','https://doi.org/10.5281/zenodo.20768087','Measured repetition code is not full surface-code/gate calibration'),
 'photonic':('Xanadu Aurora/GKP public datasets','https://github.com/XanaduAI/xanadu-aurora-data','Figure and decoder demonstrations do not calibrate T-state factories'),
 'trapped_ion':('Quantinuum Helios experimental outputs','https://github.com/Quantinuum/Helios-paper-data','Physical benchmarks do not by themselves reproduce protected logical gates'),
 'neutral_atom':('Bluvstein–Geim surface-code shots','https://doi.org/10.5281/zenodo.15685795','Loss-aware surface-code memory is not a universal FTQC stack'),
}


def audit(claims:dict)->dict:
    if claims.get('schema')!='ftqc.four-family-evidence.v1':
        raise ValueError('invalid four-family evidence manifest schema')
    result={}
    for family,gates in REQUIRED.items():
        supplied=claims.get('families',{}).get(family,{})
        entries=supplied.get('gates',{})
        checks={}
        for name in gates:
            item=entries.get(name)
            if not isinstance(item,dict):
                checks[name]={'status':'missing'};continue
            # Never accept an assertion of success without traceable artifacts.
            if item.get('status')!='verified' or not isinstance(item.get('evidence'),list) or not item['evidence']:
                checks[name]={'status':'unverified'};continue
            valid=True;why=[]
            for src in item['evidence']:
                if not isinstance(src,dict) or not src.get('artifact') or not src.get('sha256'):
                    valid=False; why.append('evidence artifact and SHA-256 required');continue
                f=ROOT/src['artifact']
                if not f.is_file() or not f.resolve().is_relative_to(ROOT.resolve()):
                    valid=False;why.append('missing or unsafe local evidence path');continue
                digest=hashlib.sha256()
                with f.open('rb') as inp:
                    for chunk in iter(lambda:inp.read(1024*1024),b''):
                        digest.update(chunk)
                h=digest.hexdigest()
                if h!=src['sha256']:
                    valid=False;why.append('evidence checksum mismatch')
            checks[name]={'status':'evidence_file_hash_matched' if valid else 'invalid_evidence',
                         'issues':why}
        result[family]={'gates':checks,'gates_with_matching_files':sum(1 for x in checks.values() if x['status']=='evidence_file_hash_matched'),
                        'required_gate_count':len(gates), 'evidence_files_present':all(x['status']=='evidence_file_hash_matched' for x in checks.values()),
                        'independent_scientific_verification':'requires reviewer inspection of raw source-to-observable methodology',
                        'source_context':{'name':SOURCES[family][0],'url':SOURCES[family][1],'limitation':SOURCES[family][2]}}
    registered=sum(1 for f in result.values() for g in f['gates'].values() if g['status']!='missing')
    hashed=sum(f['gates_with_matching_files'] for f in result.values())
    return {'schema':'ftqc.four-family-acceptance-audit.v1','families':result,
            'total_required_gates':sum(len(x) for x in REQUIRED.values()),
            'submitted_gate_dossiers':registered,
            'gate_dossiers_with_matching_hashes':hashed,
            'zero_dossiers_explanation':'An empty evidence manifest means no full-stack gate dossiers have been submitted; it does not mean 34 experiments failed or that existing components are absent.',
            'all_evidence_file_contracts_met':all(x['evidence_files_present'] for x in result.values()),
            'independently_validated_end_to_end_ftqc':False,
            'why_not_certified':'Manifest status and matching hashes cannot establish experimental protocol agreement, trained/held-out independence, or model physical validity. Independent reproduction and review remain required.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=ROOT/'evidence/validation/four_family_evidence.json')
    p.add_argument('--output',type=Path,default=ROOT/'outputs/external_validation/FOUR_FAMILY_ACCEPTANCE_AUDIT.json')
    args=p.parse_args(argv)
    r=audit(json.loads(args.manifest.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({f:{'evidence':v['gates_with_matching_files'],'required':v['required_gate_count']} for f,v in r['families'].items()},indent=2))
    return 0 if r['all_evidence_file_contracts_met'] else 2

if __name__=='__main__':
    raise SystemExit(main())
