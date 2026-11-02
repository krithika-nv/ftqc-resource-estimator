"""Figure generated ONLY from measured, source-linked IBM 2024 calibration fields."""
from pathlib import Path
import json
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'outputs/public_calibration/normalized_calibration.json'
if not source.exists():
    raise SystemExit('Run ./scripts/commands/RUN_PUBLIC_CALIBRATION.sh first')
data=json.loads(source.read_text())
if data['backend_name'] != 'ibmq_manila' or data['last_update_date'] != '2024-05-27T15:27:23-03:00':
    raise SystemExit('Unrecognized historical source - refusing to label figure as IBM Manila')
q=data['qubits']
ids=[x['qubit'] for x in q]
values=[100*x['readout_error'] for x in q]
fig,ax=plt.subplots(figsize=(7.2,4.0))
ax.bar(ids,values)
ax.set_xticks(ids)
ax.set_xlabel('Physical qubit index (archived ibmq_manila)')
ax.set_ylabel('Reported readout assignment error (%)')
ax.set_title('Historical device heterogeneity - measured, May 2024')
ax.set_ylim(0,max(values)*1.2)
for x,y in zip(ids,values):
    ax.text(x,y+0.13,f'{y:.2f}%',ha='center',fontsize=9)
fig.text(0.5,0.01,'Source: Qiskit/IBM published props_manila.json; snapshot 2024-05-27. Not a current QPU benchmark.',ha='center',fontsize=8)
fig.tight_layout(rect=(0,0.04,1,1))
dest=ROOT/'outputs/public_calibration/readout_error_by_qubit.png'
fig.savefig(dest,dpi=160)
print(dest)
