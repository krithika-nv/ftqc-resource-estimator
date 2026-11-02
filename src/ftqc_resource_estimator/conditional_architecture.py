"""Illustrative, platform-native FTQC workload cost envelopes.

This is an architecture *assumption ledger* with explicit inputs, NOT an
independently calibrated or device validated prediction. It never translates
photons/modes, ions, atoms and superconducting qubits into equal resource units.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from .full_stack_prediction import FAMILIES,OPERATIONS


def number(v,name,strict=False):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or (strict and v==0):
        raise ValueError(f'{name} must be finite and {"positive" if strict else "nonnegative"}')
    return float(v)


def project(profile:dict,workload:dict)->dict:
    if profile.get('schema')!='ftqc.conditional-native-architecture.v1':raise ValueError('unknown profile')
    family=profile.get('hardware_family')
    if family not in FAMILIES:raise ValueError('unsupported hardware family')
    if profile.get('input_evidence_class')!='illustrative_assumptions_unvalidated':
        raise ValueError('only explicitly illustrative profiles permitted by this model')
    if workload.get('schema')!='ftqc.logical-workload.v1' or set(workload.get('operation_counts',{}))!=set(OPERATIONS):
        raise ValueError('workload must define six native-agnostic logical operations')
    counts={k:workload['operation_counts'][k] for k in OPERATIONS}
    if any(type(v)!=int or v<0 for v in counts.values()):raise ValueError('operation counts must be nonnegative integers')
    if counts['t_gate']==0 or counts['clifford_2q']==0:raise ValueError('universal workload must contain T and entangling gates')
    timings=profile.get('operation_durations_us',{})
    probabilities=profile.get('operation_failure_probabilities',{})
    if set(timings)!=set(OPERATIONS) or set(probabilities)!=set(OPERATIONS):raise ValueError('all operations need timings and failures')
    for op in OPERATIONS:
        number(timings[op],op+' duration',strict=True)
        number(probabilities[op],op+' failure')
        if probabilities[op]>=1:raise ValueError('op failure must be < 1')
    resources=profile.get('physical_resource_assumptions',{})
    required={'native_unit','logical_data_units','factory_units_per_lane','factory_lanes','control_units','communication_units'}
    if set(resources)!=required or not isinstance(resources['native_unit'],str) or not resources['native_unit'].strip():
        raise ValueError('physical resources must be native and completely specified')
    for k in required-{'native_unit'}:number(resources[k],k,strict=(k=='logical_data_units' or k=='factory_lanes'))
    factories=resources['factory_lanes']
    if not factories.is_integer() or factories<1:raise ValueError('factory lanes must be positive integers')
    supply=profile.get('non_clifford_supply',{})
    if set(supply)!={'attempt_duration_us','accepted_state_probability','logical_error_probability_per_accepted_state'}:
        raise ValueError('must declare accepted-state supply and logical error assumptions')
    duration=number(supply['attempt_duration_us'],'attempt_duration_us',strict=True)
    p_accept=number(supply['accepted_state_probability'],'accepted_state_probability',strict=True)
    p_t=number(supply['logical_error_probability_per_accepted_state'],'magic logical error')
    if p_accept>1 or p_t>=1:raise ValueError('invalid magic state probabilities')
    # Optional assumption intervals are sensitivity ranges, *not* statistical
    # confidence or independently measured uncertainty. Fail closed if omitted
    # or inconsistent bounds are disguised as a calibration.
    ranges=profile.get('illustrative_failure_probability_ranges')
    t_range=profile.get('illustrative_accepted_t_error_range')
    a_range=profile.get('illustrative_acceptance_probability_range')
    if any(v is not None for v in (ranges,t_range,a_range)):
        if not isinstance(ranges,dict) or set(ranges)!=set(OPERATIONS) or t_range is None or a_range is None:
            raise ValueError('all six failure ranges plus T-error and acceptance ranges are required together')
        def check_range(values,value,name,exclusive_upper=False):
            if not isinstance(values,list) or len(values)!=2:raise ValueError(name+' must be [lower,upper]')
            low,high=(number(x,name) for x in values)
            if high >= 1 if exclusive_upper else high>1:raise ValueError(name+' upper probability invalid')
            if not (low<=value<=high):raise ValueError(name+' does not contain central assumption')
            return low,high
        bounds={op:check_range(ranges[op],probabilities[op],op,True) for op in OPERATIONS}
        tlo,thi=check_range(t_range,p_t,'T error',True)
        alo,ahi=check_range(a_range,p_accept,'acceptance probability')
        if alo<=0:raise ValueError('acceptance range must be strictly positive')
    else:
        bounds=None
    # The T-operation failure represents the injection gate, distinct from the
    # fidelity of its accepted resource state. Correlations are NOT modeled.
    log_success=0.0;critical_path=0.0
    for op in OPERATIONS:
        log_success+=counts[op]*math.log1p(-probabilities[op])
        critical_path+=counts[op]*timings[op]
    log_success+=counts['t_gate']*math.log1p(-p_t)
    magic_accepted=counts['t_gate']; mean_attempts=magic_accepted/p_accept
    supply_time=mean_attempts*duration/factories
    communication_us=number(profile.get('communication_critical_path_us'),'communication_critical_path_us')
    controller_us=number(profile.get('controller_critical_path_us'),'controller_critical_path_us')
    # Two envelopes, not a schedule claim: fully overlapped resource production
    # vs a pessimistic serial sum. Timings inside each term are user assumptions.
    optimistic=max(critical_path,supply_time,communication_us,controller_us)
    pessimistic=critical_path+supply_time+communication_us+controller_us
    scenario_uncertainty=None
    if bounds is not None:
        most_error=math.exp(sum(counts[op]*math.log1p(-bounds[op][1]) for op in OPERATIONS)+counts['t_gate']*math.log1p(-thi))
        least_error=math.exp(sum(counts[op]*math.log1p(-bounds[op][0]) for op in OPERATIONS)+counts['t_gate']*math.log1p(-tlo))
        scenario_uncertainty={
            'type':'assumption_sensitivity_range_NOT_a_confidence_interval',
            'independent_success_range':[most_error,least_error],
            'expected_factory_supply_time_us_range':[magic_accepted/ahi*duration/factories,
                                                      magic_accepted/alo*duration/factories]}
    total=resources['logical_data_units']+resources['factory_units_per_lane']*factories+resources['control_units']+resources['communication_units']
    return {'schema':'ftqc.conditional-native-architecture-result.v1','hardware_family':family,
            'workload_id':workload.get('id'),'input_evidence_class':'illustrative_assumptions_unvalidated',
            'calibration_status':'NOT_CALIBRATED','independent_hardware_validation':False,
            'native_resource_unit':resources['native_unit'],'assumption_sensitivity':scenario_uncertainty,
            'native_physical_resource_budget':{'logical_data':resources['logical_data_units'],
                'magic_factory':resources['factory_units_per_lane']*factories,
                'control':resources['control_units'],'communication':resources['communication_units'],
                'total':total},
            'prediction_conditional_on_assumptions':{'success_independent_errors':math.exp(log_success),
                'logical_computation_critical_path_us':critical_path,
                'expected_magic_state_attempts':mean_attempts,
                'mean_magic_state_supply_time_us':supply_time,
                'runtime_lower_bound_us':optimistic,
                'serial_upper_scheduling_envelope_us':pessimistic},
            'limitations':['No empirical device calibration or holdout validation',
                'Native unit counts are assumptions and incomparable across hardware families',
                'Failure probabilities assumed independent across gates, errors, and resource states',
                'Factory attempts are represented by expected throughput, not tail distribution',
                'Scheduling bounds are not an executable compilation or runtime guarantee',
                'Encoded T gate and state injection are modeled separately; no actual distillation circuit compiled']}

def run(profiles:Path,workload:Path,output:Path)->dict:
    p=json.loads(profiles.read_text());w=json.loads(workload.read_text())
    if p.get('schema')!='ftqc.conditional-four-family-profiles.v1':raise ValueError('bad profile bundle')
    fs=p.get('families',{})
    if set(fs)!=set(FAMILIES):raise ValueError('exactly four hardware families required')
    results={f:project(fs[f],w) for f in FAMILIES}
    out={'schema':'ftqc.four-family-conditional-workload.v1', 'evidence_level':'illustrative_sensitivity_analysis',
         'common_logical_workload':w,'hardware_comparison_validated':False,
         'warning':'This is a four-scenario illustration, not independently calibrated four-hardware FTQC predictions.',
         'results':results}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(out,indent=2)+'\n');return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--profiles',type=Path,required=True)
    p.add_argument('--workload',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.profiles,a.workload,a.output)
    print('Generated four-platform CONDITIONAL model, not measured hardware predictions:',a.output)
if __name__=='__main__':main()
