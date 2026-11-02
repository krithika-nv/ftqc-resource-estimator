#!/usr/bin/env python3
"""Create a small reproducibility handoff; never include raw source shots or secrets."""
import argparse,csv,io,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES=[
'outputs/matched_hardware_evidence/ibm_fez/EVIDENCE_MANIFEST.json',
'outputs/matched_hardware_evidence/ibm_fez/EVIDENCE_REPORT.md',
'outputs/matched_hardware_evidence/ibm_fez/MATCHED_EVIDENCE_INVENTORY.csv',
'outputs/external_validation/IBM_SOURCE_SCHEMA.json',
'outputs/external_validation/ibm_raw_decode_summary.json',
'outputs/external_validation/ibm_decoded_shots.json',
]

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'outputs'/'IBM_REVIEW_BUNDLE.zip')
 a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 runs=ROOT/'logs'/'runs'
 candidates=sorted((x for x in runs.glob('*/run_manifest.json') if x.is_file()),key=lambda x:x.stat().st_mtime,reverse=True)
 picked=next((x.parent for x in candidates if json.loads(x.read_text()).get('profile') in ('ibm','evidence','all')),None)
 with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for fn in FILES:
   f=ROOT/fn
   if f.is_file():z.write(f,arcname=fn)
  if picked:
   for f in sorted(picked.iterdir()):
    if f.is_file() and f.suffix in ('.log','.json','.md'):
     z.write(f,arcname='logs/'+f.name)
  shots=ROOT/'data'/'verified'/'ibm_decoded_shots.csv'
  if shots.is_file():
   with shots.open(newline='',encoding='utf8') as handle:
    reader=csv.reader(handle); buf=io.StringIO();writer=csv.writer(buf)
    for i,row in enumerate(reader):
     if i>25:break
     # share only derived shot outputs, not raw syndrome histories
     writer.writerow(row)
   z.writestr('preview/ibm_decoded_shots_FIRST25.csv',buf.getvalue())
  z.writestr('READ_ME_FIRST.txt','Review bundle: limited log reports, public source hashes, and at most 25 decoded shot rows. Raw experimental files, credentials and the full decoded CSV are not included. If schema parsing fails, provide the original 9 MB public Fez archive separately for real format debugging.\n')
 print(f'Review bundle: {a.output} ({a.output.stat().st_size} bytes)')
if __name__=='__main__':main()
