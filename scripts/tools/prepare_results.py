"""Validate and assemble *allowlisted* analysis outputs for GitHub Actions artifacts.

No real-backend files may be published in `--mode full` unless they actually exist.
This script does not execute quantum engines and never creates mock observations.
"""
import argparse
import csv
from hashlib import sha256
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Permit running directly from a source checkout without editable pip installation.
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def checked_csv(path, required, minimum=1):
    if not path.exists():
        raise RuntimeError(f'Missing result CSV: {path}')
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(set(reader.fieldnames or [])):
            raise RuntimeError(f'Incomplete result fields in {path}: {sorted(required)}')
        rows = list(reader)
    if len(rows) < minimum:
        raise RuntimeError(f'Expected at least {minimum} data rows: {path}')
    return rows


def copy_required(src, dest, staging):
    item = ROOT / src
    if not item.is_file():
        raise RuntimeError(f'Required output missing: {src}')
    target = staging / dest
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(item, target)


def copy_existing_tree(src, dest, staging, extensions):
    basedir = ROOT / src
    if not basedir.is_dir():
        raise RuntimeError(f'Output directory missing: {src}')
    count = 0
    for item in basedir.rglob('*'):
        if item.is_file() and item.suffix.lower() in extensions:
            copy_required(item.relative_to(ROOT), Path(dest) / item.relative_to(basedir), staging)
            count += 1
    if count == 0:
        raise RuntimeError(f'No publishable results found under: {src}')
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True, choices=['offline', 'full'])
    parser.add_argument('--output-dir', type=Path, default=Path('build/publication'))
    args = parser.parse_args()
    destination = (ROOT / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    if destination == ROOT or ROOT in destination.parents and destination.name == 'docs':
        raise ValueError('Select a dedicated staging directory, not the source repository')
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    allowed = {'.csv', '.png', '.md', '.json', '.txt'}
    project = ROOT.name
    snippets = []
    if project == 'ftqc-resource-estimator':
        rows = checked_csv(ROOT / 'outputs/architecture_study/pareto_feasible.csv', {'architecture','distance','total_site_equivalents','latency_us'}, 2)
        for row in rows:
            if float(row['total_site_equivalents']) <= 0 or float(row['latency_us']) <= 0:
                raise RuntimeError('Unphysical numeric sign in illustrative Pareto study')
        copy_existing_tree('outputs/architecture_study', 'architecture_study', destination, allowed)
        copy_existing_tree('outputs/hardware_profiles', 'hardware_profiles', destination, allowed)
        for s in ('outputs/repetition_sanity.csv', 'outputs/queue_sanity.csv'):
            copy_required(Path(s),Path(s).name,destination)
        copy_required('docs/reference/PROVENANCE_AND_CLAIMS.md', 'FIGURE_AND_CLAIM_AUDIT.md',destination)
        # Independently reconstructed arithmetic of published IBM readout
        # values: SECONDARY DATA, not newly executed hardware measurements.
        source_dir=ROOT/'outputs/published_readout'
        from ftqc_resource_estimator.published_readout_evidence import DATA, summarize, write_report
        source_record=source_dir/'SOURCE_RECORD.json'
        source_summary=source_dir/'RECALCULATED_SUMMARY.json'
        if not source_record.exists() or not source_summary.exists():
            raise RuntimeError('Missing published readout secondary empirical audit; run scripts/commands/RUN_PUBLISHED_READOUT_AUDIT.sh')
        if json.loads(source_record.read_text()) != DATA or json.loads(source_summary.read_text()) != summarize():
            raise RuntimeError('Published readout source or arithmetic was modified without verification')
        import tempfile as _tempfile
        with _tempfile.TemporaryDirectory() as _t:
            _p=Path(_t);write_report(_p)
            for _f in ('published_readout_comparison.csv','PUBLISHED_READOUT_AUDIT.md'):
                if (source_dir/_f).read_bytes() != (_p/_f).read_bytes():
                    raise RuntimeError(f'Published readout audit inconsistent with frozen source: {_f}')
        copy_existing_tree('outputs/published_readout','published_readout',destination,allowed)
        snippets.append('**Secondary published measurement comparison:** IBM Nighthawk 2026 study readout times and per-round logical errors are reported-source data, not newly measured or simulated results. This does NOT calibrate the Willow-based hypothetical control scenarios.')

        # Archived measured calibration is publishable only after strict regeneration
        # from the committed, openly attributed source subset. Its derived Stim
        # knobs are illustrative and never evidence of physical QPU validation.
        from ftqc_resource_estimator.public_calibration import (
            validate_calibration, produce_outputs, CURATED_URL, CURATED_DATE)
        curated_path=ROOT/'examples/public_ibmq_manila_2024_subset.json'
        raw_curated=curated_path.read_bytes()
        curated_obj=validate_calibration(json.loads(raw_curated))
        if curated_obj.get('backend_name')!='ibmq_manila' or curated_obj.get('last_update_date')!=CURATED_DATE or curated_obj.get('upstream_raw_url')!=CURATED_URL:
            raise RuntimeError('Unrecognized historical IBM calibration reference')
        with _tempfile.TemporaryDirectory() as _t:
            temp=Path(_t)
            produce_outputs(curated_obj,temp,source_type='CURATED_PUBLISHED_SUBSET',
                           source_sha256=sha256(raw_curated).hexdigest(),source_url=CURATED_URL)
            files=['normalized_calibration.json','calibration_projection.json',
                   'provenance.json','qubit_calibrations.csv','coupling_errors.csv',
                   'CALIBRATION_IMPORT_REPORT.md']
            for filename in files:
                if (ROOT/'outputs/public_calibration'/filename).read_bytes()!=(temp/filename).read_bytes():
                    raise RuntimeError(f'Calibration source or derived values changed: {filename}; rerun scripts/commands/RUN_PUBLIC_CALIBRATION.sh and inspect')
        copy_existing_tree('outputs/public_calibration','public_calibration',destination,allowed)
        snippets.append('**Real historical IBM calibration:** 2024 Qiskit Manila measured qubit/gate properties are ingested from an attributed curated transcription. Model-projected noise is explicitly NOT physically validated; full raw-file integrity is not established by the subset SHA.')

        snippets.append('**Illustrative models:** the site/time Pareto set and hardware sensitivities are neither calibrated logical-gate results nor predictions for named quantum machines.')
        if args.mode == 'full':
            validation = ROOT / 'outputs/stim_memory/VALIDATED_RUN.json'
            metadata = json.loads(validation.read_text()) if validation.is_file() else None
            if not isinstance(metadata, dict) or not metadata:
                raise RuntimeError('Stim memory scientific validation evidence absent')
            observations = ROOT/'outputs/stim_memory/observations.json'
            obs = json.loads(observations.read_text()) if observations.is_file() else {}
            if obs.get('schema') != 'ftqc.rotated_surface_memory.v1' or len(obs.get('observations',[])) != 9:
                raise RuntimeError('Matched real Stim record not present')
            if (metadata.get('total_shots') != 180000 or metadata.get('observations') != 9 or
                    not str(metadata.get('status','')).startswith('PASSED')):
                raise RuntimeError('Original memory run not verified for exact protocol')
            if sha256(observations.read_bytes()).hexdigest() != metadata.get('observation_sha256'):
                raise RuntimeError('Original memory results changed since verification')
            followup_path = ROOT / 'outputs/stim_memory/followup/observations.json'
            evidence_path = ROOT / 'outputs/stim_memory/followup/VERIFIED_FOLLOWUP.json'
            followup = json.loads(followup_path.read_text()) if followup_path.is_file() else {}
            evidence = json.loads(evidence_path.read_text()) if evidence_path.is_file() else {}
            if (evidence.get('total_shots') != 40000 or evidence.get('observations') != 2 or
                    not str(evidence.get('status','')).startswith('PASSED') or
                    evidence.get('stim_version') != followup.get('software',{}).get('stim') or
                    evidence.get('pymatching_version') != followup.get('software',{}).get('pymatching') or
                    followup.get('schema') != 'ftqc.rotated_surface_memory.v1' or
                    len(followup.get('observations', [])) != 2 or
                    sha256(followup_path.read_bytes()).hexdigest() != evidence.get('observation_sha256')):
                raise RuntimeError('Verified d7/d9 real-backend follow-up missing/stale. Run scripts/commands/RUN_STIM_MEMORY_FOLLOWUP.sh')
            # Do not trust a publication-stage copy without recomputing the
            # report/CSV numbers from the source observation manifest.
            from ftqc_resource_estimator.memory_analysis import validate_stim_manifest
            from ftqc_resource_estimator.memory_analysis import compare_memory, load_memory_scenarios
            validate_stim_manifest(followup, basis='X', physical_error=.003, rounds=9, distances=(7,9))
            if any(x['shots'] != 20000 for x in followup['observations']):
                raise RuntimeError('Unregistered follow-up protocol')
            from importlib.util import spec_from_file_location, module_from_spec
            spec=spec_from_file_location('followup_release_audit',ROOT/'scripts/tools/verify_scientific_followup.py')
            followup_audit=module_from_spec(spec)
            spec.loader.exec_module(followup_audit)
            followup_audit.audit_followup(
                followup,
                baseline_csv=ROOT/'outputs/stim_memory/followup/analysis/memory_tradeoffs.csv',
                sensitivity_csv=ROOT/'outputs/stim_memory/followup/control_cost_analysis/memory_tradeoffs.csv',
            )
            # The literature-aligned real-backend run MUST be replay-verified;
            # no output substitution from older fixed-nine-round records.
            literature_dir = ROOT/'outputs/literature_benchmark'
            literature_path = literature_dir/'observations.json'
            literature_cert_path = literature_dir/'VALIDATED_LITERATURE_BENCHMARK.json'
            lit_obj = json.loads(literature_path.read_text()) if literature_path.is_file() else {}
            lit_cert = json.loads(literature_cert_path.read_text()) if literature_cert_path.is_file() else {}
            from ftqc_resource_estimator.literature_benchmark import validate_benchmark, REFERENCE
            if (lit_cert.get('status') != 'PASSED real Stim/PyMatching same-environment protocol replay' or
                lit_cert.get('observations') != 20 or lit_cert.get('total_shots') != 400000 or
                lit_cert.get('reference_url') != REFERENCE or
                lit_cert.get('stim_version') != lit_obj.get('software',{}).get('stim') or
                lit_cert.get('pymatching_version') != lit_obj.get('software',{}).get('pymatching') or
                not literature_path.is_file() or
                lit_cert.get('manifest_sha256') != sha256(literature_path.read_bytes()).hexdigest()):
                raise RuntimeError('Real d-round reference benchmark is not replay-certified. Run scripts/commands/RUN_LITERATURE_BENCHMARK.sh')
            validate_benchmark(lit_obj)
            for expected in ('round_scaled_results.csv','LITERATURE_COMPARISON.md','round_scaled_curves.png'):
                if not (literature_dir/expected).is_file():
                    raise RuntimeError(f'Literature benchmark artifact missing: {expected}')
            from ftqc_resource_estimator.controller_capacity import analyze
            capacity = ROOT/'outputs/controller_capacity'
            if not (capacity/'capacity_sensitivity.csv').is_file() or not (capacity/'CAPACITY_STUDY.md').is_file():
                raise RuntimeError('Capacity sensitivity not computed; run scripts/commands/RUN_CONTROLLER_CAPACITY.sh')
            # Independently rebuild numerical CSVs in a temporary directory and
            # compare contents. A valid certificate does not authorize edited plots/CSV.
            import tempfile
            from pathlib import Path as _P
            import csv as _csv
            from ftqc_resource_estimator.literature_benchmark import report_benchmark
            from ftqc_resource_estimator.controller_capacity import analyze, load_controllers
            with tempfile.TemporaryDirectory() as tmp:
                tmp=_P(tmp)
                report_benchmark(lit_obj,tmp/'lit')
                if (tmp/'lit/round_scaled_results.csv').read_text() != (literature_dir/'round_scaled_results.csv').read_text():
                    raise RuntimeError('Literature benchmark result CSV changed after audit')
                analyze(followup,ROOT/'examples/controller_capacity_hypotheses.json',tmp/'capacity',verified=True)
                if (tmp/'capacity/capacity_sensitivity.csv').read_text() != (capacity/'capacity_sensitivity.csv').read_text():
                    raise RuntimeError('Controller capacity report disagrees with certified follow-up data')
            # Conditional controller idle-noise simulation: require new real
            # backend certificate. Source-matched T1/T2 is *not* hardware calibration.
            idle_dir = ROOT/'outputs/idle_coherence'
            idle_path = idle_dir/'observations.json'
            idle_cert_path = idle_dir/'VALIDATED_IDLE_STUDY.json'
            idle_obj = json.loads(idle_path.read_text()) if idle_path.is_file() else {}
            idle_cert = json.loads(idle_cert_path.read_text()) if idle_cert_path.is_file() else {}
            from ftqc_resource_estimator.idle_coherence import (load_hypotheses as load_idle,
                validate_manifest as validate_idle, analyze_rows as analyze_idle,
                write_study as write_idle)
            coh, idle_controllers, idle_patches, idle_windows, idle_target = load_idle(ROOT/'examples/idle_coherence_study.json')
            if (idle_cert.get('status') != 'PASSED real Stim/PyMatching full replay - conditional idle model only' or
                idle_cert.get('shots') != 240000 or idle_cert.get('conditions') != 12 or
                idle_cert.get('manifest_sha256') != (sha256(idle_path.read_bytes()).hexdigest() if idle_path.exists() else '') or
                idle_cert.get('stim_version') != idle_obj.get('software',{}).get('stim') or
                idle_cert.get('pymatching_version') != idle_obj.get('software',{}).get('pymatching')):
                raise RuntimeError('Missing validated controller-induced idle-noise sweep; run scripts/commands/RUN_IDLE_COHERENCE_STUDY.sh')
            validate_idle(idle_obj,coh,idle_controllers,idle_patches,idle_windows,idle_target)
            with tempfile.TemporaryDirectory() as idle_temp:
                rebuilt=_P(idle_temp)
                write_idle(idle_obj,rebuilt,coh,idle_controllers,idle_patches,idle_windows,idle_target)
                if ((rebuilt/'idle_decoding_results.csv').read_text() !=
                    (idle_dir/'idle_decoding_results.csv').read_text()):
                    raise RuntimeError('Controller idle decoded rates changed since verification')
            copy_existing_tree('outputs/idle_coherence','idle_coherence',destination,allowed)
            snippets.append('**Controller idle-noise conditional simulation:** published Willow mean T1 and T2_CPMG inform a Pauli-twirled data-idle channel. Readout channel/batching/power are hypothetical and do not constitute hardware calibration; schedule-specific logical failure rates require the 240,000-shot real Stim/PyMatching run.')
            copy_existing_tree('outputs/literature_benchmark','literature_benchmark',destination,allowed)
            copy_existing_tree('outputs/controller_capacity','controller_capacity',destination,allowed)
            snippets.append('**Protocol benchmark:** a smaller independent matched-protocol subset of the Riverlane surface-code tutorial (rounds=d); not an exact reproduction of its numerical figure or a hardware threshold estimate.')
            snippets.append('**Controller capacity:** a separate hypothetical channel/time/power sensitivity; physical patch qubits are NOT added to controller electronics quantities.')
            copy_existing_tree('outputs/stim_memory','stim_memory',destination,allowed)
            snippets.append('**Real scientific backend:** Stim/PyMatching rotated-surface-code **memory** baseline plus separately seeded distance-7/9 follow-up verified under explicit protocol. At d=9 the per-event upper Wilson endpoint passes the 40-event proxy budget. The controller-cost sensitivity is an assumed proxy, not measured hardware.')
    else:
        rows=checked_csv(ROOT/'docs/results/phenomenological_paired.csv',{'distance','p_measure','trials','bayes_failures','baseline_failures','bayes_rate','baseline_rate','difference_ci_low','difference_ci_high'},9)
        for row in rows:
            n=int(row['trials'])
            if not (0<=int(row['bayes_failures'])<=n and 0<=int(row['baseline_failures'])<=n):
                raise RuntimeError('Out-of-range decoder failures')
            if abs(int(row['bayes_failures'])/n-float(row['bayes_rate']))>1e-10:
                raise RuntimeError('Decoder CSV observed rate mismatch')
            if abs(int(row['baseline_failures'])/n-float(row['baseline_rate']))>1e-10:
                raise RuntimeError('Baseline CSV observed rate mismatch')
        copy_existing_tree('docs/results', 'numerical_results', destination, allowed)
        for src in ('docs/VALIDATED_RESULTS.md','docs/HARDWARE_NOISE_ANALYSIS.md',
                    'docs/PENNYLANE_STIM_MATCHED_STUDY.md','docs/reference/PROVENANCE_AND_CLAIMS.md'):
            copy_required(src,Path(src).name,destination)
        snippets.append('**Executed local models:** classical/phenomenological repeated-syndrome, biased Pauli-sector, and located-erasure studies. The final syndrome is ideal in the Bayes comparison.')
        if args.mode == 'full':
            full=ROOT/'docs/results/matched_frameworks/matched_frameworks_real.json'
            obj=json.loads(full.read_text()) if full.is_file() else {}
            if not obj.get('stim_fixed_fault_patterns_checked')==32 or not obj.get('stim_restoration_in_5sigma_band'):
                raise RuntimeError('Real PennyLane/Stim/PyMatching matched comparison not validated')
            rows=checked_csv(ROOT/'docs/results/stim_memory_results.csv', {'task','distance','shots','failures'}, 3)
            if any(int(x['shots'])<=0 for x in rows):
                raise RuntimeError('Real backend circuit memory trial count invalid')
            copy_required('docs/STIM_RESULTS.md','STIM_RESULTS.md',destination)
            snippets.append('**Real scientific backend:** external Stim/PyMatching memory and matched PennyLane/Stim circuit runs completed; these are **different tasks and outcome metrics**.')
    provenance={
        'project':project,'publication_mode':args.mode,
        'git_commit':os.environ.get('GITHUB_SHA','local-unpublished'),
        'github_run_id':os.environ.get('GITHUB_RUN_ID','local-unpublished'),
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'python':sys.version.split()[0],
        'scope_note':'Publication does not imply calibration against commercial quantum hardware.'
    }
    (destination/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    md=[f'# {project}: reproducible analysis results', '',
        f'**Mode:** {args.mode} | **Commit:** `{provenance["git_commit"]}` | **UTC:** {provenance["generated_at_utc"]}', '',
        '## What these results establish', '',*['- '+x for x in snippets], '',
        '## Audit and limitations','',
        'See [Figure and claim audit](FIGURE_AND_CLAIM_AUDIT.md). All parameters and seeds appear in the included files; no external hardware is claimed.','',
        '## Source code','',
        'The code, simulations, and controls are on the GitHub default branch; this branch is generated **only by trusted CI** after its checks. Run artifacts from PRs may contain offline-only studies.','']
    if project == 'ftqc-resource-estimator':
        md.extend(['## Illustrative architectural comparison', '',
            '![Site/time Pareto points from the uncalibrated model](architecture_study/feasible_tradeoffs.png)', '',
            '| Assumed design | Code distance | Site equivalents | Latency (ms) |',
            '|---|---:|---:|---:|'])
        for row in rows:
            md.append(f"| {row['architecture']} | {row['distance']} | {int(float(row['total_site_equivalents'])):,} | {float(row['latency_us'])/1000:.2f} |")
        md.extend(['', 'Do not interpret this as a cross-hardware ranking, hardware measurement, or logical-gate prediction.',''])
    else:
        md.extend(['## Executed phenomenological model study', '',
            '![Bayesian vs final-syndrome-only comparison](numerical_results/paired_comparison.png)', '',
            'The model assumes a perfect final syndrome and known data/measurement error rates. At large measurement noise, the gain can be statistically inconclusive.','',
            '![Known-versus-hidden erasures, hypothetical classical code](numerical_results/hardware_noise/erasure_flag_comparison.png)', '',
            '![Biased Pauli repetition sectors](numerical_results/hardware_noise/bias_sector_comparison.png)', '',
            'These are distinct classical/phenomenological studies; none establishes a physical GKP, photonic, or hardware QEC result.',''])
    (destination/'README.md').write_text('\n'.join(md))
    print(f'Validated {project} {args.mode} publication staging: {destination}')

if __name__ == '__main__':
    main()
