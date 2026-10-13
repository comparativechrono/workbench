#!/usr/bin/env python3
"""Freeze independent bustools/StringTie packs and check exact Windows applications.

The prior candidate's archive and normal-graph helpers are loaded privately.
Neither its configuration nor the immutable application modules are changed.
The two packs remain independent. A separately pinned released HISAT2 dependency
provides a real paired RNA alignment to StringTie integration graph.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import traceback
import zipfile

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('bustools_stringtie_candidate_common', SOURCE / 'scripts/check_prodigal_fasttree_windows.py')
common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(common)
common.PACK_IDS = ('bustools', 'stringtie')
common.VERSIONS = {identity: '1.0.0' for identity in common.PACK_IDS}
common.OPERATIONS = {'bustools': {'count-bus'}, 'stringtie': {'assemble-guided', 'estimate-reference'}}
common.FROZEN_GATE_PATHS = {
    'scripts/check_bustools_stringtie_windows.py', 'scripts/check_bustools_stringtie_gui.py',
    'scripts/audit_bustools_stringtie_candidate.py', 'tests/test_bustools_stringtie_validation.py',
    '.github/workflows/native-bustools-stringtie-recheck.yml',
}
PACK_IDS, VERSIONS, APPLICATIONS = common.PACK_IDS, common.VERSIONS, common.APPLICATIONS
HISAT2 = {'id': 'hisat2', 'version': '0.5.3',
          'sha256': '85d02ead1c7205428b22c73b1c7f751786645c4a4d51296cb6fc824623fd6126',
          'manifestSha256': '06f912deb5926b00a8ca269138b4b3822bb4b3e36d4956e30ca7793655052967',
          'url': 'https://github.com/comparativechrono/workbench/releases/download/pack-hisat2-v0.5.3/native-workbench-pack-hisat2-0.5.3.zip',
          'publicationStatus': 'published development prerelease'}
SAMTOOLS = {'packId': 'bam', 'packVersion': '0.4.0',
            'manifestSha256': '45b3f9d5092b0b3014f67b29331003e1214c72919f85695a571fb371030a9888',
            'operation': 'bam/flagstat', 'id': 'samtools', 'version': '1.24',
            'sha256': '49c2f16425d464e4ad1c1439d7a9e32a3b1c1bf8e5d54403778de610d2f440b3',
            'path': 'bin/samtools.exe', 'providedBy': 'unchanged pinned Starter application'}
require, sha, read_json, write_json = common.require, common.sha, common.read_json, common.write_json
file_record, verify_extracted, run_command = common.file_record, common.verify_extracted, common.run_command


def freeze(args):
    sys.path.insert(0, str(SOURCE / 'scripts'))
    from package_split import build_pack
    from validate_pack_release import inspect_release
    source = common.checkout_sources(args.source_commit)
    require(not args.output.exists(), 'Choose a new candidate output directory.')
    args.output.mkdir(parents=True)
    packs, entries = {}, [('source/' + name, path) for name, path in source]
    for identity in PACK_IDS:
        folder = getattr(args, identity + '_pack').resolve()
        archive = args.output / ('native-workbench-pack-' + identity + '-' + VERSIONS[identity] + '.zip')
        built = build_pack(folder, archive, '0.16.0')
        inspected = inspect_release(archive)
        require((inspected['id'], inspected['version']) == (identity, VERSIONS[identity]), 'Unexpected pack identity.')
        require(built['sha256'] == inspected['sha256'], 'Static validation changed archive identity.')
        packs[identity] = {**file_record(archive), 'id': identity, 'version': VERSIONS[identity],
                           'manifestSha256': inspected['manifestSha256'], 'staticValidation': inspected}
        for path in sorted((folder / 'licenses').rglob('*')):
            if path.is_file():
                require(not path.is_symlink(), 'Corresponding source contains a symbolic link.')
                entries.append(('corresponding-sources/' + identity + '/' + path.relative_to(folder / 'licenses').as_posix(), path))
    for number, root in enumerate(args.build_evidence):
        require(root.is_dir(), 'Build evidence directory is absent.')
        for path in sorted(root.rglob('*')):
            if path.is_file():
                require(not path.is_symlink(), 'Build evidence contains a symbolic link.')
                entries.append(('build-evidence/' + str(number + 1) + '/' + path.relative_to(root).as_posix(), path))
    inventory = [{'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)} for name, path in entries]
    provenance = {'schema': 1, 'kind': 'unpublished-bustools-stringtie-candidate',
                  'sourceCommit': args.source_commit,
                  'sourceTree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=SOURCE, text=True).strip(),
                  'createdUtc': datetime.now(timezone.utc).isoformat(), 'buildHost': platform.platform(),
                  'python': sys.version, 'packs': packs, 'applications': APPLICATIONS,
                  'nativeWindowsExecuted': False, 'published': False, 'integrationDependency': HISAT2,
                  'limits': ['Build-time source/static evidence only. Separate native reports must bind these exact archive hashes.',
                             'The packs are independently importable and do not imply a shared scientific workflow.',
                             'Application binaries and published catalogues are unchanged.']}
    companion = args.output / 'native-workbench-bustools-stringtie-1.0.0-source-evidence.zip'
    common.zip_files(companion, entries, {'SOURCE-INVENTORY.json': {'schema': 1, 'sourceCommit': args.source_commit, 'files': inventory},
                                        'BUILD-PROVENANCE.json': provenance})
    provenance['sourceCompanion'] = file_record(companion)
    write_json(args.output / 'BUILD-PROVENANCE.json', provenance)
    (args.output / 'SHA256SUMS.txt').write_text('\n'.join(row['sha256'] + '  ' + row['file']
        for row in [*packs.values(), provenance['sourceCompanion']]) + '\n', encoding='ascii')
    return provenance


def installed_inventory(folder):
    return {path.relative_to(folder).as_posix(): sha(path) for path in folder.rglob('*') if path.is_file()}


def archive_inventory(archive):
    with zipfile.ZipFile(archive) as zipped:
        envelope = json.loads(zipped.read('workbench-pack.json'))
        return {row['path']: row['sha256'] for row in envelope['files']}


def scientific_report_passed(report):
    """Fail closed when a selected scientific suite did not actually execute."""
    return (report.get('success') is True and report.get('nativeWindowsExecuted') is True and
            isinstance(report.get('testsRun'), int) and report['testsRun'] > 0 and
            not report.get('skipped') and bool(report.get('executions')))


def candidate_check_catalog(catalog, identity, version):
    """Retain the target checks and its exact existing SAMtools preflight helper.

    The generic historical release checker removes every other pack descriptor.
    That makes StringTie checks unable to see SAMtools already in Starter. This
    scoped catalogue preserves the dependency without changing app preflight.
    """
    selected = copy.deepcopy(catalog)
    selected['tools'] = {key: tool for key, versions in catalog['toolVersions'].items()
                         for tool in versions if tool.get('packId') == identity and tool.get('packVersion') == version}
    require(selected['tools'], 'No exact candidate operation selected.')
    candidates = [tool for tool in catalog['toolVersions'].get(SAMTOOLS['operation'], [])
                  if all(tool.get(key) == SAMTOOLS[key] for key in ('packId', 'packVersion', 'manifestSha256'))]
    require(len(candidates) == 1, 'Exact Starter SAMtools dependency is absent or changed.')
    dependency = candidates[0]
    matches = [executable for executable in dependency.get('executables', [])
               if all(executable.get(key) == SAMTOOLS[key] for key in ('id', 'version', 'sha256', 'path'))]
    require(len(matches) == 1, 'Exact Starter SAMtools executable is absent or changed.')
    selected['tools'][dependency['id']] = dependency
    selected['toolVersions'] = {key: [tool] for key, tool in selected['tools'].items()}
    selected['packs'] = [item for item in catalog['packs']
                         if (item['id'], item['version']) in {(identity, version), ('bam', '0.4.0')}]
    return selected, dependency


def timed_installation_checks(root, catalog, results, backend, runner, report, *, seconds=120):
    """Cancel the real native backend at a bounded self-check deadline.

    The cancellation event reaches ordinary engine/bridge cancellation. Closing
    the backend also closes the bridge's kill-on-close Job Object, so a modal
    child cannot indefinitely prevent the check report from being preserved.
    """
    cancel, expired = threading.Event(), threading.Event()
    deadline_errors = []
    results.mkdir(parents=True, exist_ok=True)
    events = results / 'installation-events.jsonl'
    log_lock = threading.Lock()

    def event(item):
        with log_lock, events.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(item, ensure_ascii=False) + '\n')

    def deadline():
        expired.set()
        cancel.set()
        try:
            event({'type': 'error', 'message': 'Native StringTie installation checks exceeded the validation deadline.',
                   'deadlineSeconds': seconds})
        except Exception as exc:
            deadline_errors.append('Could not retain deadline event: ' + str(exc))
        try:
            backend.shutdown()
        except Exception as exc:
            deadline_errors.append(str(exc))

    timer = threading.Timer(seconds, deadline)
    timer.daemon = True
    timer.start()
    try:
        checks = runner(root, catalog, results, backend=backend, cancel=cancel, event=event)
        report['scientificChecks'] = checks
    finally:
        timer.cancel()
        timer.join(timeout=10)
        report['scientificDeadline'] = {'seconds': seconds, 'exceeded': expired.is_set(),
                                        'cancellationRequested': cancel.is_set(), 'backendShutdownErrors': deadline_errors}
        report['retainedCheckResults'] = str(results)
        report['retainedCheckEventLog'] = str(events)
    # A deadline callback may already have started when cancellation occurs.
    # Test the final state only after joining it; a late success cannot hide it.
    require(not expired.is_set(), 'Native StringTie installation checks exceeded the ' + str(seconds) + '-second deadline.')
    return checks


def stringtie_installation_check(root, archive, report_path):
    """Native exact import and target checks with frozen Starter preflight intact."""
    from catalog import load_catalog, load_pack
    from engine import NativeBackend, pin_for
    from pack_checks import run_pack_checks
    from pack_manager import PackManager
    from service import Workbench
    report = {'schema': 1, 'nativeWindowsHost': os.name == 'nt', 'nativeWindowsExecuted': False, 'success': False}
    require(os.name == 'nt', 'Installation checks require native Windows.')
    class ObservedBackend(NativeBackend):
        def _spawn(self, *arguments, **options):
            process = super()._spawn(*arguments, **options)
            report['nativeWindowsExecuted'] = True
            return process
    app, backend = None, None
    try:
        app = Workbench(root)
        manager = PackManager(root, app._install_pack_folder)
        installed = manager.import_archive(archive.resolve())
        identity, version = installed['packId'], installed['packVersion']
        require((identity, version) == ('stringtie', '1.0.0'), 'Unexpected target import identity.')
        report.update(packId=identity, packVersion=version, installation=installed)
        catalog = load_catalog(root)
        selected, dependency = candidate_check_catalog(catalog, identity, version)
        dependency_folder = root / dependency['packFolder']
        require(sha(dependency_folder / 'pack.ini') == SAMTOOLS['manifestSha256'] and
                sha(dependency_folder / SAMTOOLS['path']) == SAMTOOLS['sha256'],
                'Installed Starter preflight dependency bytes differ.')
        dependency_pack = load_pack(dependency_folder / 'pack.ini')
        require('workbench-checks' not in dependency_pack['assets'],
                'Dependency unexpectedly introduces unrelated declared checks.')
        candidate = next(item for item in selected['packs'] if item['id'] == identity)
        folder = root / candidate['folder']
        pack = load_pack(folder / 'pack.ini')
        spec = read_json(folder / pack['assets']['workbench-checks']['path'])
        expected_checks = {identity + '/' + case['id'] + '@' + version for case in spec['checks']}
        require(expected_checks, 'Target has no declared scientific checks.')
        report['preflightDependency'] = {**SAMTOOLS, 'pin': pin_for(dependency),
                                         'scope': 'Existing Starter descriptor retained for ordinary alignment inspection; dependency has no selected self-checks.'}
        # Keep partial plans, child logs and check reports inside the uploaded
        # evidence directory even when validation fails or the deadline fires.
        results = report_path.parent / 'stringtie-installation-results'
        backend = ObservedBackend(root)
        checks = timed_installation_checks(root, selected, results, backend, run_pack_checks, report)
        require(checks.get('success') and checks.get('nativeWindowsExecuted') and
                report['nativeWindowsExecuted'] and checks.get('passed') == len(expected_checks) and
                {row['id'] for row in checks['checks']} == expected_checks and
                all(row['status'] == 'passed' for row in checks['checks']),
                'Exact target scientific checks failed, skipped, or included unrelated checks.')
        try:
            manager.import_archive(archive.resolve())
        except ValueError as exc:
            require('already installed' in str(exc).lower(), 'Unexpected duplicate import failure: ' + str(exc))
            report['duplicateVersionRejected'] = True
        else:
            raise ValueError('Duplicate version unexpectedly installed.')
        require(sha(folder / 'pack.ini') == candidate['manifestSha256'] and
                sha(dependency_folder / 'pack.ini') == SAMTOOLS['manifestSha256'] and
                sha(dependency_folder / SAMTOOLS['path']) == SAMTOOLS['sha256'],
                'Candidate/dependency bytes changed during checks.')
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if app is not None:
            app.shutdown()
        if backend is not None:
            backend.shutdown()
        write_json(report_path, report)
    return report


def graph_for_case(root, catalog, identity, operation):
    """Use installed declared scientific inputs through an ordinary saved graph."""
    from catalog import load_pack, resolve_tool
    from engine import pin_for
    item = next(item for item in catalog['packs'] if item['id'] == identity and item['version'] == VERSIONS[identity])
    folder = root / item['folder']
    pack = load_pack(folder / 'pack.ini')
    cases = read_json(folder / pack['assets']['workbench-checks']['path'])['checks']
    case = next(case for case in cases if case['workflow'] == operation)
    tool = resolve_tool(catalog, identity + '/' + operation)
    sources, inputs = [], {}
    ports = {port['id']: port for port in tool['ports']}
    for port_id, members in case['inputs'].items():
        inputs[port_id] = []
        for member in members:
            source_id = 'input-' + str(len(sources) + 1)
            files = {key: str(folder / pack['assets'][asset]['path']) for key, asset in member.items()}
            sources.append({'id': source_id, 'label': ports[port_id]['label'], 'type': ports[port_id]['type'], 'files': files})
            inputs[port_id].append(source_id)
    return {'schema': 1, 'name': 'Pack candidate ' + identity,
            'nodes': [{'id': 'step-1', 'tool': tool['id'], 'pin': pin_for(tool), 'params': case.get('params', {}), 'inputs': inputs}],
            'sources': sources, 'nextNode': 2, 'nextSource': len(sources) + 1}


def record_graph(host, graph, output, evidence, stem):
    record = common.completed(host, 'run', {'graph': graph, 'output_folder': str(output)})
    folder = Path(record['folder'])
    frozen, run = read_json(folder / 'plan.json'), read_json(folder / 'run.json')
    require([node['pin'] for node in frozen['graph']['nodes']] == [node['pin'] for node in graph['nodes']],
            'Run changed exact selected pins.')
    for name in ('run.json', 'methods-completed.txt', 'workflow.cwl'):
        require((folder / name).is_file() and (folder / name).stat().st_size > 0, 'Missing run provenance: ' + name)
    summary = host.call('results/summary', {'id': record['run_id']})
    require(not summary.get('failures'), 'Successful result reports failure.')
    found = host.call('results/search', {'query': graph['name']})
    require({row['run_id'] for row in found['runs']} == {record['run_id']}, 'Result search did not isolate the run.')
    outputs = {}
    for key, item in run['outputs'].items():
        for field, path in item['files'].items():
            outputs[key + ':' + field] = file_record(Path(path))
    write_json(evidence / (stem + '-result-summary.json'), summary)
    write_json(evidence / (stem + '-graph.json'), graph)
    return record, run, {'runId': record['run_id'], 'name': graph['name'],
                        'planSha256': sha(folder / 'plan.json'), 'runSha256': sha(folder / 'run.json'),
                        'methodsSha256': sha(folder / 'methods-completed.txt'), 'cwlSha256': sha(folder / 'workflow.cwl'),
                        'pins': [node['pin'] for node in graph['nodes']], 'outputs': outputs}


def graph_checks(root, evidence, report):
    from catalog import load_catalog
    from check_references_windows import PrivateHost
    catalog = load_catalog(root)
    for identity in PACK_IDS:
        require({key.split('/', 1)[1] for key, value in catalog['tools'].items() if value.get('packId') == identity} == common.OPERATIONS[identity],
                'Pack operation catalogue differs: ' + identity)
    host = PrivateHost(root, evidence, 'bustools-stringtie-host', offline=True)
    output = evidence / 'analysis-results'
    output.mkdir()
    report['recordedRuns'], report['guiRunTools'] = {}, {}
    try:
        require(host.call('init')['app_version'] == report['applicationVersion'], 'Wrong application process.')
        for identity in PACK_IDS:
            for number, operation in enumerate(sorted(common.OPERATIONS[identity])):
                graph = graph_for_case(root, catalog, identity, operation)
                if number:
                    graph['name'] = 'Additional operation ' + identity + ' ' + operation
                else:
                    report['guiRunTools'][identity] = graph['nodes'][0]['tool']
                reviewed = host.call('review', {'graph': graph})
                require(reviewed['valid'], 'Exact-pin graph is not ready: ' + json.dumps(reviewed))
                wrong = copy.deepcopy(graph)
                # RNA BAM is a legitimate StringTie input, so the old generic
                # sequence-operation negative is unsuitable for this stage.
                wrong['sources'][0]['type'] = 'bam' if identity == 'stringtie' else 'bam-rna'
                require(not host.call('review', {'graph': wrong})['valid'], 'Incompatible input type accepted: ' + identity)
                stale = copy.deepcopy(graph)
                stale['nodes'][0]['pin']['manifestSha256'] = '0' * 64
                require(not host.call('review', {'graph': stale})['valid'], 'Stale saved manifest pin accepted.')
                _, _, receipt = record_graph(host, graph, output, evidence, identity + '-' + operation)
                report['recordedRuns'][identity + '/' + operation] = receipt
                report['checks'].append(identity + '/' + operation + ': exact-pin normal graph execution, incompatible input/stale pin rejection, methods/CWL and searchable results.')
    finally:
        host.close()


def hisat2_stringtie_checks(root, evidence, report):
    """Execute the published RNA producer and both new consumer contracts."""
    from catalog import load_catalog
    from engine import pin_for
    from check_references_windows import PrivateHost
    catalog = load_catalog(root)
    aligner = catalog['tools']['hisat2/rna-paired']
    require(aligner['manifestSha256'] == HISAT2['manifestSha256'], 'HISAT2 exact dependency changed.')
    stringtie_folder = root / next(item['folder'] for item in catalog['packs'] if item['id'] == 'stringtie')
    fixture = stringtie_folder / 'fixtures'
    spec = importlib.util.spec_from_file_location('stringtie_integration_oracle', SOURCE / 'tests/test_stringtie_pack.py')
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    host = PrivateHost(root, evidence, 'hisat2-stringtie-host', offline=True)
    report['hisat2StringtieGraphChains'] = []
    try:
        require(host.call('init')['app_version'] == report['applicationVersion'], 'Wrong application process.')
        for operation in sorted(common.OPERATIONS['stringtie']):
            consumer = catalog['tools']['stringtie/' + operation]
            chain = {'schema': 1, 'name': 'HISAT2 RNA to StringTie ' + operation, 'nextNode': 3, 'nextSource': 4,
                     'sources': [
                         {'id': 'input-1', 'type': 'pair', 'label': 'Synthetic paired spliced RNA reads',
                          'files': {'reads1': str(fixture / 'hisat-r1.fastq'), 'reads2': str(fixture / 'hisat-r2.fastq')}},
                         {'id': 'input-2', 'type': 'reference', 'label': 'Synthetic genome',
                          'files': {'reference': str(fixture / 'hisat-reference.fa')}},
                         {'id': 'input-3', 'type': 'text', 'label': 'Matching synthetic transcript guide',
                          'files': {'annotation': str(fixture / 'hisat-annotation.gtf')}}],
                     'nodes': [
                         {'id': 'step-1', 'tool': aligner['id'], 'pin': pin_for(aligner),
                          'params': {'sample': 'integration', 'read-group': 'integration', 'library': 'lib1',
                                     'platform-unit': 'unit1', 'threads': 1, 'seed': 0, 'strandness': 'unstranded'},
                          'inputs': {'reads': ['input-1'], 'reference': ['input-2']}},
                         {'id': 'step-2', 'tool': consumer['id'], 'pin': pin_for(consumer),
                          'params': {'strandness': 'unstranded', 'min-length': 100},
                          'inputs': {'alignment': ['step-1::aligned'], 'annotation': ['input-3']}}]}
            reviewed = host.call('review', {'graph': chain})
            require(reviewed['valid'], 'Published coordinate RNA BAM does not satisfy StringTie contract: ' + json.dumps(reviewed))
            wrong = copy.deepcopy(chain)
            wrong['nodes'][1]['inputs']['alignment'] = ['step-1::aligned-sam']
            require(not host.call('review', {'graph': wrong})['valid'], 'Unsorted RNA SAM accepted by coordinate RNA BAM consumer.')
            record, run, receipt = record_graph(host, chain, evidence / 'analysis-results', evidence,
                                               'hisat2-stringtie-' + operation)
            # This oracle validates hand-constructed splice/paired coordinates,
            # GTF exon structure and measured abundance; it does not compare two
            # executions of the same port as the sole scientific expectation.
            observed = oracle.validate_hisat_graph(run, fixture)
            receipt.update(operation=operation, scientificAssertions=observed)
            report['hisat2StringtieGraphChains'].append(receipt)
            report['checks'].append('Published HISAT2 paired spliced RNA output feeds StringTie ' + operation +
                                    ' through the real typed graph; independent alignment and transcript truth agree.')
    finally:
        host.close()


def installation_regression(root, evidence, report):
    from check_references_windows import PrivateHost
    host = PrivateHost(root, evidence, 'bustools-stringtie-regression-host', offline=True)
    try:
        require(host.call('init')['app_version'] == report['applicationVersion'], 'Wrong application process.')
        record = common.completed(host, 'check', {'output_folder': str(evidence / 'analysis-results')})
        write_json(evidence / 'installation-regression.json', record)
        require(record.get('pack_checks', {}).get('success'), 'Combined installed pack checks failed.')
        require(record.get('starter_checks', {}).get('nativeWindowsExecuted') and
                record['starter_checks'].get('passed', 0) > 0 and record.get('skipped') == 0,
                'Starter science must execute natively; skipped checks cannot pass.')
        report['checks'].append('Unchanged Starter science and all installed declared pack checks pass together.')
    finally:
        host.close()


def native(args):
    require(os.name == 'nt', 'This gate requires native Windows; Linux is not equivalent.')
    root, evidence = args.app_root.resolve(), args.report.resolve().parent
    require(not evidence.is_relative_to(root), 'Evidence must be outside the immutable application tree.')
    evidence.mkdir(parents=True, exist_ok=True)
    candidate_commit = args.candidate_source_commit or args.source_commit
    report = {'schema': 1, 'kind': 'native-bustools-stringtie-candidate', 'success': False,
              'candidateSourceCommit': candidate_commit, 'gateSourceCommit': args.source_commit,
              'applicationVersion': args.app_version, 'applicationSourceCommit': APPLICATIONS[args.app_version]['sourceCommit'],
              'applicationArchive': file_record(args.app_archive), 'mode': args.mode,
              'nativeWindowsHost': True, 'nativeWindowsExecuted': False, 'python': sys.version,
              'platform': platform.platform(), 'checks': [], 'captures': [],
              'limitations': ['Synthetic bounded fixtures only; no representative-PC or large-data performance acceptance.',
                             'No release, catalogue publication, signing, institutional deployment or updater validation.',
                             'Offline private host denies Python socket calls; not operating-system network isolation.',
                             'BUS counts depend on the matching quantification files and supplied allowlist; no cell calling is performed.',
                             'StringTie abundance/assembly measurements do not establish biological truth or QC acceptance thresholds.']}
    try:
        require(sha(args.app_archive) == APPLICATIONS[args.app_version]['sha256'], 'Unexpected application archive.')
        report['coreFilesVerifiedBefore'] = verify_extracted(args.app_archive, root)
        frozen = common.verify_candidate(args.candidate, candidate_commit, args.source_commit)
        report['frozenCandidateRecheck'] = candidate_commit != args.source_commit
        report['gateSourceDifferences'] = common.frozen_source_changes(candidate_commit, args.source_commit) if candidate_commit != args.source_commit else []
        report['packs'], report['sourceCompanion'] = frozen['packs'], frozen['sourceCompanion']
        sys.path.insert(0, str(root / 'workspace'))
        sys.path.insert(1, str(SOURCE / 'scripts'))
        import catalog
        require(Path(catalog.__file__).resolve().parent == root / 'workspace',
                'Native graph expectations must use the exact packaged application modules.')
        python = root / 'runtime/python/python.exe'
        installed, expected = {}, {}
        for identity in PACK_IDS:
            archive = args.candidate / frozen['packs'][identity]['file']
            if identity == 'stringtie':
                result = stringtie_installation_check(root, archive, evidence / (identity + '-installation.json'))
                report['samtoolsPreflightDependency'] = result.get('preflightDependency')
            else:
                run_command([python, '-I', '-B', SOURCE / 'scripts/check_pack_release_windows.py', '--app-root', root,
                             '--archive', archive, '--report', evidence / (identity + '-installation.json')],
                            evidence / (identity + '-installation.log'))
                result = read_json(evidence / (identity + '-installation.json'))
            require(result['success'] and result['nativeWindowsExecuted'] and result['duplicateVersionRejected'],
                    'Native import/check did not fully execute: ' + identity)
            report['nativeWindowsExecuted'] = True
            report['checks'].append(identity + ': exact ZIP native import, declared scientific checks and duplicate-version rejection.')
            installed[identity] = root / 'packs' / (identity + '-' + VERSIONS[identity])
            expected[identity] = archive_inventory(archive)
            if args.mode == 'science':
                run_command([python, '-I', '-B', SOURCE / ('tests/test_' + identity + '_pack.py'),
                             '--pack', installed[identity], '--report', evidence / (identity + '-regressions.json')],
                            evidence / (identity + '-regressions.log'))
                regression = read_json(evidence / (identity + '-regressions.json'))
                require(scientific_report_passed(regression),
                        'Selected native scientific regressions must execute with no skips: ' + identity)
                report['checks'].append(identity + ': exact installed scientific and failure regressions.')
        if args.mode == 'science':
            require(args.hisat2_archive and sha(args.hisat2_archive) == HISAT2['sha256'],
                    'Science requires the exact released HISAT2 archive.')
            run_command([python, '-I', '-B', SOURCE / 'scripts/check_pack_release_windows.py', '--app-root', root,
                         '--archive', args.hisat2_archive, '--report', evidence / 'hisat2-installation.json'],
                        evidence / 'hisat2-installation.log')
            dependency = read_json(evidence / 'hisat2-installation.json')
            require(dependency['success'] and dependency['nativeWindowsExecuted'] and dependency['duplicateVersionRejected'],
                    'HISAT2 native import/check did not fully execute.')
            report['hisat2Dependency'] = {**HISAT2, **file_record(args.hisat2_archive)}
            installed['hisat2'] = root / 'packs/hisat2-0.5.3'
            expected['hisat2'] = archive_inventory(args.hisat2_archive)
            require(sha(installed['hisat2'] / 'pack.ini') == HISAT2['manifestSha256'], 'HISAT2 manifest differs.')
            report['checks'].append('Exact released HISAT2 ZIP native import, four declared alignment checks and duplicate-version rejection.')
        for identity, folder in installed.items():
            require(installed_inventory(folder) == expected[identity], 'Installed pack differs from exact archive: ' + identity)
        graph_checks(root, evidence, report)
        if args.mode == 'science':
            hisat2_stringtie_checks(root, evidence, report)
            installation_regression(root, evidence, report)
        else:
            from check_bustools_stringtie_gui import run_gui
            run_gui(root, evidence, report)
        for identity, folder in installed.items():
            require(installed_inventory(folder) == expected[identity], 'Installed pack changed during graph/GUI checks: ' + identity)
        report['coreFilesVerifiedAfter'] = verify_extracted(args.app_archive, root)
        report['checks'].append('Pinned application and installed pack bytes remain unchanged after execution.')
        report['success'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        write_json(args.report, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('freeze')
    for identity in PACK_IDS:
        create.add_argument('--' + identity + '-pack', type=Path, required=True)
    create.add_argument('--output', type=Path, required=True)
    create.add_argument('--build-evidence', type=Path, action='append', default=[])
    create.add_argument('--source-commit', required=True)
    check = commands.add_parser('native')
    check.add_argument('--candidate', type=Path, required=True)
    check.add_argument('--hisat2-archive', type=Path, help='Exact released HISAT2 integration dependency; required for science mode.')
    check.add_argument('--app-root', type=Path, required=True)
    check.add_argument('--app-archive', type=Path, required=True)
    check.add_argument('--app-version', choices=APPLICATIONS, required=True)
    check.add_argument('--mode', choices=('science', 'gui'), required=True)
    check.add_argument('--source-commit', required=True, help='Actual validator/gate checkout commit.')
    check.add_argument('--candidate-source-commit', help='Frozen pack build commit; defaults to the gate commit.')
    check.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    report = freeze(args) if args.command == 'freeze' else native(args)
    print(json.dumps({'success': report.get('success', True), 'command': args.command,
                      'checks': len(report.get('checks', [])), 'sourceCommit': args.source_commit}))
    return 0 if report.get('success', True) else 1


if __name__ == '__main__':
    raise SystemExit(main())
