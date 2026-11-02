#!/usr/bin/env python3
"""Evidence-level summary; never promote source inventories to paper reproduction."""
from __future__ import annotations
import argparse,json
from pathlib import Path

FAMILIES=('superconducting','photonic','trapped_ion','neutral_atom')
FAMILY_GATES={
 'superconducting':{'source':'ibm_evidence','decoded':'ibm_decoded','figure_reproduction':None},
 'photonic':{'source':'aurora_workbook','decoded':None,'figure_reproduction':'aurora_reproduction'},
 'trapped_ion':{'source':'helios_inventory','decoded':'helios_counts','figure_reproduction':None},
 'neutral_atom':{'source':'neutral_archive_inventory','decoded':'neutral_decoded','figure_reproduction':None},
}

def report(run:dict):
    states={s['step']:s['status'] for s in run.get('steps',[])}
    families={}
    for family,gates in FAMILY_GATES.items():
        checks={key:('not_applicable' if step is None else states.get(step,'not_run')) for key,step in gates.items()}
        families[family]={'checks':checks,
            'paper_protocol_reproduced':False,
            'hardware_prediction_validated':False,
            'note':'Successful source inventory, numerical replot, or decoded-shot analysis is not a verified matched-paper reproduction.'}
    return {'schema':'ftqc.hardware-evidence-gates.v1','source_run_id':run.get('run_id'),
            'software_orchestration_passed':run.get('execution_passed',False),
            'all_required_source_inputs_present':run.get('all_external_inputs_available',False),
            'four_platform_paper_reproduction_completed':False,
            'families':families}

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    content=report(json.loads(a.manifest.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(content,indent=2,sort_keys=True)+'\n')
    print('Evidence gates:',a.output)
if __name__=='__main__':main()
