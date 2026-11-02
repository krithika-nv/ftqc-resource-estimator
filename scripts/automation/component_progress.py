#!/usr/bin/env python3
"""Report observed engineering work separately from strict FTQC scientific acceptance.

Never infer that code presence, a passing download, or a published-data replot
constitutes independent experimental validation. Files and run logs are observations,
not a self-certification of their scientific methodology.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ('superconducting', 'photonic', 'trapped_ion', 'neutral_atom')

# Explicit narrow capabilities, each linked to source, tests and optional saved evidence.
# A recorded evidence file is a traceable output, NOT automatically a reproduced paper or
# a gate in the full-stack hardware acceptance manifest.
COMPONENTS = {
 'superconducting': (
  ('raw_repetition_shots','IBM repetition-code register reader', 'external_validation/ibm_raw.py','tests/test_ibm_raw_decoder.py','evidence/verified/IBM_FEZ_D11_R1_JOB1_MAJORITY.json','measured_single_job_majority_baseline','ibm_raw_decode'),
  ('calibration_coverage','Historical Fez calibration-epoch audit','scripts/automation/ibm_epoch_audit.py','tests/test_ibm_epoch_audit.py','evidence/verified/IBM_FEZ_CALIBRATION_EPOCH_AUDIT.json','historical_calibration_inventory','ibm_calibration_coverage'),
  ('native_analysis','Repetition-code numerical analysis','src/ftqc_resource_estimator/ibm_hardware_analysis.py','tests/test_platform_numeric_analysis.py',None,'implementation_only','ibm_decoded'),
  ('surface_memory_simulator','Rotated surface-code Stim/PyMatching simulator','src/ftqc_resource_estimator/stim_memory.py','tests/test_real_stim.py','outputs/stim_memory/VALIDATED_RUN.json','simulator_not_ibm_hardware','real_science'),
  ('physical_noise_fit','Calibrated circuit-level physical noise','src/ftqc_resource_estimator/ibm_calibrated_noise.py','tests/test_ibm_calibrated_noise.py',None,'planned_not_implemented',None),
  ('matched_holdout','Circuit-matched held-out prediction and residuals','src/ftqc_resource_estimator/ibm_prediction_holdout.py','tests/test_ibm_prediction_holdout.py',None,'planned_not_implemented',None),
  ('native_logical_clifford','Verified hardware-native logical Clifford gates','src/ftqc_resource_estimator/ibm_logical_clifford.py','tests/test_ibm_logical_clifford.py',None,'planned_not_implemented',None),
  ('native_nonclifford','Verified non-Clifford resource path','src/ftqc_resource_estimator/ibm_nonclifford.py','tests/test_ibm_nonclifford.py',None,'planned_not_implemented',None),
 ),
 'photonic': (
  ('aurora_replot','Aurora figures 3c/3d replot from published workbook','external_validation/aurora_reproduce.py','tests/test_aurora_reproduction.py','evidence/verified/AURORA_PUBLISHED_FIGURE_DATA_REPORT.json','published_figure_data_replot_not_raw_optics','aurora_reproduction'),
  ('gkp_numerics','GKP/density-matrix numerical diagnostics','src/ftqc_resource_estimator/xanadu_analysis.py','tests/test_platform_numeric_analysis.py',None,'implementation_only','gkp_inventory'),
  ('physical_noise_fit','Measured-loss and GKP-noise calibration','src/ftqc_resource_estimator/photonic_calibrated_noise.py','tests/test_photonic_calibrated_noise.py',None,'planned_not_implemented',None),
  ('native_qec','Raw optical shot GKP QEC decoder reproduction','src/ftqc_resource_estimator/photonic_qec.py','tests/test_photonic_qec.py',None,'planned_not_implemented',None),
  ('native_gates','Native protected Clifford and non-Clifford path','src/ftqc_resource_estimator/photonic_logical_gates.py','tests/test_photonic_logical_gates.py',None,'planned_not_implemented',None),
  ('matched_holdout','Matched GKP/logical experiment holdout','src/ftqc_resource_estimator/photonic_holdout.py','tests/test_photonic_holdout.py',None,'planned_not_implemented',None),
 ),
 'trapped_ion': (
  ('helios_cached_outputs','Helios saved-notebook numeric output extractor','external_validation/helios_notebook.py','tests/test_release_candidate.py','evidence/verified/HELIOS_MCMR_CACHED_NOTEBOOK_OUTPUT.json','author_saved_notebook_values_not_raw_reanalysis','helios_author_notebook_output'),
  ('ion_statistics','Verified-count trapped-ion statistical analysis','src/ftqc_resource_estimator/quantinuum_analysis.py','tests/test_platform_numeric_analysis.py',None,'implementation_only','helios_counts'),
  ('physical_noise_fit','Gate, leakage, SPAM and transport calibration','src/ftqc_resource_estimator/ion_calibrated_noise.py','tests/test_ion_calibrated_noise.py',None,'planned_not_implemented',None),
  ('native_qec','Hardware-matched ion logical-code reproduction','src/ftqc_resource_estimator/ion_native_qec.py','tests/test_ion_native_qec.py',None,'planned_not_implemented',None),
  ('native_gates','Native protected Clifford and non-Clifford path','src/ftqc_resource_estimator/ion_logical_gates.py','tests/test_ion_logical_gates.py',None,'planned_not_implemented',None),
  ('matched_holdout','Independent Helios logical-protocol holdout','src/ftqc_resource_estimator/ion_holdout.py','tests/test_ion_holdout.py',None,'planned_not_implemented',None),
 ),
 'neutral_atom': (
  ('source_archive','Loss-aware QEC archive safe inventory','external_validation/neutral_archive.py','tests/test_neutral_archive.py',None,'implementation_only','neutral_archive_inventory'),
  ('scheduling','Neutral-atom geometry and scheduling model','src/ftqc_resource_estimator/neutral_atom_schedule.py','tests/test_platform_numeric_analysis.py','outputs/neutral_atom_schedule_illustrative/NEUTRAL_ATOM_SCHEDULING.json','illustrative_scheduling_not_device_calibration',None),
  ('randomized_measurement','Neutral-atom randomized measurement diagnostic','src/ftqc_resource_estimator/quera_analysis.py','tests/test_platform_numeric_analysis.py',None,'implementation_only','neutral_decoded'),
  ('physical_noise_fit','Gate-loss-erasure-rearrangement calibration','src/ftqc_resource_estimator/neutral_calibrated_noise.py','tests/test_neutral_calibrated_noise.py',None,'planned_not_implemented',None),
  ('native_qec','Published loss-aware decoder and logical-memory reproduction','src/ftqc_resource_estimator/neutral_loss_aware_qec.py','tests/test_neutral_loss_aware_qec.py',None,'planned_not_implemented',None),
  ('native_gates','Verified protected neutral-atom logical gates','src/ftqc_resource_estimator/neutral_logical_gates.py','tests/test_neutral_logical_gates.py',None,'planned_not_implemented',None),
  ('matched_holdout','Independent experimental neutral-atom holdout','src/ftqc_resource_estimator/neutral_holdout.py','tests/test_neutral_holdout.py',None,'planned_not_implemented',None),
 ),
}
SHARED = (
 ('conditional_workload','Illustrative four-family logical workload','src/ftqc_resource_estimator/conditional_architecture.py','tests/test_release_candidate.py','outputs/external_validation/CONDITIONAL_FOUR_PLATFORM_WORKLOAD.json','illustrative_not_hardware_calibrated','conditional_four_family_workload'),
 ('logic_primitive_baseline','Conditional logical-primitive probability composition','src/ftqc_resource_estimator/full_stack_prediction.py','tests/test_full_stack_prediction.py',None,'implementation_only',None),
)
TRACK_A = (
 ('architecture_pareto','Original architecture Pareto optimization','src/ftqc_resource_estimator/pareto.py','tests/test_pareto.py','outputs/architecture_study/ARCHITECTURE_REPORT.md','heuristic_model'),
 ('distance9_memory','Distance-9 surface-code memory','src/ftqc_resource_estimator/stim_memory.py','tests/test_memory_followup.py','outputs/stim_memory/followup/analysis/MEMORY_REPORT.md','simulator'),
 ('controller_cost','Controller-cost Pareto tradeoffs','src/ftqc_resource_estimator/controller_capacity.py','tests/test_controller_capacity.py','outputs/stim_memory/followup/control_cost_analysis/MEMORY_REPORT.md','simulator_plus_assumed_costs'),
 ('distance11_architecture','Distance-11 heuristic architecture','src/ftqc_resource_estimator/architecture.py','tests/test_architecture.py','outputs/architecture_study/ARCHITECTURE_REPORT.md','heuristic_model'),
 ('literature_aligned','Literature-aligned memory benchmark','src/ftqc_resource_estimator/literature_benchmark.py','tests/test_literature_benchmark.py',None,'simulator_outputs_not_bundled'),
 ('idle_noise','Controller-induced idle-noise model','src/ftqc_resource_estimator/idle_coherence.py','tests/test_idle_coherence.py',None,'simulator_outputs_not_bundled'),
)


def load_run_manifest(path: Path | None = None, review_bundle: Path | None = None):
    if review_bundle:
        with zipfile.ZipFile(review_bundle) as z:
            matches=[n for n in z.namelist() if n.startswith('logs/') and n.endswith('/run_manifest.json')]
            if not matches: raise ValueError('No run manifest in review bundle')
            return json.loads(z.read(sorted(matches)[-1]))
    if path: return json.loads(path.read_text())
    # Do NOT silently use a previous run: it may refer to an older source revision.
    return None


def _component(entry, run_states, root=ROOT):
    key,title,source,test,artifact,scope,step=entry
    source_present=(root/source).is_file()
    test_present=(root/test).is_file()
    record_present=bool(artifact and (root/artifact).is_file())
    return {'id':key,'title':title,'source':source,'test':test,'source_present':source_present,'planned_not_implemented':scope=='planned_not_implemented' and not source_present,
            'test_file_present_not_test_execution':test_present,
            'recorded_artifact':artifact,'recorded_artifact_present':record_present,
            'recorded_artifact_scope':scope,
            'recent_step':step,'recent_step_status':run_states.get(step,'not_checked') if step else 'not_applicable',
            'scientific_acceptance_inferred':False}


def build_report(acceptance: dict, run: dict | None = None, root=ROOT) -> dict:
    states={s['step']:s['status'] for s in (run or {}).get('steps',[])}
    result={}; totals={'component_definitions':0,'source_files_present':0,'test_files_present':0,'saved_artifact_files_present':0,'steps_passed_in_supplied_run':0}
    for family in FAMILIES:
        comps=[_component(x,states,root) for x in COMPONENTS[family]]
        gate=acceptance['families'][family]
        registered=sum(1 for value in gate['gates'].values() if value['status']!='missing')
        hashes=gate['gates_with_matching_files']
        summary={'component_definitions':len(comps),
                 'source_files_present':sum(x['source_present'] for x in comps),
                 'test_files_present':sum(x['test_file_present_not_test_execution'] for x in comps),
                 'saved_artifact_files_present':sum(x['recorded_artifact_present'] for x in comps),
                 'steps_passed_in_supplied_run':sum(x['recent_step_status']=='passed' for x in comps)}
        for k,v in summary.items():totals[k]+=v
        result[family]={'component_progress':summary,'components':comps,
                        'scientific_acceptance':{
                           'total_gates':gate['required_gate_count'],
                           'gate_dossiers_registered':registered,
                           'gate_dossier_files_hash_matched':hashes,
                           'independent_scientific_review_completed':False,
                           'missing_gate_ids':[key for key,value in gate['gates'].items() if value['status']=='missing']},
                        'not_equivalent_to':'An implemented component or recorded artifact does not satisfy a full-stack evidence gate.'}
    a=[_component((id,title,source,test,artifact,scope,None),states,root) for id,title,source,test,artifact,scope in TRACK_A]
    s=[_component(x,states,root) for x in SHARED]
    return {'schema':'ftqc.component-progress.v1','latest_run_id':(run or {}).get('run_id'),
            'latest_run_profile':(run or {}).get('profile'),
            'family_component_summary':totals,'families':result,
            'track_a':{'studies':a,'source_files_present':sum(x['source_present'] for x in a),
                       'saved_report_files_present':sum(x['recorded_artifact_present'] for x in a)},
            'shared_conditional_models':s,
            'strict_acceptance_summary':{'gates_total':sum(x['scientific_acceptance']['total_gates'] for x in result.values()),
                 'registered_dossiers':sum(x['scientific_acceptance']['gate_dossiers_registered'] for x in result.values()),
                 'hash_matched_dossiers':sum(x['scientific_acceptance']['gate_dossier_files_hash_matched'] for x in result.values()),
                 'hardware_validated_end_to_end':False},
            'interpretation':{
                'zero_of_34':'The evidence manifest contains zero qualifying submitted gate dossiers; this is not a score of failed experiments or absent software.',
                'code_and_tests':'Source/test file presence shows implementation and test coverage exist; test execution is verified separately by CI.',
                'saved_artifacts':'Record presence proves only that a report exists, not its raw-data authenticity or methodology.',
                'full_stack':'No four-family independently validated universal FTQC prediction is certified by this report.'}}


def as_markdown(r):
    lines=['# FTQC evidence dashboard - component progress versus scientific acceptance','',''
           '> **Do not interpret 0/34 as 34 failed experiments.** The strict manifest has no submitted full-stack evidence dossiers. This dashboard reports a **selected implemented-and-planned capability inventory**, not a percentage of all required analysis. File/run observations are **separate** from certification.','',
           '| Hardware | Component code | Test files | Saved scoped evidence | Last supplied run steps passed | Strict gate dossiers |',
           '|---|---:|---:|---:|---:|---:|']
    for family in FAMILIES:
        x=r['families'][family];c=x['component_progress'];g=x['scientific_acceptance']
        lines.append(f"| {family.replace('_',' ').title()} | {c['source_files_present']}/{c['component_definitions']} | {c['test_files_present']}/{c['component_definitions']} | {c['saved_artifact_files_present']}/{c['component_definitions']} | {c['steps_passed_in_supplied_run']}/{c['component_definitions']} | {g['gate_dossier_files_hash_matched']}/{g['total_gates']} (registered {g['gate_dossiers_registered']}) |")
    lines += ['','**How to read the table:** Denominators include selected planned-but-unimplemented capabilities. Code and test-file counts are filesystem observations, *not* pass rates or a science-completeness percentage. Saved evidence includes narrowly qualified published-data replots, measured-shot baselines, and illustrative simulations. Missing latest run information is displayed as zero (no observed pass), **not as failure**. Matching a gate dossier hash is not independent scientific peer review.',
              '',f"**Run context:** {r['latest_run_id'] or 'No matching pipeline run was supplied'}. This dashboard is not a hardware readiness percentage.",'',
              '## Track A - simulator-backed and heuristic analysis','',
              '| Study | Source | Report present | Scope |','|---|---|---|---|']
    for x in r['track_a']['studies']:
        lines.append(f"| {x['title']} | `{x['source']}` | {'Yes' if x['recorded_artifact_present'] else 'Not bundled; regenerate'} | {x['recorded_artifact_scope'].replace('_',' ')} |")
    lines += ['','## Track B - actual per-family components','']
    for family in FAMILIES:
        x=r['families'][family];lines += [f"### {family.replace('_',' ').title()}",'',
             '| Component | Recorded evidence | Last pipeline step |','|---|---|---|']
        for c in x['components']:
            e=('**Planned: not implemented**' if c['planned_not_implemented'] else f"`{c['recorded_artifact']}` - {c['recorded_artifact_scope'].replace('_',' ')}" if c['recorded_artifact_present'] else 'No bundled result')
            lines.append(f"| {c['title']} | {e} | {c['recent_step_status']} |")
        g=x['scientific_acceptance'];lines+=['',f"Strict hardware-specific evidence files: **{g['gate_dossier_files_hash_matched']}/{g['total_gates']}**. Missing requirements: {', '.join(g['missing_gate_ids']) or 'none (still requires methodological review)'}. The entire model is **not certified**.",'']
    lines += ['## Shared models','']
    for x in r['shared_conditional_models']:
        lines.append(f"- **{x['title']}** - source present: {x['source_present']}; saved artifact: {x['recorded_artifact_present']}; evidence scope: {x['recorded_artifact_scope'].replace('_',' ')}.")
    lines += ['','## Scientific qualification and next action','',
          '1. The full-stack gate manifest (`evidence/validation/four_family_evidence.json`) is empty. A legitimate gate dossier requires source hashes, a matching experiment/protocol, independent prediction and holdout evidence, and a methodology review. Never fill it automatically from code or source inventories.',
          '2. Record actual CI execution separately from test-file presence. On each four-family evidence run, retain the run manifest plus this report in the GitHub artifact bundle.',
          '3. Prioritize converting specific sub-results into reviewed, source-traceable evidence dossiers. Do not count figures, notebook cached values, or toy workload output as certified end-to-end native FTQC predictions.',
          '']
    return '\n'.join(lines)


def main(argv=None):
    from audit_ftqc_end_to_end import audit
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=ROOT/'evidence/validation/four_family_evidence.json')
    p.add_argument('--run-manifest',type=Path)
    p.add_argument('--source-review-bundle',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/external_validation/COMPONENT_PROGRESS.json')
    p.add_argument('--markdown',type=Path,default=ROOT/'outputs/external_validation/COMPONENT_PROGRESS.md')
    args=p.parse_args(argv)
    report=build_report(audit(json.loads(args.manifest.read_text())),
                        load_run_manifest(args.run_manifest,args.source_review_bundle))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.markdown.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    args.markdown.write_text(as_markdown(report))
    print(f"Component progress: {args.output}\nEvidence dashboard: {args.markdown}\nStrict gate dossiers: {report['strict_acceptance_summary']['hash_matched_dossiers']}/{report['strict_acceptance_summary']['gates_total']} (not a score of failed experiments)")
    return 0

if __name__=='__main__':
    raise SystemExit(main())
