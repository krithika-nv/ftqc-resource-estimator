#!/usr/bin/env python3
"""One entry point for four-platform FTQC evidence collection.

The runner downloads sources to stable per-family directories and performs the
available calculations. It does not imply publication-quality hardware validation.
Blocked experimental tasks remain visible in the manifest, not silently skipped.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'ibm_fez': ROOT/'data/public_calibrations/2026/ibm_fez.tar.gz',
    'aurora': ROOT/'data/external_hardware/xanadu_aurora',
    'gkp': ROOT/'data/external_hardware/xanadu_gkp',
    'helios': ROOT/'data/external_hardware/quantinuum_helios',
    'ion_specs': ROOT/'data/external_hardware/quantinuum_specifications',
    'neutral_qec': ROOT/'data/external_hardware/neutral_atom_qec',
}
RESULTS = ROOT/'outputs/external_validation'


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run_id() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + str(os.getpid())


def safe_id(raw: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',raw) or raw in ('.','..'):
        raise ValueError('Invalid run ID; use up to 100 letters, digits, dashes, underscores or dots')
    return raw


def pipeline_plan(profile: str, fetch: bool) -> list[dict]:
    plan=[]
    def item(name, stage, family, produces, requires=None):
        plan.append({'step':name,'stage':stage,'family':family,'produces':str(produces),
                     'requires':str(requires) if requires else None})
    if fetch and profile in ('evidence','ibm','all'):
        item('download_ibm_fez','download','superconducting',SOURCES['ibm_fez'])
        if profile != 'ibm':
            for key,family in [('aurora','photonic'),('gkp','photonic'),('helios','trapped_ion'),('ion_specs','trapped_ion')]:
                item('fetch_'+key,'download',family,SOURCES[key])
            item('fetch_neutral_qec','download','neutral_atom',SOURCES['neutral_qec'])
    if profile in ('ci','science','all'):
        item('unit_tests','tests','all',ROOT/'logs/runs')
    if profile in ('science','all'):
        item('architecture_study','simulation','all',ROOT/'outputs/architecture_study')
        item('real_science','simulation','all',ROOT/'outputs/stim_memory')
    if profile in ('evidence','ibm','all'):
        item('ibm_evidence','analysis','superconducting',ROOT/'outputs/matched_hardware_evidence/ibm_fez',SOURCES['ibm_fez'])
        item('ibm_source_schema','analysis','superconducting',RESULTS/'IBM_SOURCE_SCHEMA.json',SOURCES['ibm_fez'])
        item('ibm_raw_decode','analysis','superconducting',ROOT/'data/verified/ibm_decoded_shots.csv',SOURCES['ibm_fez'])
        item('ibm_decoded','analysis','superconducting',RESULTS/'ibm_decoded_shots.json',ROOT/'data/verified/ibm_decoded_shots.csv')
        item('ibm_majority_decode','analysis','superconducting',ROOT/'data/verified/ibm_majority_shots.csv',SOURCES['ibm_fez'])
        item('ibm_calibration_readout_prediction','analysis','superconducting',RESULTS/'IBM_READOUT_ONLY_CALIBRATION.json',ROOT/'data/verified/ibm_majority_shots.csv')
        item('ibm_calibration_coverage','analysis','superconducting',RESULTS/'IBM_CALIBRATION_EPOCHS.json',SOURCES['ibm_fez'])
        if profile!='ibm':
            item('aurora_workbook','analysis','photonic',RESULTS/'aurora_workbook_schema.json',SOURCES['aurora']/'xanadu_aurora_plot_data.xlsx')
            item('aurora_reproduction','analysis','photonic',RESULTS/'aurora_reproduction/REPORT.json',SOURCES['aurora']/'xanadu_aurora_plot_data.xlsx')
            item('gkp_inventory','analysis','photonic',RESULTS/'gkp_source_inventory.json',SOURCES['gkp'])
            item('aurora_raw_numeric','analysis','photonic',RESULTS/'aurora_raw_quadratures.json',SOURCES['aurora']/'raw_numeric')
            item('helios_inventory','analysis','trapped_ion',RESULTS/'helios_source_inventory.json',SOURCES['helios'])
            item('ion_specs_inventory','analysis','trapped_ion',RESULTS/'ion_specs_source_inventory.json',SOURCES['ion_specs'])
            item('quantinuum_public_counts','analysis','trapped_ion',RESULTS/'quantinuum_public_counts.json',SOURCES['ion_specs'])
            item('helios_pickle_audit','analysis','trapped_ion',RESULTS/'helios_pickle_audit.json',SOURCES['helios'])
            item('helios_raw_counts','analysis','trapped_ion',RESULTS/'helios_raw_counts.json',SOURCES['helios'])
            item('helios_counts','analysis','trapped_ion',RESULTS/'helios_counts.json',ROOT/'data/verified/helios_counts.csv')
            item('neutral_source_survey','analysis','neutral_atom',RESULTS/'neutral_source_schemas.json',SOURCES['neutral_qec']/'Zenodo.zip')
            item('neutral_source_inventory','analysis','neutral_atom',RESULTS/'neutral_source_inventory.json',SOURCES['neutral_qec'])
            item('neutral_archive_inventory','analysis','neutral_atom',RESULTS/'neutral_source_archive.json',SOURCES['neutral_qec']/'Zenodo.zip')
            item('neutral_decoded','analysis','neutral_atom',RESULTS/'neutral_atom_decoded_shots.json',ROOT/'data/verified/neutral_atom_decoded_shots.csv')
    # Reports that the hardware-specific plan above does not list separately.
    # Model outputs and evidence snapshots use cross-platform scope, not a
    # falsely attributed hardware family.
    if profile in ('evidence','all'):
        item('helios_author_notebook_output','analysis','trapped_ion',
             RESULTS/'helios_mcmr_author_notebook.json',
             SOURCES['helios']/'notebooks/MCMR Crosstalk.ipynb')
        item('conditional_four_family_workload','illustrative_model','all',
             RESULTS/'CONDITIONAL_FOUR_PLATFORM_WORKLOAD.json')
        item('measured_primitive_ledger','characterization','all',
             RESULTS/'MEASURED_PRIMITIVE_LEDGER.json')
    if profile in ('evidence','ibm','all'):
        item('gate_review_snapshot','review','all',
             RESULTS/'GATE_EVIDENCE_CANDIDATES.json')
    return plan


def main(argv=None):
    p=argparse.ArgumentParser(description='Automate reproducibility and per-family downloads, inventories and verified-input analyses.')
    p.add_argument('--profile',choices=['ci','science','evidence','ibm','all'],default='all')
    p.add_argument('--run-id')
    p.add_argument('--fetch',action='store_true',help='Download checksum-verified IBM and approved public lightweight analysis sources')
    p.add_argument('--download-large-neutral',action='store_true',help='Explicitly allow the approximately 1 GB Zenodo source dataset download on this local machine')
    p.add_argument('--max-ibm-jobs',type=int,help='Fast smoke test only: limit IBM jobs, never publish as full experimental run')
    p.add_argument('--review-bundle',action='store_true',help='After running, package one small cross-platform ZIP with logs and source-metadata reports')
    p.add_argument('--plot-figures',action='store_true',help='Render optional Aurora plots (slow on clean CI runners)')
    p.add_argument('--dry-run',action='store_true',help='Print the full plan and source destinations without downloading or running')
    p.add_argument('--base-dir',type=Path,default=ROOT/'logs/runs')
    args=p.parse_args(argv)
    if args.max_ibm_jobs is not None and args.max_ibm_jobs<1:p.error('--max-ibm-jobs must be positive')
    ibm_limit=['--max-jobs',str(args.max_ibm_jobs)] if args.max_ibm_jobs else []
    rid=safe_id(args.run_id or run_id())
    plan=pipeline_plan(args.profile,args.fetch)
    if args.dry_run:
        print(json.dumps({'profile':args.profile,'fetch':args.fetch,'plan':plan},indent=2))
        return 0
    dest=(args.base_dir/rid).resolve()
    if dest.exists():p.error(f'Run directory already exists: {dest}')
    dest.mkdir(parents=True)
    states=[]
    env=os.environ.copy()
    env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT)+(os.pathsep+env['PYTHONPATH'] if env.get('PYTHONPATH') else '')

    def record(name,cmd,*,requires=(),family='all',stage='analysis',upstream=None):
        if upstream and not any(x['step']==upstream and x['status']=='passed' for x in states):
            states.append({'step':name,'family':family,'stage':stage,
                           'status':'blocked_upstream','reason':'Required predecessor did not pass: '+upstream})
            return
        absent=[str(Path(x)) for x in requires if not Path(x).exists()]
        if absent:
            states.append({'step':name,'family':family,'stage':stage,'status':'blocked_missing_input','reason':'Missing: '+', '.join(absent)})
            return
        file=dest/(f'{len(states)+1:02d}_{name}.log')
        began=time.monotonic()
        with file.open('w',encoding='utf8') as f:
            f.write('WORKDIR: '+str(ROOT)+'\nCOMMAND: '+ ' '.join(cmd)+'\n\n');f.flush()
            try:proc=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=False)
            except OSError as exc:f.write('ERROR: '+str(exc)+'\n');returncode=127
            else:returncode=proc.returncode
        states.append({'step':name,'family':family,'stage':stage,'status':'passed' if returncode==0 else 'failed',
                       'exit_code':returncode,'duration_seconds':round(time.monotonic()-began,2),
                       'log_file':file.name,'log_sha256':sha(file)})

    def blocked(name,reason,family,stage='analysis'):
        states.append({'step':name,'family':family,'stage':stage,'status':'blocked_missing_input','reason':reason})

    def file_analysis(name,sub,src,out,family,upstream=None):
        record(name,['bash','scripts/commands/RUN_EXTERNAL_VALIDATION.sh',sub,'--input',str(src),'--output',str(out)],requires=[src],family=family,upstream=upstream)

    if args.fetch and args.profile in ('evidence','ibm','all'):
        record('download_ibm_fez',[sys.executable,'scripts/tools/download_2026_qec_calibration.py','--backend','ibm_fez'],stage='download',family='superconducting')
        if args.profile!='ibm':
            for key,source,family in [('aurora','aurora','photonic'),('gkp','gkp','photonic'),
                                       ('helios','helios','trapped_ion'),('ion_specs','ion-specs','trapped_ion')]:
                record('fetch_'+key,[sys.executable,'scripts/automation/fetch_sources.py','--source',source]+
                       (['--max-megabytes','400'] if key=='ion_specs' else []),stage='download',family=family)
            record('fetch_neutral_qec',[sys.executable,'scripts/automation/zenodo_neutral_atom.py',
                 *(['--download-large'] if args.download_large_neutral else ['--download-small','--max-megabytes','10'])],stage='download',family='neutral_atom')

    if args.profile in ('ci','science','all'):
        record('unit_tests',[sys.executable,'-m','unittest','discover','-s','tests','-v'],stage='test')
    if args.profile in ('science','all'):
        record('architecture_study',['bash','scripts/commands/RUN_ARCHITECTURE_STUDY.sh'],stage='simulation')
        record('real_science',['bash','scripts/commands/RUN_ALL_VALIDATIONS.sh'],stage='simulation',upstream='architecture_study')
    if args.profile in ('evidence','ibm','all'):
        archive=SOURCES['ibm_fez']
        record('ibm_evidence',['bash','scripts/commands/RUN_MATCHED_HARDWARE_EVIDENCE.sh','--archive',str(archive),
            '--backend','ibm_fez','--max-age-days','365','--output-dir','outputs/matched_hardware_evidence/ibm_fez'],requires=[archive],family='superconducting')
        record('ibm_source_schema',[sys.executable,'-m','external_validation.ibm_raw','--archive',str(archive),
            '--backend','ibm_fez','--schema-only'],requires=[archive],family='superconducting')
        record('ibm_raw_decode',[sys.executable,'-m','external_validation.ibm_raw','--archive',str(archive),
            '--backend','ibm_fez','--decoder','mwpm','--skip-unsupported',*ibm_limit],requires=[archive],family='superconducting')
        file_analysis('ibm_decoded','ibm',ROOT/'data/verified/ibm_decoded_shots.csv',RESULTS/'ibm_decoded_shots.json','superconducting',upstream='ibm_raw_decode')
        record('ibm_majority_decode',[sys.executable,'-m','external_validation.ibm_raw','--archive',str(archive),
            '--backend','ibm_fez','--decoder','majority','--skip-unsupported',
            '--output',str(ROOT/'data/verified/ibm_majority_shots.csv'),
            '--summary',str(RESULTS/'ibm_majority_summary.json'),*ibm_limit],requires=[archive],family='superconducting')
        record('ibm_calibration_readout_prediction',[sys.executable,'-m','external_validation.ibm_readout_prediction',
            '--archive',str(archive),'--decoded',str(ROOT/'data/verified/ibm_majority_shots.csv'),
            '--output',str(RESULTS/'IBM_READOUT_ONLY_CALIBRATION.json'),*ibm_limit],
            requires=[archive,ROOT/'data/verified/ibm_majority_shots.csv'],
            upstream='ibm_majority_decode',family='superconducting')
        record('ibm_calibration_coverage',[sys.executable,'scripts/automation/ibm_epoch_audit.py',
                '--archive',str(archive),'--decode-summary',str(RESULTS/'ibm_raw_decode_summary.json'),
                '--output',str(RESULTS/'IBM_CALIBRATION_EPOCHS.json')],requires=[archive],family='superconducting')
        if args.profile != 'ibm':
            candidates=sorted(SOURCES['aurora'].rglob('xanadu_aurora_plot_data.xlsx')) if SOURCES['aurora'].exists() else []
            if candidates:
                file_analysis('aurora_workbook','aurora',candidates[0],RESULTS/'aurora_workbook_schema.json','photonic')
                record('aurora_reproduction',[sys.executable,'-m','external_validation.aurora_reproduce',
                       '--input',str(candidates[0]),'--output-dir',str(RESULTS/'aurora_reproduction'),
                       *([] if args.plot_figures else ['--no-plot'])],
                       requires=[candidates[0]],family='photonic')
            else:blocked('aurora_workbook','Missing Aurora figure workbook; fetch sources or inspect upstream checkout','photonic')
            file_analysis('gkp_inventory','inspect',SOURCES['gkp'],RESULTS/'gkp_source_inventory.json','photonic')
            opt_raw=sorted((SOURCES['aurora']/'raw_numeric').glob('*.npy')) if (SOURCES['aurora']/'raw_numeric').exists() else []
            units_file=SOURCES['aurora']/'raw_numeric/UNITS.txt'
            if opt_raw and units_file.is_file():
                units=units_file.read_text().strip()
                record('aurora_raw_numeric',[sys.executable,'-m','external_validation.aurora_raw_quadratures',
                    '--input',str(opt_raw[0]),'--units',units,'--output',str(RESULTS/'aurora_raw_quadratures.json')],
                    requires=[opt_raw[0]],family='photonic')
            else:blocked('aurora_raw_numeric','Optional: original optical raw numeric .npy export and UNITS.txt absent','photonic')
            file_analysis('helios_inventory','inspect',SOURCES['helios'],RESULTS/'helios_source_inventory.json','trapped_ion')
            file_analysis('ion_specs_inventory','inspect',SOURCES['ion_specs'],RESULTS/'ion_specs_source_inventory.json','trapped_ion')
            record('helios_author_notebook_output',[sys.executable,'-m','external_validation.helios_notebook',
                '--input',str(SOURCES['helios']/'notebooks/MCMR Crosstalk.ipynb'),
                '--output',str(RESULTS/'helios_mcmr_author_notebook.json')],
                requires=[SOURCES['helios']/'notebooks/MCMR Crosstalk.ipynb'],family='trapped_ion')
            record('quantinuum_public_counts',[sys.executable,'-m','external_validation.quantinuum_json_counts',
                '--source',str(SOURCES['ion_specs']), '--output',str(RESULTS/'quantinuum_public_counts.json')],
                requires=[SOURCES['ion_specs']],family='trapped_ion')
            candidates=sorted((SOURCES['helios']/'data').glob('exp_MCMR_Crosstalk_Helios-1*.p')) if (SOURCES['helios']/'data').is_dir() else []
            if candidates:
                real_mcmr=[p for p in candidates if '0,2,4,6,8,10,12,14' in p.name]
                candidate=real_mcmr[0] if real_mcmr else candidates[-1]
                record('helios_pickle_audit',[sys.executable,'-m','external_validation.helios_pickle_audit',
                    '--input',str(candidate),'--output',str(RESULTS/'helios_pickle_audit.json')],
                    requires=[candidate],family='trapped_ion')
                if real_mcmr:
                    record('helios_raw_counts',[sys.executable,'-m','external_validation.helios_static_counts',
                       '--input',str(candidate),'--output',str(RESULTS/'helios_raw_counts.json')],
                       requires=[candidate],family='trapped_ion')
                else:blocked('helios_raw_counts','Expected exact 98-qubit MCMR source pickle not found','trapped_ion')
            else:
                blocked('helios_pickle_audit','Helios paper pickle absent; static audit not run','trapped_ion')
                blocked('helios_raw_counts','Helios paper pickle absent; count reanalysis blocked','trapped_ion')
            file_analysis('helios_counts','helios',ROOT/'data/verified/helios_counts.csv',RESULTS/'helios_counts.json','trapped_ion')
            file_analysis('neutral_source_inventory','inspect',SOURCES['neutral_qec'],RESULTS/'neutral_source_inventory.json','neutral_atom')
            record('neutral_archive_inventory',[sys.executable,'-m','external_validation.neutral_archive',
                   '--input',str(SOURCES['neutral_qec']/'Zenodo.zip'),'--output',str(RESULTS/'neutral_source_archive.json')],
                   requires=[SOURCES['neutral_qec']/'Zenodo.zip'],family='neutral_atom')
            record('neutral_source_survey',[sys.executable,'-m','external_validation.neutral_source_survey',
                    '--archive',str(SOURCES['neutral_qec']/'Zenodo.zip'),
                    '--output',str(RESULTS/'neutral_source_schemas.json')],
                    requires=[SOURCES['neutral_qec']/'Zenodo.zip'],family='neutral_atom')
            file_analysis('neutral_decoded','neutral',ROOT/'data/verified/neutral_atom_decoded_shots.csv',RESULTS/'neutral_atom_decoded_shots.json','neutral_atom')

    if args.profile in ('evidence','all'):
        record('conditional_four_family_workload',[sys.executable,'-m','ftqc_resource_estimator.conditional_architecture',
               '--profiles','examples/SCENARIO_ONLY_native_four_family_profiles.json',
               '--workload','evidence/validation/reference_workload.json',
               '--output',str(RESULTS/'CONDITIONAL_FOUR_PLATFORM_WORKLOAD.json')],
               stage='illustrative_model',family='all')
    if args.profile in ('evidence','all'):
        record('measured_primitive_ledger',[sys.executable,'-m','external_validation.measured_primitives',
            '--ibm',str(SOURCES['ibm_fez']),
            '--helios',str(RESULTS/'helios_mcmr_author_notebook.json'),
            '--quantinuum',str(RESULTS/'quantinuum_public_counts.json'),
            '--helios-raw',str(RESULTS/'helios_raw_counts.json'),
            '--aurora',str(RESULTS/'aurora_reproduction/REPORT.json'),
            '--neutral',str(ROOT/'evidence/neutral_atom_zenodo_metadata.json'),
            '--output',str(RESULTS/'MEASURED_PRIMITIVE_LEDGER.json')],family='all',stage='characterization')
    if args.profile in ('evidence','ibm','all'):
        record('gate_review_snapshot',[sys.executable,'scripts/automation/review_dossiers.py',
             '--output',str(RESULTS/'GATE_EVIDENCE_CANDIDATES.json')],family='all',stage='review')
    families=['superconducting','photonic','trapped_ion','neutral_atom']
    by_family={fam:{'passed':[s['step'] for s in states if s['family']==fam and s['status']=='passed'],
                    'blocked':[s['step'] for s in states if s['family']==fam and s['status'].startswith('blocked_')],
                    'failed':[s['step'] for s in states if s['family']==fam and s['status']=='failed']}
               for fam in families}
    execution_passed=not any(x['status']=='failed' for x in states)
    ibm_decoding_receipt=RESULTS/'ibm_raw_decode_summary.json'
    ibm_decoder_status=None
    if any(x['step']=='ibm_raw_decode' and x['status']=='passed' for x in states) and ibm_decoding_receipt.is_file():
        receipt=json.loads(ibm_decoding_receipt.read_text())
        ibm_decoder_status={'status':receipt.get('status'),'total_chain_shots':receipt.get('total_decoded_chain_shots'),
                            'skipped_job_count':len(receipt.get('skipped_jobs',[])),
                            'all_jobs_processed':receipt.get('all_jobs_processed',False),
                            'calibration_conditioned':receipt.get('calibration_conditioned',False)}

    external=[x for x in states if x['stage']=='analysis' and x['family'] in families]
    report={'schema':'ftqc.pipeline.run.v2','run_id':rid,'profile':args.profile,'fetch_requested':args.fetch,
            'ibm_smoke_job_limit':args.max_ibm_jobs, 'full_dataset_validation_run':args.max_ibm_jobs is None,
            'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'python':sys.version.split()[0],
            'source_destinations':{k:str(v) for k,v in SOURCES.items()},'steps':states,'platforms':by_family,
            'execution_passed':execution_passed,
            'analysis_pipeline_complete':all(x['status']=='passed' for x in external) if external else False,
            'all_external_inputs_available':bool(external) and all(x['status']=='passed' for x in external),
            'hardware_validation_completed':False,'ibm_decoder_evidence':ibm_decoder_status,
            'caveat':'Passing download, inspection, simulator and decoded-shot stages does NOT reproduce all four papers, establish calibrated hardware prediction or validate FTQC cross-platform performance.'}
    (dest/'run_manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    lines=['# FTQC multi-platform run '+rid,'','| Family | Passed | Blocked | Failed |','|---|---:|---:|---:|']
    for fam,st in by_family.items():lines.append('| '+fam+' | '+str(len(st['passed']))+' | '+str(len(st['blocked']))+' | '+str(len(st['failed']))+' |')
    lines.extend(['','## Steps',''])
    lines.extend('- **'+s['step']+'** ('+s['family']+'): '+s['status']+(' - '+s['reason'] if 'reason' in s else '') for s in states)
    lines.extend(['',report['caveat'],''])
    (dest/'SUMMARY.md').write_text('\n'.join(lines))
    from acceptance_gate_report import report as gate_report
    RESULTS.mkdir(parents=True,exist_ok=True)
    (RESULTS/'HARDWARE_EVIDENCE_GATES.json').write_text(json.dumps(gate_report(report),indent=2,sort_keys=True)+'\n')
    if args.profile in ('evidence', 'ibm', 'all'):
        from audit_ftqc_end_to_end import audit as ftqc_acceptance_audit
        acceptance=ftqc_acceptance_audit(json.loads((ROOT/'evidence/validation/four_family_evidence.json').read_text()))
        (RESULTS/'FOUR_PLATFORM_FTQC_ACCEPTANCE.json').write_text(json.dumps(acceptance,indent=2,sort_keys=True)+'\n')
        from component_progress import build_report, as_markdown
        component_status=build_report(acceptance, report)
        (RESULTS/'COMPONENT_PROGRESS.json').write_text(json.dumps(component_status,indent=2,sort_keys=True)+'\n')
        (RESULTS/'COMPONENT_PROGRESS.md').write_text(as_markdown(component_status))
        report['component_progress_report']='outputs/external_validation/COMPONENT_PROGRESS.json'
        report['four_platform_ftqc_evidence_file_contracts_met']=acceptance['all_evidence_file_contracts_met']
        report['hardware_validation_completed']=False
        (dest/'run_manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    if args.review_bundle:
        from package_platform_review import generate
        bundle=ROOT/'outputs/FOUR_PLATFORM_REVIEW_BUNDLE.zip'
        generate(bundle,dest)
        print('Review bundle:',bundle)
    print(json.dumps({'logs':str(dest),'execution_passed':execution_passed,
            'analysis_pipeline_complete':all(x['status']=='passed' for x in external) if external else False,
                      'all_external_inputs_available':report['all_external_inputs_available'],
                      'platforms':by_family,'steps':[{k:v for k,v in s.items() if k in ('step','status','reason')} for s in states]},indent=2))
    return 0 if execution_passed else 1

if __name__=='__main__':sys.exit(main())
