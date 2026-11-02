"""Validate scoped public hardware-source registry; no data values fabricated."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

FAMILIES={'superconducting','photonic','trapped_ion','neutral_atom'}

def validate_catalog(data:dict)->list[dict]:
    if not isinstance(data,dict) or not isinstance(data.get('sources'),list):
        raise ValueError('sources must be list')
    sources=data['sources']
    if not sources: raise ValueError('empty catalog')
    ids=set()
    for s in sources:
        if not isinstance(s,dict): raise ValueError('invalid source')
        if not isinstance(s.get('id'),str) or not s['id'] or s['id'] in ids:raise ValueError('duplicate or invalid source ID')
        ids.add(s['id'])
        if s.get('hardware_family') not in FAMILIES:raise ValueError('unknown hardware family')
        if not isinstance(s.get('url'),str) or not s['url'].startswith('https://'):
            raise ValueError('missing primary source URL')
        if s.get('calibrates_surface_code') is not False:
            raise ValueError('source catalog must not imply unsupported full surface-code calibration')
        if not isinstance(s.get('critical_gaps'),list) or not s['critical_gaps']:
            raise ValueError('must document critical gaps')
        if not s.get('status') or not s.get('data_type'):raise ValueError('missing evidence status')
    return sources


def report(path:Path)->str:
    sources=validate_catalog(json.loads(path.read_text()))
    lines=['# Hardware evidence-source registry','',
      '**Scope:** public primary analysis sources and evidence limits. Listing a source does not mean its data have been downloaded, imported or calibrated to the estimator.','',
      '| Platform | Provider / dataset | What is actually available | Pipeline status |',
      '|---|---|---|---|']
    for s in sources:
        lines.append(f"| {s['hardware_family']} | [{s['provider']} / {s['id']}]({s['url']}) | {s['data_type']} | {s['status']} |")
    lines+=['','## Scientific boundary','','- IBM processor properties characterize **superconducting** qubits. They cannot parameterize photonic loss, GKP state defects or trapped-ion transport.',
    '- Xanadu Aurora and GKP data address specific **photonic experiments**; they are not automatically logical FTQC benchmarks.',
    '- Quantinuum Helios data and specifications concern **trapped-ion** devices; typical spec values are not shot-matched per-qubit calibrations.',
    '- QuEra Aquila experiments concern **neutral atoms** and randomized measurements, not a directly measured neutral-atom QEC failure curve.',
    '- No cross-platform numeric rankings should be produced without equivalent workloads and separately validated physical mappings.',
    '- The archived 2026 IBM repetition-code data can support a **repetition-code** validation, not a surface-code hardware claim.',
    '']
    return '\n'.join(lines)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--catalog',type=Path,default=Path('data/hardware_evidence_sources.json'))
    ap.add_argument('--output',type=Path,default=Path('docs/hardware/HARDWARE_DATA_GUIDE.md'))
    args=ap.parse_args();content=report(args.catalog);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(content+'\n');print('Wrote',args.output)
