"""Conditional neutral-atom geometry/parallel blockade scheduling.

A deterministic geometry-aware resource model, NOT calibrated FTQC or a
logical-QEC model. Pairwise exclusion is an explicitly chosen toy constraint;
real Rydberg blockade, crosstalk, transport, leakage, and optical tweezer
constraints require platform-specific measurements.
"""
import argparse,json,math
from pathlib import Path
from .evidence_analysis import save_report


def schedule(spec:dict)->dict:
    coords=spec['atoms_um']; gates=spec['two_atom_operations'];radius=float(spec['exclusion_radius_um'])
    gate_us=float(spec['two_atom_gate_duration_us'])
    if radius<=0 or gate_us<=0 or not (math.isfinite(radius) and math.isfinite(gate_us)):raise ValueError('positive finite timing and radius required')
    if not isinstance(coords,dict) or len(coords)<2:raise ValueError('missing atom coordinates')
    for k,p in coords.items():
        if len(p)!=2 or not all(math.isfinite(float(a)) for a in p):raise ValueError('invalid coordinates')
    if not gates:raise ValueError('need two-atom operations')
    used=set();layers=[]
    def distance(a,b):return math.dist(tuple(map(float,coords[a])),tuple(map(float,coords[b])))
    for gate in gates:
        if len(gate)!=2 or gate[0]==gate[1] or any(a not in coords for a in gate):raise ValueError('invalid gate pair')
        # preserve input dependence for overlapping gates; no commuting assumption.
        previous_layer=max((i for i,layer in enumerate(layers) for other in layer if set(gate)&set(other)),default=-1)
        placed=False
        for i in range(previous_layer+1,len(layers)):
            conflict=any(any(distance(a,b)<radius for a in gate for b in other) for other in layers[i])
            if not conflict: layers[i].append(gate);placed=True;break
        if not placed:layers.append([gate])
    return {'scope':'HYPOTHETICAL_NEUTRAL_ATOM_BLOCKADE_SCHEDULER_NOT_CALIBRATED_FTQC',
      'atoms':len(coords),'operations':len(gates),'scheduled_layers':layers,
      'layer_count':len(layers),'assumed_two_atom_gate_duration_us':gate_us,
      'modeled_entangling_time_us':gate_us*len(layers),'serial_time_us':gate_us*len(gates),
      'speedup_over_serial':len(gates)/len(layers),
      'caveats':['Exclusion radius and operation times are hypothetical unless supported by a device-specific calibration.',
        'No fidelity, Rydberg level, shuttling or leakage model; no quantum error-correction code modeled.']}


def main():
    p=argparse.ArgumentParser();p.add_argument('--geometry-json',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    r=schedule(json.loads(a.geometry_json.read_text()))
    save_report(a.output_dir,'NEUTRAL_ATOM_SCHEDULING',r,'A deterministic scheduling model from explicitly supplied assumptions; not a calibrated neutral-atom FTQC prediction.')
    print('Neutral atom layers:',r['layer_count'])
if __name__=='__main__':main()
