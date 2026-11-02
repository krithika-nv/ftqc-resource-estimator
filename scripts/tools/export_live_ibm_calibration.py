"""User-invoked IBM Quantum authenticated export. No credential storage here.

The user configures QiskitRuntimeService through their local IBM account.
We serialize *only backend properties* and do not output credentials.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--backend',required=True)
    ap.add_argument('--output',type=Path,default=Path('data/public_calibrations/live_properties.json'))
    args=ap.parse_args()
    if not args.backend.startswith('ibm_'):ap.error('expected an IBM quantum device ID')
    try:from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as e:raise SystemExit('Optional qiskit-ibm-runtime package required for authenticated IBM export') from e
    service=QiskitRuntimeService() # uses account configured on the user's own machine
    backend=service.backend(args.backend)
    properties=backend.properties(refresh=True)
    if properties is None:raise SystemExit('No backend properties available; nothing written')
    data=properties.to_dict()
    if data.get('backend_name')!=args.backend:raise SystemExit('IBM API device mismatch')
    if not data.get('last_update_date'):raise SystemExit('Calibration has no timestamp')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,default=lambda x:x.isoformat() if hasattr(x,'isoformat') else str(x),indent=2)+'\n')
    print('Exported hardware properties (not credentials):',args.output)
    print('Device:',data['backend_name'],'Calibration timestamp:',data['last_update_date'])
    print('Retrieved at UTC:',datetime.now(timezone.utc).isoformat())
