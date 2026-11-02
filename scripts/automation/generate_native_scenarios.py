"""Generate platform-distinct conditional *engineering assumptions*, not fitted hardware models.

No physical-to-logical calibration relation exists for the four platforms, so this
must never be labeled measured calibrated FTQC predictions.
"""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
# Transparent scenario multipliers, explicitly hypothetical, not vendor metrics.
SCALES={
 'superconducting':{'duration':1.0,'failure':1.0,'resource':1.0,'factory':1.0,'communication':1.0,'controller':1.0,'unit':'superconducting_physical_sites_scenario'},
 'photonic':{'duration':0.35,'failure':1.8,'resource':3.5,'factory':1.7,'communication':0.7,'controller':1.3,'unit':'photonic_capacity_equivalent_scenario'},
 'trapped_ion':{'duration':9.0,'failure':0.6,'resource':0.75,'factory':4.0,'communication':2.1,'controller':2.7,'unit':'ion_capacity_equivalent_scenario'},
 'neutral_atom':{'duration':2.8,'failure':1.4,'resource':1.65,'factory':2.5,'communication':3.5,'controller':2.0,'unit':'neutral_atom_capacity_equivalent_scenario'},
}
def generate(original):
    p=json.loads(json.dumps(original));p['description']='Four DISTINCT sensitivity scenarios; ALL assumptions are hypothetical and NOT independently calibrated or valid for cross-technology rankings.'
    for fam,scale in SCALES.items():
        o=p['families'][fam]
        for k in o['operation_durations_us']:o['operation_durations_us'][k]*=scale['duration']
        for k in o['operation_failure_probabilities']:o['operation_failure_probabilities'][k]*=scale['failure']
        for k in o['illustrative_failure_probability_ranges']:
            o['illustrative_failure_probability_ranges'][k]=[v*scale['failure'] for v in o['illustrative_failure_probability_ranges'][k]]
        o['non_clifford_supply']['attempt_duration_us']*=scale['factory']
        o['communication_critical_path_us']*=scale['communication']
        o['controller_critical_path_us']*=scale['controller']
        o['physical_resource_assumptions']['native_unit']=scale['unit']
        for k in ('logical_data_units','factory_units_per_lane','control_units','communication_units'):
            o['physical_resource_assumptions'][k]*=scale['resource']
        o['assumption_note']='UNVALIDATED native engineering scenario multipliers: '+json.dumps(scale,sort_keys=True)
    return p
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'examples/ILLUSTRATIVE_ONLY_four_family_profiles.json')
    p.add_argument('--output',type=Path,default=ROOT/'examples/SCENARIO_ONLY_native_four_family_profiles.json');a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(generate(json.loads(a.source.read_text())),indent=2)+'\n')
